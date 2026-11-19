import os, time
os.environ["TZ"] = "Asia/Manila"
if hasattr(time, "tzset"): time.tzset()

import os, re, sqlite3, secrets

from datetime import datetime, timedelta, date
from functools import wraps
from flask import (Flask, g, render_template, request, redirect, url_for,
                   session, jsonify, flash)
from werkzeug.security import generate_password_hash, check_password_hash

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "database.db")
ID_RE = re.compile(r"^TUPM-[0-9]{2}-[0-9]{4}$")
STATUSES = ["Present", "Late", "Absent", "Excused"]

app = Flask(__name__)
_key = os.path.join(BASE, "secret.key")
if not os.path.exists(_key):
    with open(_key, "w") as f:
        f.write(secrets.token_hex(32))
app.secret_key = open(_key).read().strip()


# ---------- database ----------
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


def q(sql, args=(), one=False):
    cur = get_db().execute(sql, args)
    rows = cur.fetchall()
    return (rows[0] if rows else None) if one else rows


def init_db(admin_user="admin", admin_pass="admin123"):
    db = sqlite3.connect(DB)
    with open(os.path.join(BASE, "schema.sql")) as f:
        db.executescript(f.read())
    h = generate_password_hash(admin_pass)
    if db.execute("SELECT 1 FROM admins WHERE username=?", (admin_user,)).fetchone():
        db.execute("UPDATE admins SET password_hash=? WHERE username=?", (h, admin_user))
    else:
        db.execute("INSERT INTO admins(username,password_hash) VALUES(?,?)", (admin_user, h))
    db.commit()
    db.close()


# ---------- auth ----------
def login_required(role):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if session.get("role") != role:
                if request.path.startswith("/api/"):
                    return jsonify(result="denied", message="Access denied"), 403
                if "role" not in session:
                    return redirect(url_for("login"))
                return "Access denied", 403
            return fn(*a, **kw)
        return wrapper
    return deco


admin_required = login_required("admin")
student_required = login_required("student")


@app.context_processor
def inject():
    return dict(role=session.get("role"), who=session.get("name"))


# ---------- attendance logic ----------
def session_start(s):
    return datetime.strptime(f"{s['session_date']} {s['start_time']}", "%Y-%m-%d %H:%M")


def is_closed(s):
    return (not s["is_open"]) or s["session_date"] < date.today().isoformat()


def effective_status(student, s, att):
    """Returns status string, or None if session does not apply to student."""
    if student["enrolled_at"] and s["session_date"] < student["enrolled_at"][:10]:
        return None
    if att:
        return att["status"]
    return "Absent" if is_closed(s) else "Pending"


def level(absent, late):
    if absent >= 3 or late >= 6:
        return "Drop"
    if absent == 2 or 4 <= late <= 5:
        return "Warning"
    return "Safe"


def student_report(student):
    sessions = q("SELECT * FROM class_sessions ORDER BY session_date DESC, start_time DESC, id DESC")
    att = {r["session_id"]: r for r in
           q("SELECT * FROM attendance WHERE student_id=?", (student["id"],))}
    rows, absent, late = [], 0, 0
    for s in sessions:
        a = att.get(s["id"])
        st = effective_status(student, s, a)
        if st is None:
            continue
        if st == "Absent":
            absent += 1
        elif st == "Late":
            late += 1
        rows.append(dict(date=s["session_date"], start=s["start_time"], status=st,
                         scanned_at=a["scanned_at"] if a else None,
                         note=a["note"] if a else None))
    return dict(rows=rows, absent=absent, late=late, level=level(absent, late))


# ---------- auth pages ----------
@app.route("/")
def index():
    if session.get("role") == "admin":
        return redirect(url_for("kiosk"))
    if session.get("role") == "student":
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        pw = request.form.get("password", "")
        adm = q("SELECT * FROM admins WHERE username=?", (user,), one=True)
        if adm and check_password_hash(adm["password_hash"], pw):
            session.clear()
            session.update(role="admin", uid=adm["id"], name=adm["username"])
            return redirect(url_for("kiosk"))
        stu = q("SELECT * FROM students WHERE tupm_id=?", (user.upper(),), one=True)
        if stu and stu["password_hash"] and check_password_hash(stu["password_hash"], pw):
            session.clear()
            session.update(role="student", uid=stu["id"], name=stu["full_name"] or stu["tupm_id"])
            return redirect(url_for("dashboard"))
        flash("Wrong ID/username or password.")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        tid = request.form.get("tupm_id", "").strip().upper()
        name = request.form.get("full_name", "").strip()
        pw = request.form.get("password", "")
        if not ID_RE.match(tid):
            flash("ID format must be TUPM-YY-NNNN.")
        elif len(pw) < 6:
            flash("Password needs at least 6 characters.")
        else:
            stu = q("SELECT * FROM students WHERE tupm_id=?", (tid,), one=True)
            if not stu or not stu["enrolled"]:
                flash("ID not enrolled. Ask your admin.")
            elif stu["password_hash"]:
                flash("Already registered. Log in.")
            else:
                db = get_db()
                db.execute("UPDATE students SET password_hash=?, full_name=COALESCE(NULLIF(?,''),full_name) WHERE id=?",
                           (generate_password_hash(pw), name, stu["id"]))
                db.commit()
                flash("Registered. You can log in now.")
                return redirect(url_for("login"))
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- student ----------
@app.route("/dashboard")
@student_required
def dashboard():
    stu = q("SELECT * FROM students WHERE id=?", (session["uid"],), one=True)
    return render_template("dashboard.html", stu=stu, rep=student_report(stu))


@app.get("/api/me/attendance")
@student_required
def api_me():
    stu = q("SELECT * FROM students WHERE id=?", (session["uid"],), one=True)
    return jsonify(student_report(stu))


# ---------- admin pages ----------
@app.route("/kiosk")
@admin_required
def kiosk():
    return render_template("kiosk.html")


@app.route("/admin/sessions")
@admin_required
def admin_sessions():
    rows = q("SELECT * FROM class_sessions ORDER BY session_date DESC, start_time DESC, id DESC")
    now = datetime.now()
    return render_template("admin_sessions.html", rows=rows,
                           today=now.strftime("%Y-%m-%d"), now=now.strftime("%H:%M"))


@app.route("/admin/students")
@admin_required
def admin_students():
    rows = q("SELECT * FROM students ORDER BY tupm_id")
    out = []
    for s in rows:
        if s["enrolled"]:
            r = student_report(s)
            out.append(dict(s=s, absent=r["absent"], late=r["late"], level=r["level"]))
        else:
            out.append(dict(s=s, absent=0, late=0, level="-"))
    return render_template("admin_students.html", rows=out)


@app.route("/admin/attendance")
@admin_required
def admin_attendance():
    sessions = q("SELECT * FROM class_sessions ORDER BY session_date DESC, start_time DESC, id DESC")
    sid = request.args.get("session", type=int) or (sessions[0]["id"] if sessions else None)
    cur = next((s for s in sessions if s["id"] == sid), None)
    rows = []
    if cur:
        att = {r["student_id"]: r for r in
               q("SELECT * FROM attendance WHERE session_id=?", (cur["id"],))}
        for stu in q("SELECT * FROM students WHERE enrolled=1 ORDER BY tupm_id"):
            a = att.get(stu["id"])
            st = effective_status(stu, cur, a)
            if st is None:
                continue
            rows.append(dict(stu=stu, status=st, a=a))
    return render_template("admin_attendance.html", sessions=sessions, cur=cur,
                           rows=rows, statuses=STATUSES)


# ---------- API ----------
def res(result, message, tid="", name="", status=None, code=200):
    return jsonify(result=result, message=message, tupm_id=tid, name=name, status=status), code


@app.post("/api/scan")
@admin_required
def api_scan():
    data = request.get_json(silent=True) or {}
    tid = str(data.get("tupm_id", "")).strip().upper()
    mode = data.get("mode", "attendance")
    if not ID_RE.match(tid):
        return res("invalid", "Invalid QR")
    db = get_db()
    stu = q("SELECT * FROM students WHERE tupm_id=?", (tid,), one=True)

    if mode == "enroll":
        if stu and stu["enrolled"]:
            return res("duplicate", "Already enrolled", tid, stu["full_name"] or "")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if stu:
            db.execute("UPDATE students SET enrolled=1, enrolled_at=? WHERE id=?", (now, stu["id"]))
        else:
            db.execute("INSERT INTO students(tupm_id, enrolled, enrolled_at) VALUES(?,1,?)", (tid, now))
        db.commit()
        return res("enrolled", "Enrolled", tid)

    if not stu or not stu["enrolled"]:
        return res("not_enrolled", "Not enrolled", tid)
    s = q("SELECT * FROM class_sessions WHERE is_open=1 ORDER BY session_date DESC, start_time DESC, id DESC LIMIT 1", one=True)
    if not s:
        return res("no_session", "No session", tid, stu["full_name"] or "")
    if q("SELECT 1 FROM attendance WHERE student_id=? AND session_id=?", (stu["id"], s["id"]), one=True):
        return res("duplicate", "Already recorded", tid, stu["full_name"] or "")
    now = datetime.now()
    cutoff = session_start(s) + timedelta(minutes=s["late_after_minutes"])
    status = "Late" if now > cutoff else "Present"
    db.execute("INSERT INTO attendance(student_id, session_id, status, scanned_at) VALUES(?,?,?,?)",
               (stu["id"], s["id"], status, now.strftime("%Y-%m-%d %H:%M:%S")))
    db.commit()
    return res(status.lower(), status, tid, stu["full_name"] or "", status)


@app.post("/api/students")
@admin_required
def api_students():
    data = request.get_json(silent=True) or {}
    tid = str(data.get("tupm_id", "")).strip().upper()
    name = str(data.get("full_name", "")).strip()
    if not ID_RE.match(tid):
        return jsonify(ok=False, message="ID format must be TUPM-YY-NNNN"), 400
    db = get_db()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    stu = q("SELECT * FROM students WHERE tupm_id=?", (tid,), one=True)
    if stu and stu["enrolled"]:
        return jsonify(ok=False, message="Already enrolled"), 409
    if stu:
        db.execute("UPDATE students SET enrolled=1, enrolled_at=?, full_name=COALESCE(NULLIF(?,''),full_name) WHERE id=?",
                   (now, name, stu["id"]))
    else:
        db.execute("INSERT INTO students(tupm_id, full_name, enrolled, enrolled_at) VALUES(?,?,1,?)",
                   (tid, name or None, now))
    db.commit()
    return jsonify(ok=True)


@app.post("/api/sessions")
@admin_required
def api_sessions():
    data = request.get_json(silent=True) or {}
    try:
        d = datetime.strptime(data.get("session_date", ""), "%Y-%m-%d").strftime("%Y-%m-%d")
        t = datetime.strptime(data.get("start_time", ""), "%H:%M").strftime("%H:%M")
        late = int(data.get("late_after_minutes", 15))
        assert 0 <= late <= 600
    except Exception:
        return jsonify(ok=False, message="Check date, time and late minutes"), 400
    db = get_db()
    db.execute("INSERT INTO class_sessions(session_date,start_time,late_after_minutes,is_open) VALUES(?,?,?,1)",
               (d, t, late))
    db.commit()
    return jsonify(ok=True)


@app.post("/api/sessions/<int:sid>/close")
@admin_required
def api_close(sid):
    db = get_db()
    db.execute("UPDATE class_sessions SET is_open=0 WHERE id=?", (sid,))
    db.commit()
    return jsonify(ok=True)


@app.post("/api/sessions/<int:sid>/open")
@admin_required
def api_reopen(sid):
    db = get_db()
    db.execute("UPDATE class_sessions SET is_open=1 WHERE id=?", (sid,))
    db.commit()
    return jsonify(ok=True)


@app.route("/api/attendance", methods=["PATCH", "POST"])
@admin_required
def api_attendance():
    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in STATUSES:
        return jsonify(ok=False, message="Bad status"), 400
    try:
        stu_id, ses_id = int(data["student_id"]), int(data["session_id"])
    except Exception:
        return jsonify(ok=False, message="Missing ids"), 400
    note = str(data.get("note", "")).strip()[:200]
    who = session.get("name")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    db = get_db()
    ex = q("SELECT id FROM attendance WHERE student_id=? AND session_id=?", (stu_id, ses_id), one=True)
    if ex:
        db.execute("UPDATE attendance SET status=?, edited_by=?, note=? WHERE id=?",
                   (status, who, note or f"edited {now}", ex["id"]))
    else:
        db.execute("INSERT INTO attendance(student_id,session_id,status,edited_by,note) VALUES(?,?,?,?,?)",
                   (stu_id, ses_id, status, who, note or f"edited {now}"))
    db.commit()
    return jsonify(ok=True)


if __name__ == "__main__":
    if not os.path.exists(DB):
        init_db()
        print("Created database. Admin login: admin / admin123")
    app.run(host="127.0.0.1", port=5000, debug=False)

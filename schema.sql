CREATE TABLE IF NOT EXISTS students (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tupm_id TEXT NOT NULL UNIQUE CHECK (tupm_id GLOB 'TUPM-[0-9][0-9]-[0-9][0-9][0-9][0-9]'),
  full_name TEXT,
  password_hash TEXT,
  enrolled INTEGER NOT NULL DEFAULT 0,
  enrolled_at TEXT
);
CREATE TABLE IF NOT EXISTS admins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS class_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_date TEXT NOT NULL,
  start_time TEXT NOT NULL,
  late_after_minutes INTEGER NOT NULL DEFAULT 15,
  is_open INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS attendance (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  student_id INTEGER NOT NULL REFERENCES students(id),
  session_id INTEGER NOT NULL REFERENCES class_sessions(id),
  status TEXT NOT NULL CHECK (status IN ('Present','Late','Absent','Excused')),
  scanned_at TEXT,
  edited_by TEXT,
  note TEXT,
  UNIQUE (student_id, session_id)
);

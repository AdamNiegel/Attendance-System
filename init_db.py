"""Create database / reset admin.  Usage: python init_db.py [username] [password]"""
import sys
from app import init_db
u = sys.argv[1] if len(sys.argv) > 1 else "admin"
p = sys.argv[2] if len(sys.argv) > 2 else "admin123"
init_db(u, p)
print(f"Database ready. Admin login: {u} / {p}")

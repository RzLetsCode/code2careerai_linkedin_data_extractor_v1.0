import sqlite3,os
from datetime import date,datetime
DB_PATH=os.path.join(os.path.dirname(os.path.dirname(__file__)),"outreach.db")
MAX_DAILY_SENDS=15
def _db():
    c=sqlite3.connect(DB_PATH)
    c.execute("CREATE TABLE IF NOT EXISTS outreach (url TEXT PRIMARY KEY,note TEXT NOT NULL,status TEXT NOT NULL,created_at TEXT NOT NULL)")
    return c
def init_db():
    c=_db(); c.commit(); c.close()
def is_contacted(url):
    if not url:return False
    c=_db(); x=c.execute("SELECT 1 FROM outreach WHERE url=?",(url,)).fetchone(); c.close(); return x is not None
def get_daily_count():
    c=_db(); x=c.execute("SELECT COUNT(*) FROM outreach WHERE substr(created_at,1,10)=?",(date.today().isoformat(),)).fetchone(); c.close(); return int(x[0])
def mark_contacted(url,note):
    c=_db()
    try:
        count=c.execute("SELECT COUNT(*) FROM outreach WHERE substr(created_at,1,10)=?",(date.today().isoformat(),)).fetchone()[0]
        if count>=MAX_DAILY_SENDS: raise ValueError("Daily handoff limit reached (15).")
        c.execute("INSERT INTO outreach VALUES (?,?,'handed_off',?)",(url,note,datetime.now().isoformat(timespec="seconds"))); c.commit()
    finally:c.close()

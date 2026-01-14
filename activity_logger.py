from db import get_db
from datetime import datetime, timedelta

def log_visit(request, page):
    # Get Malaysia time (UTC+8)
    malaysia_time = datetime.utcnow() + timedelta(hours=8)
    malaysia_time_str = malaysia_time.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO visits (ip, user_agent, page, visit_time)
        VALUES (?, ?, ?, ?)
    """, (
        request.remote_addr,
        request.headers.get("User-Agent"),
        page,
        malaysia_time_str  # store Malaysia time
    ))

    conn.commit()
    conn.close()

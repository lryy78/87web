from db import get_db

def get_live_count():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT COUNT(*) FROM visits
        WHERE visit_time >= datetime('now', '-5 minutes')
    """)

    count = c.fetchone()[0]
    conn.close()
    return count

def get_last_visitor():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        SELECT ip, visit_time
        FROM visits
        ORDER BY visit_time DESC
        LIMIT 1
    """)

    row = c.fetchone()
    conn.close()

    if row:
        return {
            "ip": row[0],
            "time": row[1]
        }
    return None

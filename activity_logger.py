from db import get_db

def log_visit(request, page):
    conn = get_db()
    c = conn.cursor()

    c.execute("""
        INSERT INTO visits (ip, user_agent, page)
        VALUES (?, ?, ?)
    """, (
        request.remote_addr,
        request.headers.get("User-Agent"),
        page
    ))

    conn.commit()
    conn.close()

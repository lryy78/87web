from flask import Flask, request, redirect, render_template, make_response, send_from_directory, url_for
from datetime import datetime
from zoneinfo import ZoneInfo
from datetime import date, timedelta

import os
import sqlite3
import uuid

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "uploads"
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_FILE = "chat.db"
USER_BIRTHDAYS = ["030605", "ry5678"]


# ---------- Database Helpers ----------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    # Users table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        birthday TEXT PRIMARY KEY,
        display_name TEXT NOT NULL
    )
    """)
    # Messages table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        time TEXT NOT NULL,
        birthday TEXT NOT NULL,
        text TEXT,
        file_path TEXT,
        active INTEGER DEFAULT 1,
        FOREIGN KEY (birthday) REFERENCES users (birthday)
    )
    """)

    # User activity table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_activity (
        id TEXT PRIMARY KEY,
        birthday TEXT NOT NULL,
        page TEXT NOT NULL,
        access_time TEXT NOT NULL,
        FOREIGN KEY (birthday) REFERENCES users (birthday)
    )
    """)

    # Drift bottle table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bottles (
        id TEXT PRIMARY KEY,
        birthday TEXT NOT NULL,
        text TEXT NOT NULL,
        file_path TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (birthday) REFERENCES users (birthday)
    )
    """)

    # Table to track which bottle a user has viewed each day
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bottle_views (
        id TEXT PRIMARY KEY,
        birthday TEXT NOT NULL,
        bottle_id TEXT NOT NULL,
        view_date TEXT NOT NULL,
        FOREIGN KEY (birthday) REFERENCES users (birthday),
        FOREIGN KEY (bottle_id) REFERENCES bottles (id)
    )
    """)



    # Check if 'active' column exists; if not, add it
    cur.execute("PRAGMA table_info(messages)")
    columns = [row["name"] for row in cur.fetchall()]
    if "active" not in columns:
        cur.execute("ALTER TABLE messages ADD COLUMN active INTEGER DEFAULT 1")
    conn.commit()
    conn.close()


init_db()


# ---------- Login ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        birthday = request.form.get("birthday")
        if birthday not in USER_BIRTHDAYS:
            # Track failed login attempt
            log_activity(f"unknown-{birthday}", "login_failed")
            return render_template("login.html", error="Invalid birthday")

        conn = get_db_connection()
        cur = conn.cursor()
        # Add user if not exists
        cur.execute("SELECT * FROM users WHERE birthday=?", (birthday,))
        user = cur.fetchone()
        if not user:
            default_name = "ry" if birthday == "ry5678" else "user"
            cur.execute("INSERT INTO users (birthday, display_name) VALUES (?, ?)", (birthday, default_name))
            conn.commit()
        conn.close()

        # Track successful login
        log_activity(birthday, "login_success")
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("birthday", birthday, max_age=31536000)
        return resp

    return render_template("login.html")

# ---------- message Chat ----------
@app.route("/message", methods=["GET", "POST"])
def message():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")
    
    log_activity(birthday, "message")  # Track dashboard visit

    conn = get_db_connection()
    cur = conn.cursor()

    # Fetch user info first
    cur.execute("SELECT display_name FROM users WHERE birthday=?", (birthday,))
    user = cur.fetchone()
    if not user:
        conn.close()
        return redirect("/")

    name = user["display_name"]

    # Log user activity
    now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    cur.execute(
        "INSERT INTO user_activity (id, birthday, page, access_time) VALUES (?, ?, ?, ?)",
        (uuid.uuid4().hex, birthday, 'message', now.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()

    if request.method == "POST":
        text = request.form.get("message")
        file = request.files.get("file")
        file_path = None

        if file and file.filename != "":
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            file_path = filename

        if text or file_path:
            now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
            cur.execute(
                "INSERT INTO messages (id, time, birthday, text, file_path) VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, now.strftime("%Y-%m-%d %H:%M:%S"), birthday, text, file_path)
            )
            conn.commit()
        conn.close()
        return redirect("/message")

    # Load active messages only
    cur.execute("""
        SELECT m.id, m.time, m.text, m.file_path, u.display_name
        FROM messages m
        JOIN users u ON m.birthday = u.birthday
        WHERE m.active = 1
        ORDER BY m.time DESC
    """)
    messages = cur.fetchall()
    conn.close()

    return render_template("message.html", name=name, messages=messages)



# ---------- Delete Message ----------
@app.route("/delete_message", methods=["POST"])
def delete_message():
    birthday = request.cookies.get("birthday")
    message_id = request.form.get("id")
    if not birthday or not message_id:
        return redirect("/message")

    conn = get_db_connection()
    cur = conn.cursor()
    # Delete only messages from this user
    cur.execute("SELECT file_path FROM messages WHERE id=? AND birthday=?", (message_id, birthday))
    msg = cur.fetchone()
    if msg:
        # Remove uploaded file if exists
        if msg["file_path"]:
            path = os.path.join(app.config['UPLOAD_FOLDER'], msg["file_path"])
            if os.path.exists(path):
                os.remove(path)
        cur.execute("UPDATE messages SET active=0 WHERE id=? AND birthday=?", (message_id, birthday))
        conn.commit()
    conn.close()
    return redirect("/message")


# ---------- Edit Name ----------
@app.route("/edit_name", methods=["POST"])
def edit_name():
    birthday = request.cookies.get("birthday")
    new_name = request.form.get("new_name", "").strip()
    if not birthday or not new_name:
        return redirect("/message")

    conn = get_db_connection()
    cur = conn.cursor()
    # Update user's name
    cur.execute("UPDATE users SET display_name=? WHERE birthday=?", (new_name, birthday))
    conn.commit()
    conn.close()

    return redirect("/message")


# ---------- Serve uploaded files ----------
@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/bottle", methods=["GET", "POST"])
def bottle():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")
    
    log_activity(birthday, "bottle")  # Track dashboard visit

    conn = get_db_connection()
    cur = conn.cursor()
    today_str = date.today().strftime("%Y-%m-%d")

    # --- Handle POST: send a new bottle ---
    if request.method == "POST":
        text = request.form.get("message")
        file = request.files.get("file")
        file_path = None

        if file and file.filename != "":
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(save_path)
            file_path = filename

        if text or file_path:
            now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
            cur.execute(
                "INSERT INTO bottles (id, birthday, text, file_path, created_at) VALUES (?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, birthday, text, file_path, now.strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()

    # --- Handle GET: Show one bottle for today ---
    # Check if user has already viewed a bottle today
    cur.execute("""
        SELECT bottle_id FROM bottle_views
        WHERE birthday=? AND view_date=?
    """, (birthday, today_str))
    view = cur.fetchone()

    bottle_to_show = None
    no_bottle = False

    if view:
        # Already viewed today, show the same bottle
        cur.execute("SELECT * FROM bottles WHERE id=?", (view["bottle_id"],))
        bottle_to_show = cur.fetchone()
    else:
        # Pick a random bottle from other users
        cur.execute("""
            SELECT * FROM bottles
            WHERE birthday != ?
            ORDER BY RANDOM()
            LIMIT 1
        """, (birthday,))
        bottle_to_show = cur.fetchone()

        if bottle_to_show:
            # Log that this user has viewed this bottle today
            cur.execute("""
                INSERT INTO bottle_views (id, birthday, bottle_id, view_date)
                VALUES (?, ?, ?, ?)
            """, (uuid.uuid4().hex, birthday, bottle_to_show["id"], today_str))
            conn.commit()
        else:
            no_bottle = True

    # --- Track which user's bottles have been picked up ---
    # Count views for this user's bottles
    cur.execute("""
        SELECT COUNT(*) as pickup_count FROM bottle_views bv
        JOIN bottles b ON bv.bottle_id = b.id
        WHERE b.birthday=?
    """, (birthday,))
    picked_count = cur.fetchone()["pickup_count"]

    conn.close()
    return render_template("bottle.html",
                           bottle=bottle_to_show,
                           no_bottle=no_bottle,
                           picked_count=picked_count)

@app.route("/dashboard")
def dashboard():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")
    
    log_activity(birthday, "dashboard")  # Track dashboard visit

    conn = get_db_connection()
    cur = conn.cursor()

    # name
    cur.execute("SELECT display_name FROM users WHERE birthday=?", (birthday,))
    user = cur.fetchone()
    name = user["display_name"] if user else "User"

    # Count messages
    cur.execute("SELECT COUNT(*) AS cnt FROM messages WHERE birthday=?", (birthday,))
    messages_count = cur.fetchone()["cnt"]

    # Count bottles sent
    cur.execute("SELECT COUNT(*) AS cnt FROM bottles WHERE birthday=?", (birthday,))
    bottles_count = cur.fetchone()["cnt"]

    # Count bottles picked up
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM bottle_views bv
        JOIN bottles b ON bv.bottle_id = b.id
        WHERE b.birthday=?
    """, (birthday,))
    picked_count = cur.fetchone()["cnt"]

    # Recent activity (last 5)
    cur.execute("""
        SELECT page, access_time FROM user_activity
        WHERE birthday=?
        ORDER BY access_time DESC
        LIMIT 5
    """, (birthday,))
    recent_activity = cur.fetchall()

    conn.close()

    return render_template(
        "dashboard.html",
        name=name,
        messages_count=messages_count,
        bottles_count=bottles_count,
        picked_count=picked_count,
        recent_activity=recent_activity
    )


def log_activity(birthday, page):
    """Log user activity, even failed login attempts."""
    conn = get_db_connection()
    cur = conn.cursor()
    now = datetime.utcnow().replace(tzinfo=ZoneInfo("UTC")).astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
    cur.execute(
        "INSERT INTO user_activity (id, birthday, page, access_time) VALUES (?, ?, ?, ?)",
        (uuid.uuid4().hex, birthday, page, now.strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)



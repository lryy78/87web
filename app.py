from flask import Flask, request, redirect, make_response
from datetime import datetime
import uuid
import os

app = Flask(__name__)

# Spotify redirect link
TARGET_URL = "https://open.spotify.com/user/22q4tinbfp6um4otx355523dq?si=a9fbfe58c82c4aa3"

# Absolute path to log file
LOG_FILE = os.path.join(os.path.dirname(__file__), "clicks.log")

# Function to log visitor info
def log_click(visitor_id):
    try:
        time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ip = request.headers.get("X-Forwarded-For", request.remote_addr)
        ua = request.headers.get("User-Agent")

        with open(LOG_FILE, "a") as f:
            f.write(f"{time} | {visitor_id} | {ip} | {ua}\n")

        # Optional: print to console for Render logs
        print(f"[LOG] {time} | {visitor_id} | {ip} | {ua}")

    except Exception as e:
        print(f"[ERROR] Logging failed: {e}")

# Main tracking route
@app.route("/")
def track():
    visitor_id = request.cookies.get("visitor_id")

    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    log_click(visitor_id)

    response = make_response(redirect(TARGET_URL))
    response.set_cookie(
        "visitor_id",
        visitor_id,
        max_age=60*60*24*365,
        httponly=True,
        samesite="Lax"
    )
    return response

# Stats route to see total and unique clicks
@app.route("/stats")
def stats():
    if not os.path.exists(LOG_FILE):
        return "No clicks yet."

    total_clicks = 0
    unique_visitors = set()

    with open(LOG_FILE, "r") as f:
        for line in f:
            total_clicks += 1
            visitor_id = line.split("|")[1].strip()
            unique_visitors.add(visitor_id)

    return (
        f"Total accesses: {total_clicks}<br>"
        f"Unique visitors: {len(unique_visitors)}"
    )

# Render deployment uses this
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

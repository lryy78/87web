from flask import Flask, request, redirect, make_response
from datetime import datetime
import uuid
import os

app = Flask(__name__)

# The Spotify link you want to redirect users to
TARGET_URL = "https://open.spotify.com/user/22q4tinbfp6um4otx355523dq?si=a9fbfe58c82c4aa3"
LOG_FILE = "clicks.log"

# Function to log each access
def log_click(visitor_id):
    time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    # Get real IP even if behind a proxy (ngrok, Render)
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    ua = request.headers.get("User-Agent")

    with open(LOG_FILE, "a") as f:
        f.write(f"{time} | {visitor_id} | {ip} | {ua}\n")

# Main tracking route
@app.route("/")
def track():
    visitor_id = request.cookies.get("visitor_id")

    # Assign a unique ID to first-time visitors
    if not visitor_id:
        visitor_id = str(uuid.uuid4())

    # Log every access
    log_click(visitor_id)

    # Redirect to Spotify and set a cookie
    response = make_response(redirect(TARGET_URL))
    response.set_cookie(
        "visitor_id",
        visitor_id,
        max_age=60 * 60 * 24 * 365,  # 1 year
        httponly=True,
        samesite="Lax"
    )
    return response

# Stats page for total clicks & unique visitors
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

# Use Render's port and host for production
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render provides PORT automatically
    app.run(host="0.0.0.0", port=port)

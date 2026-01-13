from flask import Flask, request, redirect
from datetime import datetime

app = Flask(__name__)

TARGET_URL = "https://open.spotify.com/user/22q4tinbfp6um4otx355523dq?si=a9fbfe58c82c4aa3"
LOG_FILE = "clicks.log"

@app.route("/")
def track_click():
    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ip = request.remote_addr
    user_agent = request.headers.get("User-Agent")

    log_line = f"{time} | IP: {ip} | UA: {user_agent}\n"

    with open(LOG_FILE, "a") as f:
        f.write(log_line)

    print("SPOTIFY LINK CLICKED")

    return redirect(TARGET_URL)

if __name__ == "__main__":
    app.run(port=8080)

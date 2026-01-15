# main.py
import os
from flask import Flask
from admin.routes import admin_bp
from landing.routes import landing_bp

from chat.routes import chat_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "landing", "templates")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "chat", "uploads")


app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = "SuperSecretSessionKey"

# ---------------- Register Blueprints ----------------
app.register_blueprint(admin_bp)
app.register_blueprint(landing_bp, url_prefix="/")  # "/" prefix
app.register_blueprint(chat_bp, url_prefix="/chat") 



# Ensure the folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- Run App ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

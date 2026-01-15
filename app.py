from flask import Flask
from chat import chat_bp

app = Flask(__name__)
app.secret_key = "your-secret-key"
app.config["UPLOAD_FOLDER"] = "chat/uploads"
import os
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Register chat blueprint
app.register_blueprint(chat_bp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port, debug=True)

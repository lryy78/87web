from flask import Flask
from db import init_db
from landing.routes import landing_bp

app = Flask(__name__)

# Init database once
init_db()

# Register landing blueprint
app.register_blueprint(landing_bp)

# Main app routes (login, dashboard, etc)
# are handled in app.py separately

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

from flask import Blueprint

# Create the blueprint
chat_bp = Blueprint(
    "chat",
    __name__,
    template_folder="templates",
    static_folder="uploads"
)

# Import routes AFTER defining blueprint
from . import routes

from flask import Blueprint, render_template, request
from activity_logger import log_visit
from activity_service import get_live_count, get_last_visitor

landing_bp = Blueprint(
    "landing",
    __name__,
    template_folder="templates"
)

@landing_bp.route("/")
def landing():
    log_visit(request, "landing")

    live_count = get_live_count()
    last_visitor = get_last_visitor()

    return render_template(
        "landing.html",
        live_count=live_count,
        last_visitor=last_visitor
    )

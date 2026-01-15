from flask import Blueprint, render_template, request, redirect, url_for, session
from supabase_client import supabase

admin_bp = Blueprint(
    "admin",
    __name__,
    template_folder="templates",
    url_prefix="/admin"
)

ADMIN_KEY = "secret-5678"

# ---------------- Login ----------------
@admin_bp.route("/", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("secret_key") == ADMIN_KEY:
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        return render_template("admin_login.html", error="Invalid secret key")
    return render_template("admin_login.html")


@admin_bp.route("/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.admin_login"))


# ---------------- Dashboard (OLD UI) ----------------
@admin_bp.route("/dashboard")
def dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    # EXACT SAME AS OLD SQLITE STRUCTURE
    chat_tables = [
        "users",
        "messages",
        "user_activity",
        "bottles",
        "bottle_views"
    ]

    activity_tables = [
        "visits"
    ]

    return render_template(
        "dashboard.html",   # ⬅️ OLD TEMPLATE
        chat_tables=chat_tables,
        activity_tables=activity_tables,
        name="Admin"
    )


# ---------------- View Table ----------------
@admin_bp.route("/table/<db_name>/<table_name>")
def view_table(db_name, table_name):
    if not session.get("admin_logged_in"):
        return redirect(url_for("admin.admin_login"))

    try:
        query = supabase.table(table_name).select("*")

        # SAME ORDERING LOGIC AS SQLITE
        if table_name == "messages":
            query = query.order("time", desc=True)
        elif table_name == "user_activity":
            query = query.order("access_time", desc=True)
        elif table_name == "bottles":
            query = query.order("created_at", desc=True)
        elif table_name == "visits":
            query = query.order("visit_time", desc=True)
        else:
            query = query.order("id", desc=True)

        resp = query.limit(500).execute()
        rows = resp.data or []
        columns = list(rows[0].keys()) if rows else []

    except Exception as e:
        print("[ADMIN TABLE ERROR]", e)
        rows = []
        columns = []

    return render_template(
        "table_view.html",
        db_name=db_name,
        table_name=table_name,
        rows=rows,
        columns=columns,
        can_delete=(db_name == "chat")
    )

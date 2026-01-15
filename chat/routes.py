from flask import (
    request,
    redirect,
    render_template,
    make_response,
    send_from_directory,
    current_app
)
from datetime import datetime, date
from zoneinfo import ZoneInfo
import os
import uuid

from . import chat_bp
from supabase_client import supabase

USER_BIRTHDAYS = ["030605", "ry5678"]

MY_TZ = ZoneInfo("Asia/Kuala_Lumpur")


# ---------- Activity Logger ----------
def log_activity(birthday, page):
    """
    Persist activity logs safely.
    - Store timezone-aware datetime
    - Supabase/Postgres will normalize to UTC internally
    """
    now_my = datetime.now(MY_TZ).isoformat()

    supabase.table("user_activity").insert({
        "id": uuid.uuid4().hex,
        "birthday": birthday,
        "page": page,
        "access_time": now_my
    }).execute()


# ---------- Login ----------
@chat_bp.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        birthday = request.form.get("birthday")

        if birthday not in USER_BIRTHDAYS:
            log_activity(f"unknown-{birthday}", "login_failed")
            return render_template("login.html", error="Invalid birthday")

        user_resp = supabase.table("users").select("*").eq("birthday", birthday).execute()
        user = user_resp.data[0] if user_resp.data else None

        if not user:
            supabase.table("users").insert({
                "birthday": birthday,
                "display_name": "ry" if birthday == "ry5678" else "user"
            }).execute()

        log_activity(birthday, "login_success")

        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("birthday", birthday, max_age=31536000)
        return resp

    return render_template("login.html")


# ---------- Message ----------
@chat_bp.route("/message", methods=["GET", "POST"])
def message():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")

    log_activity(birthday, "message")

    user_resp = supabase.table("users").select("display_name").eq("birthday", birthday).execute()
    name = user_resp.data[0]["display_name"] if user_resp.data else "User"

    if request.method == "POST":
        text = request.form.get("message")
        file = request.files.get("file")
        file_path = None

        if file and file.filename:
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            file_path = filename

        if text or file_path:
            supabase.table("messages").insert({
                "id": uuid.uuid4().hex,
                "time": datetime.now(MY_TZ),
                "birthday": birthday,
                "text": text,
                "file_path": file_path,
                "active": True
            }).execute()

        return redirect("/message")

    messages_resp = (
        supabase.table("messages")
        .select("*")
        .eq("active", True)
        .order("time", desc=True)
        .limit(500)
        .execute()
    )
    messages = messages_resp.data or []

    birthday_list = [m["birthday"] for m in messages]
    users_resp = supabase.table("users").select("birthday, display_name").in_("birthday", birthday_list).execute()
    user_dict = {u["birthday"]: u["display_name"] for u in users_resp.data} if users_resp.data else {}

    for m in messages:
        m["display_name"] = user_dict.get(m["birthday"], "Unknown")

    return render_template("message.html", name=name, messages=messages)


# ---------- Upload Serving ----------
@chat_bp.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)


# ---------- Dashboard ----------
@chat_bp.route("/dashboard")
def dashboard():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")

    log_activity(birthday, "dashboard")

    user_resp = supabase.table("users").select("display_name").eq("birthday", birthday).execute()
    name = user_resp.data[0]["display_name"] if user_resp.data else "User"

    messages_count = len(
        supabase.table("messages").select("id").eq("birthday", birthday).execute().data or []
    )

    bottles_count = len(
        supabase.table("bottles").select("id").eq("birthday", birthday).execute().data or []
    )

    recent_activity = (
        supabase.table("user_activity")
        .select("page, access_time")
        .eq("birthday", birthday)
        .order("access_time", desc=True)
        .limit(5)
        .execute()
        .data or []
    )

    # Convert UTC → Malaysia time for display
    for a in recent_activity:
        dt = datetime.fromisoformat(a["access_time"])
        a["access_time"] = (
            dt.astimezone(MY_TZ)
            .strftime("%Y-%m-%d %H:%M:%S")
        )


    return render_template(
        "dashboard.html",
        name=name,
        messages_count=messages_count,
        bottles_count=bottles_count,
        recent_activity=recent_activity
    )


# ---------- Bottle ----------
@chat_bp.route("/bottle", methods=["GET", "POST"])
def bottle():
    birthday = request.cookies.get("birthday")
    if not birthday:
        return redirect("/")

    log_activity(birthday, "bottle")
    today_str = date.today().strftime("%Y-%m-%d")

    if request.method == "POST":
        text = request.form.get("message")
        file = request.files.get("file")
        file_path = None

        if file and file.filename:
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], filename)
            file.save(save_path)
            file_path = filename

        if text or file_path:
            supabase.table("bottles").insert({
                "id": uuid.uuid4().hex,
                "birthday": birthday,
                "text": text,
                "file_path": file_path,
                "created_at": datetime.now(MY_TZ)
            }).execute()

    view_resp = (
        supabase.table("bottle_views")
        .select("*")
        .eq("birthday", birthday)
        .eq("view_date", today_str)
        .execute()
    )
    view = view_resp.data[0] if view_resp.data else None

    bottle_to_show = None
    no_bottle = False

    if view:
        bottle_to_show = supabase.table("bottles").select("*").eq("id", view["bottle_id"]).execute().data[0]
    else:
        bottle_resp = (
            supabase.table("bottles")
            .select("*")
            .neq("birthday", birthday)
            .order("created_at", desc=False)
            .limit(1)
            .execute()
        )
        bottle_to_show = bottle_resp.data[0] if bottle_resp.data else None

        if bottle_to_show:
            supabase.table("bottle_views").insert({
                "id": uuid.uuid4().hex,
                "birthday": birthday,
                "bottle_id": bottle_to_show["id"],
                "view_date": today_str
            }).execute()
        else:
            no_bottle = True

    picked_count = 0
    picked_resp = supabase.table("bottle_views").select("*").execute()
    for p in picked_resp.data or []:
        b = supabase.table("bottles").select("birthday").eq("id", p["bottle_id"]).execute()
        if b.data and b.data[0]["birthday"] == birthday:
            picked_count += 1

    return render_template(
        "bottle.html",
        bottle=bottle_to_show,
        no_bottle=no_bottle,
        picked_count=picked_count
    )


# ---------- Delete Message ----------
@chat_bp.route("/delete_message", methods=["POST"])
def delete_message():
    birthday = request.cookies.get("birthday")
    message_id = request.form.get("id")

    if not birthday or not message_id:
        return redirect("/message")

    msg_resp = supabase.table("messages").select("*").eq("id", message_id).eq("birthday", birthday).execute()
    msg = msg_resp.data[0] if msg_resp.data else None

    if msg and msg.get("file_path"):
        path = os.path.join(current_app.config["UPLOAD_FOLDER"], msg["file_path"])
        if os.path.exists(path):
            os.remove(path)

    supabase.table("messages").update({"active": False}).eq("id", message_id).eq("birthday", birthday).execute()
    return redirect("/message")

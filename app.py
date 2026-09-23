import os
import re
from functools import wraps
from flask import Flask, request, jsonify, render_template, session
from ingestion_pipeline import ingestion_pipeline
from rag import ask_question
from rag import load_vector_db
import traceback
from database import (
    init_db,
    save_chat,
    get_all_chats,
    get_chat,
    save_message,
    get_recent_messages,
    delete_chat,
    rename_chat,
    save_feedback,
    update_chat_status,
    create_user,
    verify_user,
    get_user_by_id,
    get_user_by_username_or_email
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key-docmind-rag-12345")
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
init_db()


# ─── Auth helpers ───

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"status": "error", "message": "Authentication required."}), 401
        return f(*args, **kwargs)
    return decorated


def current_user_id():
    return session.get("user_id")


def get_current_user_chat(chat_id):
    chat = get_chat(chat_id)
    if chat is None or chat["user_id"] != current_user_id():
        return None
    return chat


# ─── Auth routes ───

@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"status": "error", "message": "All fields are required."}), 400

    if len(username) < 3 or len(username) > 30:
        return jsonify({"status": "error", "message": "Username must be 3–30 characters."}), 400

    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return jsonify({"status": "error", "message": "Username can only contain letters, numbers, and underscores."}), 400

    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        return jsonify({"status": "error", "message": "Invalid email address."}), 400

    if len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters."}), 400

    if get_user_by_username_or_email(username) or get_user_by_username_or_email(email):
        return jsonify({"status": "error", "message": "Username or email already taken."}), 409

    user = create_user(username, email, password)
    if not user:
        return jsonify({"status": "error", "message": "Could not create account. Try a different username or email."}), 409

    session["user_id"] = user["user_id"]
    session["username"] = user["username"]

    return jsonify({
        "status": "success",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"]
        }
    })


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("identifier") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"status": "error", "message": "Please provide username/email and password."}), 400

    user = verify_user(identifier, password)
    if not user:
        return jsonify({"status": "error", "message": "Invalid credentials."}), 401

    session["user_id"] = user["user_id"]
    session["username"] = user["username"]

    return jsonify({
        "status": "success",
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"]
        }
    })


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "success"})


@app.route("/me", methods=["GET"])
def me():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"logged_in": False})

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({"logged_in": False})

    return jsonify({
        "logged_in": True,
        "user": {
            "user_id": user["user_id"],
            "username": user["username"],
            "email": user["email"]
        }
    })


# ─── App routes ───


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
@login_required
def upload_file():

    # Check if file exists in request
    if "file" not in request.files:
        return jsonify({
            "status": "error",
            "message": "No file uploaded."
        }), 400

    file = request.files["file"]

    # Check if user selected a file
    if file.filename == "":
        return jsonify({
            "status": "error",
            "message": "Please select a file."
        }), 400

   # Allow TXT and PDF files
    allowed_extensions = {".txt", ".pdf"}

    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
         return jsonify({
        "status": "error",
        "message": "Only .txt and .pdf files are allowed."
    }), 400

    try:
        # Save uploaded file
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
        file.save(filepath)

        # Create embeddings
        chat_id, db_path = ingestion_pipeline(filepath)
        load_vector_db(db_path)
        save_chat(
            chat_id,
            file.filename,
            db_path,
            user_id=current_user_id()
        )

        session["chat_id"] = chat_id
        session["db_path"] = db_path

        return jsonify({
        "status": "success",
        "message": f"{file.filename} uploaded successfully!",
        "chat_id": chat_id
         })


    except Exception as e:
        traceback.print_exc()

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/chat", methods=["POST"])
@login_required
def chat():
    if "chat_id" not in session:
        return jsonify({
            "status": "error",
            "message": "Please upload a file first."
        }), 400

    data = request.get_json()

    if not data:
        return jsonify({
            "status": "error",
            "message": "No JSON received."
        }), 400

    question = data.get("question")

    if not question:
        return jsonify({
            "status": "error",
            "message": "Question is required."
        }), 400

    try:

        chat_id = session["chat_id"]
        db_path = session["db_path"]

        # Load current user's vector DB
        load_vector_db(db_path)

        mode = data.get("mode", "rag")
        if mode not in {"rag", "reasoning"}:
            return jsonify({"status": "error", "message": "Unsupported assistant mode."}), 400

        answer = ask_question(question, mode)

        return jsonify(answer)

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
    

@app.route("/history", methods=["GET"])
@login_required
def history():

    view = request.args.get("view", "recent")
    if view not in {"recent", "pinned", "archived"}:
        return jsonify({"status": "error", "message": "Unsupported chat view."}), 400

    chats = get_all_chats(view, user_id=current_user_id())

    result = []

    for chat in chats:

        result.append({
            "chat_id": chat["chat_id"],
            "title": chat["title"],
            "filename": chat["filename"],
            "is_pinned": bool(chat["is_pinned"]),
            "is_archived": bool(chat["is_archived"])
        })

    return jsonify(result)

@app.route("/chat/<chat_id>", methods=["GET"])
@login_required
def open_chat(chat_id):

    chat = get_current_user_chat(chat_id)

    if chat is None:
        return jsonify({
            "status":"error",
            "message":"Chat not found."
        }),404

    load_vector_db(chat["db_path"])

    session["chat_id"] = chat["chat_id"]
    session["db_path"] = chat["db_path"]

    return jsonify({
        "status":"success",
        "chat_id":chat["chat_id"],
        "title":chat["title"],
        "is_pinned": bool(chat["is_pinned"]),
        "is_archived": bool(chat["is_archived"])
    })


@app.route("/messages/<chat_id>", methods=["GET"])
@login_required
def messages(chat_id):

    if get_current_user_chat(chat_id) is None:
        return jsonify({
            "status": "error",
            "message": "Chat not found."
        }), 404

    rows = get_recent_messages(chat_id,10)

    result = []

    for row in rows:

        result.append({

            "role": row["role"],

            "content": row["content"]

        })

    return jsonify(result)


@app.route("/new_chat", methods=["POST"])
@login_required
def new_chat():

    session.pop("chat_id", None)
    session.pop("db_path", None)

    return jsonify({

        "status":"success"

    })

@app.route("/delete_chat", methods=["POST"])
@login_required
def delete_chat_route():

    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")

    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required."}), 400

    if get_current_user_chat(chat_id) is None:
        return jsonify({"status": "error", "message": "Chat not found."}), 404

    if not delete_chat(chat_id):
        return jsonify({"status": "error", "message": "Chat not found."}), 404

    if session.get("chat_id") == chat_id:
        session.pop("chat_id", None)
        session.pop("db_path", None)

    return jsonify({

        "status":"success"

    })


@app.route("/chat_status", methods=["POST"])
@login_required
def chat_status():
    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    action = data.get("action")

    if not chat_id or action not in {"pin", "unpin", "archive", "unarchive"}:
        return jsonify({"status": "error", "message": "Invalid chat status request."}), 400

    if get_current_user_chat(chat_id) is None:
        return jsonify({"status": "error", "message": "Chat not found or unavailable."}), 404

    if not update_chat_status(chat_id, action):
        return jsonify({"status": "error", "message": "Chat not found or unavailable."}), 404

    if action == "archive" and session.get("chat_id") == chat_id:
        session.pop("chat_id", None)
        session.pop("db_path", None)

    return jsonify({"status": "success"})


@app.route("/feedback", methods=["POST"])
@login_required
def feedback():
    data = request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    answer = data.get("answer")
    rating = data.get("rating")

    if not chat_id or not answer or rating not in {"up", "down"}:
        return jsonify({"status": "error", "message": "Invalid feedback."}), 400

    if get_current_user_chat(chat_id) is None:
        return jsonify({"status": "error", "message": "Chat not found."}), 404

    save_feedback(chat_id, answer, rating)
    return jsonify({"status": "success"})

@app.route("/rename_chat", methods=["POST"])
@login_required
def rename_chat_route():

    data=request.get_json(silent=True) or {}
    chat_id = data.get("chat_id")
    title = (data.get("title") or "").strip()

    if not chat_id or not title:
        return jsonify({"status": "error", "message": "Chat ID and title are required."}), 400

    if get_current_user_chat(chat_id) is None:
        return jsonify({"status": "error", "message": "Chat not found."}), 404

    rename_chat(chat_id, title)

    return jsonify({

        "status":"success"

    })

if __name__ == "__main__":
    app.run(debug=True)

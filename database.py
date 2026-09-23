import sqlite3
import shutil
import os
from werkzeug.security import generate_password_hash, check_password_hash
DATABASE = "txtgpt.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats(
        chat_id TEXT PRIMARY KEY,
        title TEXT,
        filename TEXT,
        db_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(chat_id) REFERENCES chats(chat_id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_feedback(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id TEXT NOT NULL,
        answer TEXT NOT NULL,
        rating TEXT NOT NULL CHECK(rating IN ('up', 'down')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    columns = {row[1] for row in cursor.execute("PRAGMA table_info(chats)")}
    if "is_pinned" not in columns:
        cursor.execute("ALTER TABLE chats ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")
    if "is_archived" not in columns:
        cursor.execute("ALTER TABLE chats ADD COLUMN is_archived INTEGER NOT NULL DEFAULT 0")
    if "user_id" not in columns:
        cursor.execute("ALTER TABLE chats ADD COLUMN user_id INTEGER")
    conn.commit()

    conn.close()



def create_user(username, email, password):
    conn = get_connection()
    try:
        conn.execute("""
            INSERT INTO users(username, email, password_hash)
            VALUES (?, ?, ?)
        """, (username, email, generate_password_hash(password)))
        conn.commit()
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return user
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username_or_email(identifier):
    conn = get_connection()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ? OR email = ?",
        (identifier, identifier)
    ).fetchone()
    conn.close()
    return user


def get_user_by_id(user_id):
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def verify_user(identifier, password):
    user = get_user_by_username_or_email(identifier)
    if user and check_password_hash(user["password_hash"], password):
        return user
    return None




def save_chat(chat_id, filename, db_path, user_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chats(chat_id, title, filename, db_path, user_id)
        VALUES (?, ?, ?, ?, ?)
    """, (chat_id, filename, filename, db_path, user_id))
    conn.commit()
    conn.close()

def get_all_chats(view="recent", user_id=None):
    conn = get_connection()

    base = "SELECT * FROM chats WHERE"
    params = []

    if user_id is not None:
        base += " user_id = ? AND"
        params.append(user_id)

    if view == "pinned":
        base += " is_pinned = 1 AND is_archived = 0"
    elif view == "archived":
        base += " is_archived = 1"
    else:
        base += " is_archived = 0"

    base += " ORDER BY created_at DESC"
    chats = conn.execute(base, params).fetchall()
    conn.close()
    return chats


def get_chat(chat_id):

    conn = get_connection()

    chat = conn.execute(
        """
        SELECT *
        FROM chats
        WHERE chat_id = ?
        """,
        (chat_id,)
    ).fetchone()

    conn.close()

    return chat

def save_message(chat_id, role, content):

    conn = get_connection()

    conn.execute("""

    INSERT INTO messages(
        chat_id,
        role,
        content
    )

    VALUES(?,?,?)

    """,(chat_id, role, content))

    conn.commit()

    conn.close()

def get_recent_messages(chat_id, limit=10):

    conn = get_connection()

    messages = conn.execute(
        """
        SELECT role, content
        FROM messages
        WHERE chat_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (chat_id, limit)
    ).fetchall()

    conn.close()

    # Reverse because SQL returns newest first
    return list(reversed(messages))


def save_feedback(chat_id, answer, rating):
    conn = get_connection()
    conn.execute("""
        INSERT INTO message_feedback(chat_id, answer, rating)
        VALUES (?, ?, ?)
    """, (chat_id, answer, rating))
    conn.commit()
    conn.close()



def delete_chat(chat_id):

    conn = get_connection()

    # Pehle db_path nikal lo
    chat = conn.execute(
        """
        SELECT db_path
        FROM chats
        WHERE chat_id = ?
        """,
        (chat_id,)
    ).fetchone()

    if chat:

        db_path = chat["db_path"]

        # Messages delete
        conn.execute(
            """
            DELETE FROM messages
            WHERE chat_id = ?
            """,
            (chat_id,)
        )

        # Chat delete
        conn.execute(
            """
            DELETE FROM chats
            WHERE chat_id = ?
            """,
            (chat_id,)
        )

        conn.commit()

        # Vector DB Folder delete
        if os.path.exists(db_path):
            shutil.rmtree(db_path, ignore_errors=True)

    conn.close()
    return chat is not None


def update_chat_status(chat_id, action):
    conn = get_connection()

    if action == "pin":
        query = "UPDATE chats SET is_pinned = 1 WHERE chat_id = ? AND is_archived = 0"
    elif action == "unpin":
        query = "UPDATE chats SET is_pinned = 0 WHERE chat_id = ?"
    elif action == "archive":
        query = "UPDATE chats SET is_archived = 1, is_pinned = 0 WHERE chat_id = ?"
    elif action == "unarchive":
        query = "UPDATE chats SET is_archived = 0 WHERE chat_id = ?"
    else:
        conn.close()
        return False

    cursor = conn.execute(query, (chat_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def rename_chat(chat_id, title):

    conn = get_connection()

    conn.execute(
        """
        UPDATE chats
        SET title = ?
        WHERE chat_id = ?
        """,
        (title, chat_id)
    )

    conn.commit()

    conn.close()

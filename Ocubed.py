
import os
import re
import sqlite3
import secrets
from pathlib import Path
from functools import wraps
from datetime import datetime, timezone

from flask import (
    Flask, render_template_string, request, redirect,
    url_for, session, flash, g
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get(
    "OCUBED_SECRET_KEY", secrets.token_hex(32)
)

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "ocubed.db"
UPLOAD_FOLDER = BASE_DIR / "static" / "profile_pictures"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 3 * 1024 * 1024
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


# ---------------- DATABASE ----------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(str(DB_PATH))
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def create_tables():
    db = sqlite3.connect(str(DB_PATH))
    db.execute("PRAGMA foreign_keys = ON")

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    db.execute("""
        CREATE TABLE IF NOT EXISTS follows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_id INTEGER NOT NULL,
            followed_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(follower_id, followed_id),
            CHECK(follower_id != followed_id),
            FOREIGN KEY (follower_id) REFERENCES users(id),
            FOREIGN KEY (followed_id) REFERENCES users(id)
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            post_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, post_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    

    columns = {
        row[1] for row in db.execute(
            "PRAGMA table_info(users)"
        ).fetchall()
    }

    additions = {
        "display_name": "TEXT DEFAULT ''",
        "bio": "TEXT DEFAULT ''",
        "profile_picture": "TEXT DEFAULT ''",
    }

    for name, definition in additions.items():
        if name not in columns:
            db.execute(
                f"ALTER TABLE users ADD COLUMN {name} {definition}"
            )

    db.commit()
    db.close()


create_tables()


# ---------------- SECURITY / HELPERS ----------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in first.")
            return redirect(url_for("login"))
        return function(*args, **kwargs)
    return wrapper


def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_db().execute(
        "SELECT * FROM users WHERE id = ?", (user_id,)
    ).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def allowed_file(filename):
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


# ---------------- DESIGN ----------------

STYLE = """
<style>
* {
    box-sizing: border-box;
}

:root {
    --bg: #0c0815;
    --panel: #171023;
    --panel-hover: #211532;
    --border: #302040;
    --purple: #a855f7;
    --purple-light: #d8b4fe;
    --text: #f8f4ff;
    --muted: #a99bbd;
}

body {
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
    line-height: 1.65;
    font-size: 15px;
}

a {
    color: var(--purple-light);
    text-decoration: none;
    transition: color 0.2s ease;
}

a:hover {
    color: #ffffff;
}

nav {
    position: sticky;
    top: 0;
    z-index: 10;
    background: rgba(23, 16, 35, 0.96);
    backdrop-filter: blur(14px);
    border-bottom: 1px solid var(--border);
    padding: 14px 5%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 12px;
}

.brand {
    color: var(--purple-light);
    font-size: 28px;
    font-weight: 800;
    letter-spacing: -1px;
}

nav div {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
}

nav div a {
    padding: 8px 12px;
    border-radius: 9px;
    color: #ded2ed;
    font-size: 14px;
    font-weight: 600;
}

nav div a:hover {
    background: var(--panel-hover);
    color: white;
}

main {
    width: 100%;
    max-width: 780px;
    margin: 34px auto;
    padding: 0 20px;
    min-height: 65vh;
}

h1, h2, h3 {
    line-height: 1.3;
    letter-spacing: -0.4px;
}

h1 {
    font-size: clamp(25px, 4vw, 34px);
    margin-top: 0;
}

h2 {
    font-size: 23px;
}

h3 {
    font-size: 18px;
}

p {
    overflow-wrap: anywhere;
}

.card {
    background: linear-gradient(145deg, #1b1329, #151020);
    border: 1px solid var(--border);
    padding: 24px;
    border-radius: 19px;
    margin-bottom: 20px;
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.15);
    transition: border-color 0.2s ease;
}

.card:hover {
    border-color: #49305f;
}

.card h1:last-child,
.card h2:last-child,
.card h3:last-child {
    margin-bottom: 0;
}

input, textarea {
    display: block;
    width: 100%;
    padding: 13px 15px;
    margin: 9px 0 18px;
    border-radius: 11px;
    border: 1px solid #413052;
    background: #0e0a17;
    color: var(--text);
    font: inherit;
    outline: none;
    transition: border-color 0.2s, box-shadow 0.2s;
}

input:focus, textarea:focus {
    border-color: var(--purple);
    box-shadow: 0 0 0 3px rgba(168, 85, 247, 0.13);
}

input::placeholder, textarea::placeholder {
    color: #81728f;
}

input[type="file"] {
    padding: 10px;
}

textarea {
    min-height: 120px;
    resize: vertical;
}

label {
    display: block;
    color: #e6d9f5;
    font-weight: 600;
    font-size: 14px;
}

button, .button {
    display: inline-block;
    background: linear-gradient(135deg, #b05cff, #8737df);
    color: white;
    border: 1px solid transparent;
    border-radius: 11px;
    padding: 11px 19px;
    cursor: pointer;
    font-weight: 700;
    font-size: 14px;
    font-family: inherit;
    text-align: center;
    box-shadow: 0 4px 14px rgba(143, 55, 223, 0.18);
    transition: transform 0.2s, box-shadow 0.2s, filter 0.2s;
}

button:hover, .button:hover {
    color: white;
    filter: brightness(1.12);
    transform: translateY(-1px);
    box-shadow: 0 6px 18px rgba(143, 55, 223, 0.28);
}

button:active, .button:active {
    transform: translateY(0);
}

.muted {
    color: var(--muted);
    font-size: 13px;
}

.notice {
    padding: 13px 16px;
    background: #241631;
    border: 1px solid #54346d;
    border-radius: 12px;
    color: #e9d5ff;
    overflow-wrap: anywhere;
}

.person {
    display: flex;
    gap: 16px;
    align-items: center;
}

.person > div {
    min-width: 0;
}

.avatar {
    width: 76px;
    height: 76px;
    flex-shrink: 0;
    border-radius: 50%;
    object-fit: cover;
    background: linear-gradient(135deg, #a855f7, #4c1d95);
    border: 2px solid #71429b;
}

.card .person h1 {
    margin-bottom: 3px;
}

.card .person p {
    margin-top: 0;
}

hr {
    border: 0;
    border-top: 1px solid var(--border);
    margin: 22px 0;
}

footer {
    text-align: center;
    color: #9281a6;
    padding: 28px 16px;
    border-top: 1px solid var(--border);
    font-size: 13px;
}

@media (max-width: 600px) {
    nav {
        padding: 13px 16px;
        align-items: flex-start;
    }

    nav div {
        width: 100%;
        gap: 4px;
    }

    nav div a {
        padding: 7px 9px;
        font-size: 13px;
    }

    main {
        margin-top: 22px;
        padding: 0 13px;
    }

    .card {
        padding: 19px;
        border-radius: 15px;
    }

    .person {
        align-items: flex-start;
        gap: 12px;
    }

    .avatar {
        width: 60px;
        height: 60px;
    }

    button, .button {
        max-width: 100%;
    }
}
</style>
"""

BASE_HTML = """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ title }} | Ocubed</title>
""" + STYLE + """
</head>
<body>
<nav>
  <a class="brand" href="{{ url_for('home') }}">Ocubed</a>
  <div>
  {% if current_user %}
    <a href="{{ url_for('home') }}">Feed</a>
    <a href="{{ url_for('discover') }}">Discover</a>
    <a href="{{ url_for('profile', username=current_user['username']) }}">Profile</a>
    <a href="{{ url_for('logout') }}">Log out</a>
  {% else %}
    <a href="{{ url_for('login') }}">Log in</a>
    <a href="{{ url_for('register') }}">Join</a>
  {% endif %}
  </div>
</nav>
<main>
{% for message in get_flashed_messages() %}
  <p class="notice">{{ message }}</p>
{% endfor %}
{{ content|safe }}
</main>
<footer>Ocubed · Connect, share, belong.</footer>
</body>
</html>
"""


def page(title, content, **context):
    body = render_template_string(content, **context)
    return render_template_string(
        BASE_HTML, title=title, content=body
    )


# ---------------- HOMEPAGE / FEED ----------------
@app.route("/like/<int:post_id>", methods=["POST"])
def like_post(post_id):
    user = current_user()

    if not user:
        return redirect(url_for("login"))

    db = get_db()

    post = db.execute(
        "SELECT id FROM posts WHERE id = ?",
        (post_id,)
    ).fetchone()

    if post:
        db.execute("""
            INSERT OR IGNORE INTO likes (user_id, post_id)
            VALUES (?, ?)
        """, (user["id"], post_id))
        db.commit()

    return redirect(url_for("home"))



@app.route("/")
def home():
    user = current_user()
    posts = []

    if user:
        posts = get_db().execute("""
            SELECT posts.*, users.username, users.display_name,
                   users.profile_picture,
                   (SELECT COUNT(*) FROM likes
                    WHERE likes.post_id = posts.id) AS like_count,
                   (SELECT COUNT(*) FROM likes
                    WHERE likes.post_id = posts.id
                    AND likes.user_id = ?) AS liked_by_me
            FROM posts
            JOIN users ON users.id = posts.user_id
            WHERE posts.user_id = ?
               OR posts.user_id IN (
                   SELECT followed_id FROM follows
                   WHERE follower_id = ?
               )
            ORDER BY posts.id DESC
        """, (user["id"], user["id"], user["id"])).fetchall()

    return page("Home", """
    {% if current_user %}
      <h1>Your feed</h1>
      <form class="card" method="post" action="{{ url_for('create_post') }}">
        <h3>What's happening?</h3>
        <textarea name="content" maxlength="2000"
          placeholder="Share something with Ocubed..." required></textarea>
        <button type="submit">Publish post</button>
      </form>

      {% for post in posts %}
        <article class="card">
          <a href="{{ url_for('profile', username=post['username']) }}">
            <strong>{{ post['display_name'] or post['username'] }}</strong>
            @{{ post['username'] }}
          </a>

          <p class="muted">{{ post['created_at'] }}</p>
          <p style="white-space: pre-wrap">{{ post['content'] }}</p>

          <form method="post"
                action="{{ url_for('like_post', post_id=post['id']) }}"
                style="margin-top: 12px;">
            <button type="submit">
              {% if post['liked_by_me'] %}
                ❤️ Liked
              {% else %}
                🤍 Like
              {% endif %}
              · {{ post['like_count'] }}
            </button>
          </form>
        </article>
      {% else %}
        <div class="card">
          <h3>Your feed is waiting!</h3>
          Follow people in Discover or publish your first post.
        </div>
      {% endfor %}
    {% else %}
      <section class="card">
        <h1>Welcome to Ocubed!</h1>
        <p>A place to share your thoughts, meet people and build connections.</p>
        <a class="button" href="{{ url_for('register') }}">Create account</a>
        <a class="button" href="{{ url_for('login') }}">Log in</a>
      </section>
    {% endif %}
    """, posts=posts)



# ---------------- REGISTRATION ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
            flash("Username must be 3–24 characters: letters, numbers or underscores.")
        elif len(password) < 10:
            flash("Your password must be at least 10 characters.")
        elif password != confirm:
            flash("The passwords do not match.")
        else:
            db = get_db()
            try:
                cursor = db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password))
                )
                db.commit()
                session.clear()
                session["user_id"] = cursor.lastrowid
                return redirect(url_for("home"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.")

    return page("Join Ocubed", """
    <div class="card">
      <h1>Create your account</h1>
      <form method="post">
        <label>Username</label>
        <input name="username" minlength="3" maxlength="24"
          pattern="[A-Za-z0-9_]+" required autocomplete="username">
        <label>Password (at least 10 characters)</label>
        <input type="password" name="password" minlength="10"
          required autocomplete="new-password">
        <label>Confirm password</label>
        <input type="password" name="confirm_password"
          minlength="10" required autocomplete="new-password">
        <button type="submit">Join Ocubed</button>
      </form>
      <p>Already joined? <a href="{{ url_for('login') }}">Log in</a></p>
    </div>
    """)


# ---------------- LOGIN / LOGOUT ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?",
            (username,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("home"))

        flash("Incorrect username or password.")

    return page("Log in", """
    <div class="card">
      <h1>Welcome back</h1>
      <form method="post">
        <label>Username</label>
        <input name="username" required autocomplete="username">
        <label>Password</label>
        <input type="password" name="password" required
          autocomplete="current-password">
        <button type="submit">Log in</button>
      </form>
      <p>New to Ocubed? <a href="{{ url_for('register') }}">Create an account</a></p>
    </div>
    """)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.")
    return redirect(url_for("home"))


# ---------------- CREATE POSTS ----------------

@app.route("/post", methods=["POST"])
@login_required
def create_post():
    content = request.form.get("content", "").strip()

    if not content:
        flash("Your post cannot be empty.")
    elif len(content) > 2000:
        flash("Posts must be 2,000 characters or fewer.")
    else:
        get_db().execute(
            "INSERT INTO posts (user_id, content) VALUES (?, ?)",
            (session["user_id"], content)
        )
        get_db().commit()
        flash("Your post has been published!")

    return redirect(url_for("home"))


# ---------------- PROFILES ----------------

@app.route("/profile/<username>", methods=["GET", "POST"])
def profile(username):
    db = get_db()
    person = db.execute(
        "SELECT * FROM users WHERE username = ?", (username.lower(),)
    ).fetchone()

    if not person:
        return page("Not found", "<div class='card'><h1>User not found</h1></div>"), 404

    own_profile = (
        current_user() is not None
        and current_user()["id"] == person["id"]
    )

    if request.method == "POST":
        if not own_profile:
            flash("You can only edit your own profile.")
            return redirect(url_for("profile", username=username))

        display_name = request.form.get("display_name", "").strip()[:50]
        bio = request.form.get("bio", "").strip()[:300]
        picture = person["profile_picture"] or ""

        uploaded = request.files.get("picture")
        if uploaded and uploaded.filename:
            safe_name = secure_filename(uploaded.filename)
            extension = Path(safe_name).suffix.lower()

            if extension not in ALLOWED_EXTENSIONS:
                flash("Use a PNG, JPG, JPEG or WEBP image.")
                return redirect(url_for("profile", username=username))

            filename = secrets.token_hex(16) + extension
            uploaded.save(UPLOAD_FOLDER / filename)
            picture = filename

        db.execute("""
            UPDATE users SET display_name = ?, bio = ?, profile_picture = ?
            WHERE id = ?
        """, (display_name, bio, picture, person["id"]))
        db.commit()
        flash("Your profile has been updated.")
        return redirect(url_for("profile", username=username))

    person = db.execute(
        "SELECT * FROM users WHERE id = ?", (person["id"],)
    ).fetchone()

    followers = db.execute(
        "SELECT COUNT(*) FROM follows WHERE followed_id = ?",
        (person["id"],)
    ).fetchone()[0]

    following = db.execute(
        "SELECT COUNT(*) FROM follows WHERE follower_id = ?",
        (person["id"],)
    ).fetchone()[0]

    is_following = False
    if current_user() and not own_profile:
        is_following = db.execute(
            "SELECT 1 FROM follows WHERE follower_id = ? AND followed_id = ?",
            (current_user()["id"], person["id"])
        ).fetchone() is not None

    posts = db.execute("""
        SELECT * FROM posts WHERE user_id = ? ORDER BY id DESC
    """, (person["id"],)).fetchall()

    return page("Profile", """
    <section class="card">
      <div class="person">
        {% if person['profile_picture'] %}
          <img class="avatar"
            src="{{ url_for('static', filename='profile_pictures/' + person['profile_picture']) }}"
            alt="Profile picture">
        {% else %}
          <div class="avatar"></div>
        {% endif %}
        <div>
          <h1>{{ person['display_name'] or person['username'] }}</h1>
          <p class="muted">@{{ person['username'] }}</p>
        </div>
      </div>
      <p>{{ person['bio'] or 'No bio yet.' }}</p>
      <p>{{ followers }} followers · {{ following }} following</p>

      {% if current_user and not own_profile %}
        <form method="post"
          action="{{ url_for('follow_user' if not is_following else 'unfollow_user', username=person['username']) }}">
          <button type="submit">{{ 'Follow' if not is_following else 'Unfollow' }}</button>
        </form>
      {% endif %}
    </section>

    {% if own_profile %}
    <section class="card">
      <h2>Edit your profile</h2>
      <form method="post" enctype="multipart/form-data">
        <label>Display name</label>
        <input name="display_name" maxlength="50"
          value="{{ person['display_name'] or '' }}">
        <label>Bio (up to 300 characters)</label>
        <textarea name="bio" maxlength="300">{{ person['bio'] or '' }}</textarea>
        <label>Profile picture (PNG, JPG or WEBP, max 3 MB)</label>
        <input type="file" name="picture" accept=".png,.jpg,.jpeg,.webp">
        <button type="submit">Save profile</button>
      </form>
    </section>
    {% endif %}

    <h2>Posts</h2>
    {% for post in posts %}
      <article class="card">
        <p class="muted">{{ post['created_at'] }}</p>
        <p style="white-space: pre-wrap">{{ post['content'] }}</p>
      </article>
    {% else %}
      <div class="card">No posts yet.</div>
    {% endfor %}
    """, person=person, own_profile=own_profile, followers=followers,
         following=following, is_following=is_following, posts=posts)


# ---------------- FOLLOW / UNFOLLOW ----------------

@app.route("/follow/<username>", methods=["POST"])
@login_required
def follow_user(username):
    db = get_db()
    person = db.execute(
        "SELECT id FROM users WHERE username = ?", (username.lower(),)
    ).fetchone()

    if not person:
        flash("User not found.")
    elif person["id"] == session["user_id"]:
        flash("You cannot follow yourself.")
    else:
        db.execute("""
            INSERT OR IGNORE INTO follows (follower_id, followed_id)
            VALUES (?, ?)
        """, (session["user_id"], person["id"]))
        db.commit()

    return redirect(url_for("profile", username=username))


@app.route("/unfollow/<username>", methods=["POST"])
@login_required
def unfollow_user(username):
    db = get_db()
    person = db.execute(
        "SELECT id FROM users WHERE username = ?", (username.lower(),)
    ).fetchone()

    if person:
        db.execute("""
            DELETE FROM follows WHERE follower_id = ? AND followed_id = ?
        """, (session["user_id"], person["id"]))
        db.commit()

    return redirect(url_for("profile", username=username))


# ---------------- DISCOVER USERS ----------------

@app.route("/discover")
@login_required
def discover():
    search = request.args.get("q", "").strip()[:50]
    pattern = "%" + search + "%"

    people = get_db().execute("""
        SELECT users.*,
          (SELECT COUNT(*) FROM follows
           WHERE follows.followed_id = users.id) AS followers
        FROM users
        WHERE users.id != ?
          AND (users.username LIKE ? OR users.display_name LIKE ?)
        ORDER BY followers DESC, users.username ASC
        LIMIT 100
    """, (session["user_id"], pattern, pattern)).fetchall()

    return page("Discover", """
    <h1>Discover people</h1>
    <form class="card" method="get">
      <input name="q" value="{{ search }}" placeholder="Search usernames or names">
      <button type="submit">Search</button>
    </form>
    {% for person in people %}
      <section class="card person">
        {% if person['profile_picture'] %}
          <img class="avatar"
            src="{{ url_for('static', filename='profile_pictures/' + person['profile_picture']) }}"
            alt="Profile picture">
        {% else %}
          <div class="avatar"></div>
        {% endif %}
        <div>
          <a href="{{ url_for('profile', username=person['username']) }}">
            <strong>{{ person['display_name'] or person['username'] }}</strong>
          </a>
          <div class="muted">@{{ person['username'] }}</div>
          <div class="muted">{{ person['followers'] }} followers</div>
          <a href="{{ url_for('profile', username=person['username']) }}">View profile</a>
        </div>
      </section>
    {% else %}
      <div class="card">No users found. Try another search.</div>
    {% endfor %}
    """, people=people, search=search)


# ---------------- ERROR PAGES ----------------

@app.errorhandler(404)
def not_found(error):
    return page("Not found", """
      <div class="card"><h1>Page not found</h1>
      <a href="{{ url_for('home') }}">Return home</a></div>
    """), 404


@app.errorhandler(413)
def too_large(error):
    return page("File too large", """
      <div class="card"><h1>Upload too large</h1>
      <p>Please upload a file smaller than 3 MB.</p></div>
    """), 413


# Keep this at the very bottom of the file.
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(os.environ.get("PORT", 5001)),
        debug=False
    )

    

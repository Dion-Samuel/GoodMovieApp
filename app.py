from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3

app = Flask(__name__)
app.secret_key = "goodmoviesecret"   # basic session key


# -----------------------------------------
# Helper: Connect to SQLite
# -----------------------------------------
def get_db():
    conn = sqlite3.connect("goodmovie.db")
    conn.row_factory = sqlite3.Row
    return conn

def query_db(sql, params=(), one=False):
    conn = get_db()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    if one:
        return rows[0] if rows else None
    return rows



# -----------------------------------------
# Routes
# -----------------------------------------

@app.route("/")
def home():
    return redirect(url_for("movies"))


# ------------- AUTH ----------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()
        conn.execute("INSERT INTO Users (username, email, password_hash, created_at) VALUES (?, ?, ?, '2025-01-01')",
                     (username, email, password))
        conn.commit()
        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM Users WHERE username=? AND password_hash=?",
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["user_id"]
            session["username"] = user["username"]
            return redirect(url_for("movies"))
        else:
            return "Invalid username or password."

    return render_template("login.html")

@app.route("/reviews")
def all_reviews():
    conn = get_db()
    rows = conn.execute("""
        SELECT Reviews.review_id,
               Reviews.rating,
               Reviews.review_text,
               Reviews.created_at,
               Movies.title AS movie_title
        FROM Reviews
        JOIN Movies ON Reviews.movie_id = Movies.movie_id
        ORDER BY Reviews.created_at DESC
    """).fetchall()
    conn.close()
    return render_template("reviews.html", reviews=rows)


@app.route("/api/movies-with-ratings")
def api_movies_with_ratings():
    rows = query_db("""
        SELECT Movies.title,
               AVG(Reviews.rating) AS avg_rating
        FROM Movies
        LEFT JOIN Reviews ON Movies.movie_id = Reviews.movie_id
        GROUP BY Movies.movie_id
    """)
    data = [
        {"title": r["title"], "avg_rating": r["avg_rating"]}
        for r in rows
    ]
    return jsonify(data)

@app.route("/my-reviews")
def my_reviews():
    if "user_id" not in session:
        return redirect(url_for("login"))

    rows = query_db("""
        SELECT Reviews.review_id,
               Reviews.rating,
               Reviews.review_text,
               Reviews.created_at,
               Movies.title AS movie_title
        FROM Reviews
        JOIN Movies ON Reviews.movie_id = Movies.movie_id
        WHERE Reviews.user_id = ?
        ORDER BY Reviews.created_at DESC
    """, (session["user_id"],))
    return render_template("my_reviews.html", reviews=rows)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ------------- MOVIES ----------------------

@app.route("/movies")
def movies():
    q = request.args.get("q", "").strip()

    if q:
        rows = query_db(
            "SELECT movie_id, title, release_year FROM Movies WHERE title LIKE ?",
            (f"%{q}%",)
        )
    else:
        rows = query_db("SELECT movie_id, title, release_year FROM Movies")

    return render_template("movies.html", movies=rows, q=q)


@app.route("/movies/<int:movie_id>")
def movie_detail(movie_id):
    conn = get_db()
    movie = conn.execute("SELECT * FROM Movies WHERE movie_id=?", (movie_id,)).fetchone()
    reviews = conn.execute("SELECT * FROM Reviews WHERE movie_id=?", (movie_id,)).fetchall()
    conn.close()

    return render_template("movie_detail.html", movie=movie, reviews=reviews)


@app.route("/movies/<int:movie_id>/review", methods=["POST"])
def add_review(movie_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    rating = request.form["rating"]
    text = request.form["review_text"]

    conn = get_db()
    conn.execute(
        "INSERT INTO Reviews (user_id, movie_id, rating, review_text, created_at) VALUES (?, ?, ?, ?, '2025-02-01')",
        (session["user_id"], movie_id, rating, text)
    )
    conn.commit()
    conn.close()

    return redirect(url_for("movie_detail", movie_id=movie_id))


# ------------- STATS (Visualization) ----------------------

@app.route("/stats")
def stats():
    conn = get_db()
    data = conn.execute("""
        SELECT Movies.title AS title, AVG(Reviews.rating) AS avg_rating
        FROM Movies
        JOIN Reviews ON Movies.movie_id = Reviews.movie_id
        GROUP BY Movies.movie_id
        ORDER BY avg_rating DESC
    """).fetchall()

    conn.close()
    return render_template("stats.html", data=data)


# -----------------------------------------
# Run App
# -----------------------------------------
if __name__ == "__main__":
    app.run(debug=True)

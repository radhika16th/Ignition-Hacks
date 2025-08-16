
from flask import Flask, render_template, request, redirect, session
import ast
import sqlite3
import random
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mfmdfkedwlkdf'

@app.after_request
def after_request(r):
    """Stops caching"""
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = 0
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

def login_required(f):
    """Creates decorator to reroute to login page if not logged in yet"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function

@app.route("/", methods=["GET"])
@login_required
def index():
    uid = session["user_id"]

    # pull all saved choices for this user
    conn = sqlite3.connect("choices.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT title FROM choices WHERE user_id = ? ORDER BY id", (uid,))
    rows = cur.fetchall()
    conn.close()

    titles = [r["title"] for r in rows]
    return render_template("index.html", titles=titles)

@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    #pulls user info from database
    if request.method == "POST":
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row #makes it like a dictionary
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        #checks if user is in database and if the password is correct
        if len(users) != 1 or not check_password_hash(users[0]["password"], request.form.get("password")):
            return("invalid username and/or password")
        #logs user in and tracks their session info
        session["user_id"] = users[0]["id"]
        return redirect("/")
    else:
        return render_template("login.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect("/")

@app.route("/register", methods=["GET", "POST"])
def register():
    session.clear()
    #checks if passwords entered match
    if request.method == "POST":
        if request.form.get("password") != request.form.get("confirmpassword"):
            return "passwords don't match"
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row #makes it like a dictionary
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.form.get("username"),))
        users = [dict(row) for row in cursor.fetchall()]
        #checks if username is unique and enters user info into the database with a hash of their password
        try:
            username = request.form.get("username")
            passwordhash = generate_password_hash(request.form.get("password"))
            cursor.execute("INSERT INTO users (username, password) VALUES(?,?)", (username, passwordhash))
            conn.commit()
            conn.close()
            return redirect("/")
        except:
            conn.close()
            return "username unavailable"
    else:

        return render_template("register.html")

@app.route("/page3", methods=["GET", "POST"])
@login_required
def page3():
    #when user swipes right, pulls info from html form and save the info from the book they liked and shows a new book on the page
    if request.method == "POST":
        conn = sqlite3.connect('choices.db')
        conn.row_factory = sqlite3.Row #makes it like a dictionary
        cursor = conn.cursor()
        cursor.execute("INSERT INTO choices (user_id, title, author) VALUES(?,?,?)",(session["user_id"], request.form.get("choice"),request.form.get("choice2")))
        conn.commit()
        conn.close()
        return redirect("/page3")
        
    #displays book based on the genres that they chose on the preferences page
    else:
        id = session["user_id"]
        conn1 = sqlite3.connect('users.db')
        conn1.row_factory = sqlite3.Row #makes it like a dictionary
        cursor1 = conn1.cursor()
        cursor1.execute("SELECT genre1,genre2,genre3 FROM users WHERE id = ?", (id,))
        user_genres = cursor1.fetchone()

        conn2 = sqlite3.connect('books.db')
        conn2.row_factory = sqlite3.Row #makes it like a dictionary
        cursor2 = conn2.cursor()
        #checks if user has entered their preferences
        if user_genres == None:
            genres = [user_genres['genre1'], user_genres['genre2'], user_genres['genre3']]
            cursor2.execute("SELECT * FROM books WHERE genres LIKE ? OR genres LIKE ? OR genres LIKE ?", ('%' + genres[0] + '%', '%' + genres[1] + '%', '%' + genres[2] + '%'))
        else:
            cursor2.execute("SELECT * FROM books")
        #format and sends info from database to html to be used
        books = [dict(row) for row in cursor2.fetchall()]
        book = random.choice(books)
        book['genres'] = ast.literal_eval(book['genres'])
        book['publication_info'] = ast.literal_eval(book['publication_info']) 
        return render_template("page3.html", book = book)

@app.route("/page4", methods=["GET", "POST"])
@login_required
def page4():
    #formats and sends info from database to html to be used
    if request.method == "POST":
        conn = sqlite3.connect('books.db')
        conn.row_factory = sqlite3.Row #makes it like a dictionary
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM books WHERE book_id = ?",(request.form.get("book_id"),))
        book = cursor.fetchone()
        book = dict(book)
        book['genres'] = ast.literal_eval(book['genres'])
        book['publication_info'] = ast.literal_eval(book['publication_info']) 
        conn.close()
        return render_template("page4.html", book=book)
    
@app.route("/preferences", methods=["GET", "POST"])
@login_required
def preferences():
    #gets preferences from user input from the html form and stores it in the appropriate database
    if request.method == "POST":
        uid = session["user_id"]

        genres = request.form.getlist("genre")[:3]
        g1, g2, g3 = (genres + [None, None, None])[:3]

        b1 = request.form.get("book1") or None
        b2 = request.form.get("book2") or None
        b3 = request.form.get("book3") or None
        
        conn = sqlite3.connect('users.db')
        cur = conn.cursor()
        cur.execute(""" UPDATE users
                        SET genre1 = ?,
                            genre2 = ?,
                            genre3 = ?,
                            book1  = ?,
                            book2  = ?,
                            book3  = ?
                        WHERE id = ?""", 
                        (g1, g2, g3, b1, b2, b3, uid))
        conn.commit()
        conn.close()

        return redirect("/")
    #display the proper information on the html page
    else:
        uid = session.get("user_id")
        conn = sqlite3.connect('users.db')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT genre1,genre2,genre3,book1,book2,book3 FROM users WHERE id = ?", (uid,))
        row = cur.fetchone()
        conn.close()
        
        return render_template("pref.html", row=row)



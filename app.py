from flask import Flask, render_template, request, redirect, url_for, session, flash
from markupsafe import escape
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import generate_csrf
from collections import defaultdict
from datetime import datetime, timedelta
import os
import sqlite3
import re

app = Flask(__name__)
app.secret_key = os.environ.get('THE_SECRET_KEY', 'dev-key-change-in-production')

login_attempts = defaultdict(list)
RATE_LIMIT = 5
RATE_WINDOW = 300

def init_db():
    conn = sqlite3.connect('library.db')
    cursor = conn.cursor()

    cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   username TEXT UNIQUE NOT NULL,
                   password_hash TEXT NOT NULL,
                   user_type TEXT NOT NULL
                   )
                ''')
    
    cursor.execute('''
                CREATE TABLE IF NOT EXISTS books (
                   id INTEGER PRIMARY KEY AUTOINCREMENT,
                   title TEXT NOT NULL,
                   author TEXT NOT NULL,
                   available BOOLEAN DEFAULT 1
                   )
                ''')
    
    try:
        cursor.execute("INSERT INTO users (username, password_hash, user_type) VALUES (?, ?, ?)",
                       ('admin', generate_password_hash('admin123'), 'librarian'))
        cursor.execute("INSERT INTO users (username, password_hash, user_type) VALUES (?, ?, ?)",
                       ('member1', generate_password_hash('member123'), 'member'))
        cursor.execute("INSERT INTO users (username, password_hash, user_type) VALUES (?, ?, ?)",
                       ('staff1', generate_password_hash('staff123'), 'staff'))
    except sqlite3.IntegrityError:
        pass

    try:
        cursor.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                       ('Python Programming', 'John K'))
        cursor.execute("INSERT INTO books (title, author) VALUES (?, ?)",
                       ('Cyber Security', 'Alex R'))
    except sqlite3.IntegrityError:
        pass

    conn.commit()
    conn.close()

@app.route('/')
def index():
    return '''
    <h1>Welcome to Library Management System</h1>
    <p><a href="/login">Login</a></p>
    <p><a href="/register">Register</a></p>
    '''

@app.route('/admin')
def admin_panel():
    if 'username' not in session:
        return '<h1>Please login first</h1>'
    if session.get('user_type') != 'librarian':
        return '<h1>Access denied - Librarians only</h1>'
    return '<h1>Admin Panel - You have librarian access!</h1>'

@app.route('/test-error')
def test_error():
    x = 1 / 0 
    return "This won't execute"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.form.get('csrf_token'))
        except:
            return "<h1>CSRF token missing or invalid</h1>", 400
        
        client_ip = request.remote_addr
        current_time = datetime.now()

        login_attempts[client_ip] = [
            attempt_time for attempt_time in login_attempts[client_ip]
            if current_time - attempt_time < timedelta(seconds=RATE_WINDOW)
        ]

        if len(login_attempts[client_ip]) >= RATE_LIMIT:
            return "<h1>Too many login attempts. Try again in 5 minutes.</h1>", 429
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user_type = request.form.get('user_type', '').strip()

        if not username or not password or not user_type:
            return "<h1>All fields are required</h1>"
        
        if user_type not in ['librarian', 'member', 'staff']:
            return "<h1>Invalid user type specified</h1>"
        
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()

        cursor.execute("SELECT username, password_hash FROM users WHERE username = ? and user_type =?",
                       (username, user_type))
        result = cursor.fetchone()

        if result and check_password_hash(result[1], password):
            if client_ip in login_attempts:
                del login_attempts[client_ip]

            session.clear()
            session.permanent = True
            session['username'] = username
            session['user_type'] = user_type
            session.modified = True

            return f'''
            <h1>Welcome {escape(username)}! You are logged in as {escape(user_type)}.</h1>
            <p><a href="/logout">Logout</a></p>
            <p><a href="/dashboard">Dashboard</a></p>
            '''
        
        else:
            login_attempts[client_ip].append(current_time)
            return "<h1>Invalid credentials</h1>"
        
    return f'''
    <h2>Login</h2>
    <form method="POST">
        <input type="hidden" name="csrf_token" value="{generate_csrf()}"/>
        <div>
            <label>Username:</label><br>
            <input type="text" name="username" required>
        </div>
        <br>
        <div>
            <label>Password:</label><br>
            <input type="password" name="password" required>
        </div>
        <br>
        <div>
            <label>Login as:</label><br>
            <select name="user_type" required>
                <option value="">Select...</option>
                <option value="librarian">Librarian</option>
                <option value="member">Member</option>
                <option value="staff">Staff</option>
            </select>
        </div>
        <br>
        <button type="submit">Login</button>
    </form>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':

        from flask_wtf.csrf import validate_csrf
        try:
            validate_csrf(request.form.get('csrf_token'))
        except:
            return "<h1>CSRF token missing or invalid</h1>", 400
        
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            return "<h1>All field are required</h1>"
        
        if len(password) < 8:
            return "<h1>Password must be at least 8 characters long</h1>"
        
        if not any(c.isupper() for c in password):
            return "<h1>Password must contain at least one uppercase letter</h1>"
        
        if not any(c.islower() for c in password):
            return "<h1>Password must contain at least one lowercase letter</h1>"
        
        if not any(c.isdigit() for c in password):
            return "<h1>Password must contain at least one number</h1>"
        
        if not re.search(r"[@$!%*?&]", password):
            return "<h1>Password must contain at least one special character (@$!%?&)</h1>"
        
        conn = sqlite3.connect('library.db')
        cursor = conn.cursor()

        try:
            cursor.execute("INSERT INTO users (username, password_hash, user_type) VALUES (?, ?, ?)",
                           (username, generate_password_hash(password), 'member'))
            conn.commit()
            conn.close()
            return "<h1>Registration successful! <a href='/login'>Login here</a></h1>"
        except sqlite3.IntegrityError:
            conn.close()
            return "<h1>Username already exists</h1>"
    
    return f'''
    <h2>Register</h2>
    <form method="POST">
        <input type="hidden" name="csrf_token" value="{generate_csrf()}"/>
        <div>
            <label>Username:</label><br>
            <input type="text" name="username" required>
        </div>
        <br>
        <div>
            <label>Password:</label><br>
            <input type="password" name="password" required>
        </div>
        <br>
        <button type="submit">Register</button>
    </form>
    '''

@app.route('/logout')
def logout():
    session.clear()
    return '<h1>Logged out successfully. <a href="/">Home</a></h1>'   
            
#This runs the program
if __name__=='__main__':
    init_db()
    app.run(debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true')

    
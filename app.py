from flask import Flask, render_template, request, redirect, url_for, session, flash
from markupsafe import escape
import os

app = Flask(__name__)
app.secret_key = 'SECRET_KEY'

class LibrarySystem:

    staff_members={'staff1': 'staff123'} 
    members={'member1':'member123'} 
    librarian = {'admin':'admin123'} 
    available_books={'Python Programming':'John K', 'Cyber Security':'Alex R'} 
    borrowed_books={}
    member_books={} 

@app.route('/')
def index():
    #return "<h1>Hello! Library System works!</h1>"
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        user_type = request.form.get('user_type', '').strip()

        if not username or not password or not user_type:
            return "<h1>All fields are required</h1>"
        
        if user_type not in ['librarian', 'member', 'staff']:
            return "<h1>Invalid user type specified</h1>"

        if user_type == 'librarian':
            if username in LibrarySystem.librarian and LibrarySystem.librarian[username] == password:
                session['username'] = username
                session['user_type'] = 'librarian'
                return f"<h1>Welcome {escape(username)}! You are logged in as librarian.</h1>"
        elif user_type == 'member':
            if username in LibrarySystem.members and LibrarySystem.members[username] == password:
                session['username'] = username
                session['user_type'] = 'member'
                return f"<h1>Welcome {escape(username)}! You are logged in as member.</h1>"
        
        return "<h1>Invalid credentials</h1>"
        
    return '''
    <h2>Login</h2>
    <form method="POST">
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
            </select>
        </div>
        <br>
        <button type="submit">Login</button>
    </form>
    '''
    


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username not in LibrarySystem.members:
            LibrarySystem.members[username] = password
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        else:
            flash('Username already exists')

    return render_template('register.html')

@app.route('/librarian_dashboard')
def librarian_dashboard():
    if 'user_type' not in session or session['user_type'] != 'librarian':
        return redirect(url_for('login'))
    return render_template('librarian_dashboard.html', books = LibrarySystem.available_books)

@app.route('/member_dashboard')
def member_dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('member_dashboard.html', available_books = LibrarySystem.available_books, borrowed_books = LibrarySystem.borrowed_books)

@app.route('/add_book', methods=['POST'])
def add_book():
    if 'user_type' not in session or session['user_type'] != 'librarian':
        return redirect(url_for('login'))
    
    title = request.form['title']
    author = request.form['author']
    LibrarySystem.available_books['title'] = author
    flash(f'Book "{title}" added successfully!')
    return redirect(url_for('librarian_dashboard'))

@app.route('/borrow_book', methods=['POST'])
def borrow_book():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    title = request.form['title']
    username = session['username']

    if title in LibrarySystem.available_books:
        author = LibrarySystem.available_books.pop(title)
        LibrarySystem.borrowed_books[title] = author

        if username not in LibrarySystem.member_books:
            LibrarySystem.member_books[username] = []
        LibrarySystem.member_books[username].append(title)

        flash(f'Book "{title}" borrowed successfully!')
    
    else:
        flash('Book not available')

    return redirect(url_for('member_dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))        
            
#This runs the program
if __name__=='__main__':
    app.run(debug=True)

    
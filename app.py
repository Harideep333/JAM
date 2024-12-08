from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Necessary for flash messages and session management

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # Set the login view

# MySQL connection setup
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",  # MySQL host
        user="root",  # MySQL user
        password="rootpass",  # MySQL password
        database="lms_db"
    )

# User class to represent the logged-in user
class User(UserMixin):
    def __init__(self, id, email):
        self.id = id
        self.email = email

# Load user from session
@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM members WHERE member_id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    connection.close()
    
    if user_data:
        return User(id=user_data['member_id'], email=user_data['email'])
    return None

# Routes



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check the user credentials in the database
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM members WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()
        connection.close()

        if user and user['password'] == password:  # Compare with hashed password if using hash
            user_obj = User(id=user['member_id'], email=user['email'])
            login_user(user_obj)  # Log the user in
            flash('Login successful!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid credentials, please try again.', 'danger')

    return render_template('index.html')

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/add_member', methods=['GET', 'POST'])
@login_required
def add_member():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']  # Optional: hash this before saving

        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO members (name, email, phone, password)
            VALUES (%s, %s, %s, %s)
        """, (name, email, phone, password))
        connection.commit()
        cursor.close()
        connection.close()

        flash('Member registered successfully!', 'success')
        return redirect(url_for('get_members'))

    return render_template('add_member.html')



@app.route('/logout')
@login_required
def logout():
    logout_user()  # Log the user out
    flash('You have logged out successfully.', 'info')
    return redirect(url_for('home'))

@app.route('/books')
@login_required
def get_books():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('books.html', books=books)

@app.route('/members')
@login_required
def get_members():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('members.html', members=members)

@app.route('/loans')
@login_required
def get_loans():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT loans.loan_id, books.title, members.name, loans.borrow_date, loans.return_date
        FROM loans
        JOIN books ON loans.book_id = books.book_id
        JOIN members ON loans.member_id = members.member_id
    """)
    loans = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('loans.html', loans=loans)

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if request.method == 'POST':
        title = request.form['title']
        author = request.form['author']
        genre = request.form['genre']
        availability = request.form['availability']
        availability = True if availability == 'on' else False
        
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO books (title, author, genre, availability) VALUES (%s, %s, %s, %s)", 
                       (title, author, genre, availability))
        connection.commit()
        cursor.close()
        connection.close()

        flash('Book added successfully!', 'success')  # Success flash message
        return redirect(url_for('get_books'))

    return render_template('add_book.html')

@app.route('/borrow_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def borrow_book(book_id):
    if request.method == 'POST':
        member_id = request.form['member_id']
        borrow_date = request.form['borrow_date']
        return_date = request.form['return_date']
        
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("""
            INSERT INTO loans (book_id, member_id, borrow_date, return_date)
            VALUES (%s, %s, %s, %s)
        """, (book_id, member_id, borrow_date, return_date))
        connection.commit()
        cursor.close()
        connection.close()
        
        flash('Book borrowed successfully!', 'success')
        return redirect(url_for('get_books'))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM members")
    members = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return render_template('borrow_book.html', book_id=book_id, members=members)


@app.route('/search_books', methods=['GET', 'POST'])
@login_required
def search_books():
    if request.method == 'POST':
        keyword = f"%{request.form['keyword']}%"
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM books
            WHERE title LIKE %s OR author LIKE %s OR genre LIKE %s
        """, (keyword, keyword, keyword))
        books = cursor.fetchall()
        cursor.close()
        connection.close()
        return render_template('search_results.html', books=books)
    return render_template('search_books.html')



@app.route('/overdue_books')
@login_required
def overdue_books():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT loans.loan_id, books.title, members.name, loans.borrow_date, loans.return_date
        FROM loans
        JOIN books ON loans.book_id = books.book_id
        JOIN members ON loans.member_id = members.member_id
        WHERE loans.return_date < CURDATE()
    """)
    overdue = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('overdue_books.html', overdue=overdue)


@app.route('/member_history/<int:member_id>')
@login_required
def member_history(member_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("""
        SELECT books.title, loans.borrow_date, loans.return_date
        FROM loans
        JOIN books ON loans.book_id = books.book_id
        WHERE loans.member_id = %s
    """, (member_id,))
    history = cursor.fetchall()
    cursor.close()
    connection.close()
    return render_template('member_history.html', history=history)

@app.route('/reports')
@login_required
def reports():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Most popular books
    cursor.execute("""
        SELECT books.title, COUNT(loans.book_id) AS borrow_count
        FROM loans
        JOIN books ON loans.book_id = books.book_id
        GROUP BY loans.book_id
        ORDER BY borrow_count DESC
        LIMIT 5
    """)
    popular_books = cursor.fetchall()

    # Members with most overdue books
    cursor.execute("""
        SELECT members.name, COUNT(loans.loan_id) AS overdue_count
        FROM loans
        JOIN members ON loans.member_id = members.member_id
        WHERE loans.return_date < CURDATE()
        GROUP BY loans.member_id
        ORDER BY overdue_count DESC
        LIMIT 5
    """)
    overdue_members = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('reports.html', popular_books=popular_books, overdue_members=overdue_members)



@app.route('/return_book/<int:loan_id>', methods=['POST'])
@login_required
def return_book(loan_id):
    connection = get_db_connection()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM loans WHERE loan_id = %s", (loan_id,))
    connection.commit()
    cursor.close()
    connection.close()

    flash('Book returned successfully!', 'success')
    return redirect(url_for('get_loans'))





if __name__ == '__main__':
    app.run(debug=True)
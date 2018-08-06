from flask import Flask, render_template, flash, request, redirect, url_for, session, abort
from wtforms import Form, StringField, PasswordField, TextAreaField, validators
from flask_mysqldb import MySQL
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gingerbreadman'

creds = {'user': 'admin', 'password': sha256_crypt.encrypt('dancer')}

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'thelostbay'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

# Register
class registerForm(Form):
    email = StringField('E-Mail', [validators.Length(min=6, max=50), validators.Required()], render_kw={"placeholder": "Enter your e-mail to stay updated"})

@app.route('/register', methods = ['GET', 'POST'])
def register():
    form = registerForm(request.form)
    if request.method == 'POST' and form.validate():
        email = form.email.data

        cur = mysql.connection.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS emails (id INT(10) AUTO_INCREMENT PRIMARY KEY, email VARCHAR (40) NOT NULL UNIQUE);''')
        try:
            cur.execute('''INSERT INTO emails (email) VALUES('{}');'''.format(email))
        except Exception as e:
            cur.close()
            form.email.data = ""
            if e.args[0] == 1062:
                flash("Error! E-Mail already in list!", 'danger')
                return redirect(url_for('register'))
            else:
                flash(str(e.args[1]), 'danger')
                return redirect(url_for('register'))
            
        mysql.connection.commit()
        cur.close()
        form.email.data = ""
        
        flash("E-Mail successfully added to mailing list!", "success")
        return redirect(url_for('index'))
    return render_template('register.html', form = form)

# Login
class loginForm(Form):
    username = StringField('Username', validators=[validators.Required()], render_kw={"placeholder":"Enter the username"})
    password = PasswordField('Password', validators=[validators.Required()], render_kw={"placeholder":"Enter the password"})

@app.route('/login', methods = ['GET', 'POST'])
def login():
    form = loginForm(request.form)
    if request.method == 'POST' and form.validate():
        # TODO: Check login credentials
        name = form.username.data
        password_candidate = form.password.data
        if name == creds['user'] and sha256_crypt.verify(password_candidate, creds['password']):
            session['logged_in'] = True
            session['username'] = name
            flash("Successfully Logged In!", "success")
            return redirect(url_for('index'))
        else:
            flash("Invalid Credentials!", 'danger')
            return redirect(url_for('login'))
    return render_template('login.html', form= form)

def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized Access! Please Log In!", 'danger')
            return redirect(url_for('login'))
    return wrap

# Add Article
# TODO: Should only be visible when logged in, use sessions.
class Write(Form):
    title = StringField('Title', validators=[validators.Length(min=5, max=200)], render_kw={"placeholder":"Article Title"})
    body = TextAreaField('Content', validators=[validators.Length(min=30)])

@app.route('/write', methods = ['GET', 'POST'])
@is_logged_in
def write():
    form = Write(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        content = form.body.data

        cur = mysql.connection.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS articles (id INT(10) AUTO_INCREMENT PRIMARY KEY, title VARCHAR(200), author VARCHAR (50), body TEXT, date TIMESTAMP DEFAULT CURRENT_TIMESTAMP);''')

        try:
            cur.execute('''INSERT INTO articles (title, author, body) VALUES ("{}", "{}", "{}");'''.format(title, "Red", content))
        except Exception as e:
            cur.close()
            flash("{}".format(str(e.args[1])), 'danger')
            return redirect(url_for('dashboard'))

        mysql.connection.commit()
        cur.close()
        flash("Article Added!", 'success')
        return redirect(url_for('dashboard'))
        
        # TODO: Add articles to database
    return render_template('create_articles.html', form = form)

# Edit Article
@app.route("/edit_article/<string:id>", methods = ['GET', 'POST'])
@is_logged_in
def edit_article(id):
    form = Write(request.form)

    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM articles WHERE id = {}".format(id))
    article = cur.fetchone()
    
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():

        cur = mysql.connection.cursor() # We need a seperate cursor for POST request
        newTitle = request.form['title']
        newBody = request.form['body']

        cur.execute('''UPDATE articles SET title = "{}", body= "{}" WHERE id = {}'''.format(newTitle, newBody, id))
        mysql.connection.commit()
        cur.close()

        flash("Article Updated!", "success")
        return redirect(url_for("dashboard"))
    return render_template("edit_article.html", form = form)

# Delete Article
@app.route("/delete_article/<string:id>", methods = ['POST'])
@is_logged_in
def delete_article(id):
    cur = mysql.connection.cursor()
    cur.execute('''DELETE FROM articles WHERE id = {}'''.format(id))
    mysql.connection.commit()
    cur.close()

    flash('Article Deleted!', 'success')
    return redirect(url_for('dashboard'))


# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out", "Success")
    return redirect(url_for('login'))

# Articles
@app.route('/articles')
def articles():
    cur = mysql.connection.cursor()

    results = cur.execute("SELECT * FROM articles")
    articles = cur.fetchall()

    if results > 0:
        return render_template('articles.html', articles = articles)
    else:
        return render_template('articles.html', msg = "No Articles Found!")
    cur.close()
    
# Article by ID
@app.route('/article/<string:id>/')
def article(id):
    cur = mysql.connection.cursor()

    cur.execute("SELECT * from articles WHERE id = {}".format(id))
    article = cur.fetchone()
    cur.close()

    if article == None:
        abort(404)
    else:
        return render_template("article.html", article = article)

# Admin Dashboard
@app.route("/dashboard")
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    results = cur.execute("SELECT * from articles")
    articles = cur.fetchall()
    mysql.connect.commit()
    cur.close()
    if results > 0:
        return render_template('dashboard.html', articles = articles)
    else:
        return render_template('dashboard.html')
    # return render_template("dashboard.html")

# Error handling
@app.errorhandler(404)
def page_not_found_error(e):
    return render_template('404.html')

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html')

@app.errorhandler(403)
def fobidden_error(e):
    return render_template('403.html')

if __name__ == "__main__":
    app.secret_key = "*scream1984"
    app.run(debug=True, port=5000)

# Sanity Tracker:
# TODO: 1. Check credentials and create session  (done)
# TODO: 2. Create isloggedin() session check (done)
# TODO: 3. If logged in (and only then) show 'Write' page in menu (done)
# TODO: 4. Complete write page add to database (done)
# TODO: 4.5 Create articles page, list of articles from DB and  (done)
# TODO: 4.6 Implement proper error checking for article ()
# TODO: 4.6.5 Rogue article routes! (done)
# TODO: 4.7 Make Images work! (use static folder/upload to static folder)
# TODO: 4.7 edit/delete articles  (done)
# TODO: 5. Get mail working 
# TODO: 6. Make mail be sent when new article published

# **
# TODO: (URGENT) Fix ugly buttons (done)
# TODO: Add button functionality (done)
# TODO: (Thoughts): Delete button should be a form submission, Check Travesty (done)
# TODO: Article Update NOT WORKING!!!!!! (done)

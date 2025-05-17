from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__)
app.secret_key = 'secret_key_here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///restaurant.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class MenuItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    items = db.Column(db.String(500), nullable=False)
    total = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    fulfilled = db.Column(db.Boolean, default=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['user_logged_in'] = True
            return redirect(url_for('menu'))
        flash('Invalid login.')
    return render_template('user_login.html')

@app.route('/user/register', methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        email = request.form['email']
        username = request.form['username']
        password = request.form['password']
        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash('Username or email already exists.')
        else:
            new_user = User(email=email, username=username)
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash('Account created. Please log in.')
            return redirect(url_for('user_login'))
    return render_template('register.html')


@app.route('/user/logout')
def user_logout():
    session.pop('user_logged_in', None)
    return redirect(url_for('index'))

class AdminUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/menu')
def menu():
    items = MenuItem.query.all()
    return render_template('menu.html', items=items)

@app.route('/add_to_cart/<int:item_id>')
def add_to_cart(item_id):
    cart = session.get('cart', [])
    cart.append(item_id)
    session['cart'] = cart
    return redirect(url_for('menu'))

@app.route('/cart')
def cart():
    cart = session.get('cart', [])
    items = MenuItem.query.filter(MenuItem.id.in_(cart)).all()
    total = sum(item.price for item in items)
    return render_template('cart.html', items=items, total=total)

@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if request.method == 'POST':
        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        cart = session.get('cart', [])
        items = MenuItem.query.filter(MenuItem.id.in_(cart)).all()
        total = sum(item.price for item in items)
        item_ids = ','.join(map(str, cart))
        new_order = Order(customer_name=name, address=address, phone=phone, items=item_ids, total=total)
        db.session.add(new_order)
        db.session.commit()
        session['cart'] = []
        return redirect(url_for('confirmation'))
    return render_template('checkout.html')

@app.route('/confirmation')
def confirmation():
    return render_template('confirmation.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('index'))

@app.route('/admin')
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    orders = Order.query.order_by(Order.timestamp.desc()).all()
    all_items = {item.id: item for item in MenuItem.query.all()}
    return render_template('admin.html', orders=orders, all_items=all_items)

@app.route('/fulfill/<int:order_id>')
def fulfill(order_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    order = Order.query.get(order_id)
    order.fulfilled = True
    db.session.commit()
    return redirect(url_for('admin'))

if __name__ == '__main__':
    if not os.path.exists('restaurant.db'):
        with app.app_context():
            db.create_all()
            if not AdminUser.query.filter_by(username='admin').first():
                admin = AdminUser(username='admin')
                admin.set_password('admin123')
                db.session.add(admin)
                db.session.commit()
    app.run(debug=True)

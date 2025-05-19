
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
    image_url = db.Column(db.String(300), nullable=True) 

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
    cart = session.get('cart', {})
    if isinstance(cart, list):
        cart = {}
    item_id_str = str(item_id)
    cart[item_id_str] = cart.get(item_id_str, 0) + 1
    session['cart'] = cart
    return redirect(url_for('menu'))

@app.route('/add/<int:item_id>')
def add_item(item_id):
    cart = session.get('cart', {})
    item_id_str = str(item_id)
    cart[item_id_str] = cart.get(item_id_str, 0) + 1
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/remove/<int:item_id>')
def remove_item(item_id):
    cart = session.get('cart', {})
    item_id_str = str(item_id)
    if item_id_str in cart:
        if cart[item_id_str] > 1:
            cart[item_id_str] -= 1
        else:
            cart.pop(item_id_str)
    session['cart'] = cart
    return redirect(url_for('cart'))

@app.route('/cart')
def cart():
    cart = session.get('cart', {})
    item_ids = list(cart.keys())
    items = MenuItem.query.filter(MenuItem.id.in_(item_ids)).all()

    cart_items = []
    total = 0
    for item in items:
        quantity = cart[str(item.id)]
        subtotal = item.price * quantity
        cart_items.append({
            'id': item.id,
            'name': item.name,
            'price': item.price,
            'quantity': quantity,
            'subtotal': subtotal
        })
        total += subtotal

    return render_template('cart.html', items=cart_items, total=total)



@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    cart = session.get('cart', {})
    item_ids = list(cart.keys())
    items = MenuItem.query.filter(MenuItem.id.in_(item_ids)).all()

    subtotal = sum(item.price * cart[str(item.id)] for item in items)

    # Only apply fees if subtotal > 0
    if subtotal > 0:
        delivery_fee = 3.00 if subtotal < 15 else 0.00
        service_fee = 1.50
    else:
        delivery_fee = 0.00
        service_fee = 0.00

    total = subtotal + delivery_fee + service_fee

    if request.method == 'POST':
        if subtotal <= 0:
            flash('You must add at least one item to place an order.')
            return redirect(url_for('cart'))

        name = request.form['name']
        address = request.form['address']
        phone = request.form['phone']
        item_str = ','.join([f"{item.id}:{cart[str(item.id)]}" for item in items])
        new_order = Order(customer_name=name, address=address, phone=phone, items=item_str, total=total)
        db.session.add(new_order)
        db.session.commit()
        session['cart'] = {}
        return redirect(url_for('confirmation'))

    return render_template(
        'checkout.html',
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        service_fee=service_fee,
        total=total
    )



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

def seed_menu_items():
    if MenuItem.query.first():
        print(" Menu already seeded.")
        return
    sample_items = [
        MenuItem(name="Margherita Pizza", price=9.99, description="Classic cheese pizza with basil."),
        MenuItem(name="BBQ Burger", price=11.49, description="Beef burger with BBQ sauce and onion rings."),
        MenuItem(name="Caesar Salad", price=7.99, description="Romaine lettuce with creamy Caesar dressing."),
        MenuItem(name="Sushi Platter", price=14.99, description="Assorted sushi rolls with soy sauce."),
        MenuItem(name="Pasta Carbonara", price=12.49, description="Creamy pasta with bacon and parmesan."),
    ]
    db.session.bulk_save_objects(sample_items)
    db.session.commit()
    print(" Menu seeded.")

if __name__ == '__main__':
    with app.app_context():
        if not os.path.exists('restaurant.db'):
            db.create_all()
            print("Database created.")
        seed_menu_items()
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, url_for, flash
from config import Config, db
from models import User, CreditCard, CreditCardApplication, Transaction
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
app.secret_key = 'supersecretkey'

@app.template_filter('date')
def _jinja2_filter_datetime(date, fmt=None):
    if date is None: return ""
    try:
        return date.strftime(fmt or '%d %b, %Y')
    except:
        return str(date)

@app.template_filter('add')
def _jinja2_filter_add(value, arg):
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value

@app.context_processor
def inject_user():
    return dict(
        user=type('User', (), {'is_authenticated': False, 'username': 'Guest', 'is_staff': False, 'is_admin_panel_user': False})(),
        csrf_token='dummy_token'
    )

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid username or password', 'danger')
    return render_template("login.html")

@app.route('/register/', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'warning')
            return redirect(url_for('register'))
            
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template("register.html")

@app.route('/admin-login/', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_dashboard'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()
        if user and user.is_admin and user.check_password(password):
            login_user(user)
            flash('Admin logged in successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin credentials', 'danger')
    return render_template("admin/login.html")

@app.route('/dashboard/')
@login_required
def dashboard():
    cards = current_user.cards.all()
    transactions = Transaction.query.join(CreditCard).filter(CreditCard.user_id == current_user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
    total_balance = sum(float(card.balance) for card in cards)
    return render_template("user/dashboard.html", cards=cards, transactions=transactions, total_balance=total_balance)

@app.route('/apply/', methods=['GET', 'POST'])
@login_required
def apply_card():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        income = request.form.get('income')
        employment_status = request.form.get('employment_status')
        
        application = CreditCardApplication(
            user_id=current_user.id,
            full_name=full_name,
            income=income,
            employment_status=employment_status
        )
        db.session.add(application)
        db.session.commit()
        flash('Application submitted successfully!', 'success')
        return redirect(url_for('dashboard'))
    return render_template("user/apply.html")

@app.route('/transactions/')
@login_required
def transactions():
    transactions = Transaction.query.join(CreditCard).filter(CreditCard.user_id == current_user.id).order_by(Transaction.timestamp.desc()).all()
    return render_template("user/transactions.html", transactions=transactions)

@app.route('/payment/', methods=['GET', 'POST'])
@login_required
def payment():
    cards = current_user.cards.filter_by(status='Active').all()
    if request.method == 'POST':
        card_id = request.form.get('card_id')
        amount = float(request.form.get('amount'))
        description = request.form.get('description')
        category = request.form.get('category')
        
        card = CreditCard.query.get(card_id)
        if card and card.user_id == current_user.id:
            # If it's a bill payment, we subtract from balance. 
            # If it's a purchase, we add to balance. 
            # The template says "Bill Payment", so we subtract.
            card.balance = float(card.balance) - amount
            transaction = Transaction(
                card_id=card.id,
                amount=amount,
                description=description or f"Bill Payment for card ****{card.card_number[-4:]}",
                category=category or "Payment"
            )
            db.session.add(transaction)
            db.session.commit()
            flash('Bill payment successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid card selected', 'danger')
            
    return render_template("user/payment.html", cards=cards)

@app.route('/profile/', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        current_user.phone_number = request.form.get('phone_number')
        current_user.address = request.form.get('address')
        current_user.email = request.form.get('email')
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    return render_template("user/profile.html")

@app.route('/logout/')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/admin-panel/')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied.', 'danger')
        return redirect(url_for('home'))
        
    pending_apps = CreditCardApplication.query.filter_by(status='Pending').all()
    total_users = User.query.filter_by(is_admin=False).count()
    total_cards = CreditCard.query.count()
    all_transactions = Transaction.query.order_by(Transaction.timestamp.desc()).limit(20).all()
    
    return render_template("admin/dashboard.html", 
                           pending_apps=pending_apps, 
                           total_users=total_users, 
                           total_cards=total_cards, 
                           all_transactions=all_transactions)

@app.route('/admin/approve/<int:app_id>/', methods=['POST'])
@login_required
def approve_application(app_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    
    application = CreditCardApplication.query.get_or_404(app_id)
    application.status = 'Approved'
    
    # Auto-generate credit card
    import random
    import datetime
    card_number = "".join([str(random.randint(0, 9)) for _ in range(16)])
    new_card = CreditCard(
        user_id=application.user_id,
        card_number=card_number,
        cvv=str(random.randint(100, 999)),
        expiry_date=datetime.date.today() + datetime.timedelta(days=365*3), # 3 years
        credit_limit=50000.00,
        balance=0.00
    )
    db.session.add(new_card)
    db.session.commit()
    flash(f'Application approved and card {card_number} generated!', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject/<int:app_id>/', methods=['POST'])
@login_required
def reject_application(app_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    application = CreditCardApplication.query.get_or_404(app_id)
    application.status = 'Rejected'
    application.admin_comment = request.form.get('comment')
    db.session.commit()
    flash('Application rejected.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/users/')
@login_required
def admin_users():
    if not current_user.is_admin: return redirect(url_for('home'))
    users = User.query.filter_by(is_admin=False).all()
    return render_template("admin/users.html", users=users)

@app.route('/admin/user/delete/<int:user_id>/', methods=['POST'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted successfully.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/card/status/<int:card_id>/', methods=['POST'])
@login_required
def toggle_card_status(card_id):
    if not current_user.is_admin: return redirect(url_for('home'))
    card = CreditCard.query.get_or_404(card_id)
    card.status = 'Blocked' if card.status == 'Active' else 'Active'
    db.session.commit()
    flash(f'Card {card.card_number} status updated to {card.status}.', 'success')
    return redirect(url_for('admin_dashboard'))

if __name__ == "__main__":
    app.run(debug=True)
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from config import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    phone_number = db.Column(db.String(15))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    cards = db.relationship('CreditCard', backref='owner', lazy='dynamic')
    applications = db.relationship('CreditCardApplication', backref='applicant', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class CreditCard(db.Model):
    __tablename__ = 'credit_cards'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    card_number = db.Column(db.String(16), unique=True, nullable=False)
    cvv = db.Column(db.String(3), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    credit_limit = db.Column(db.Numeric(12, 2), nullable=False)
    balance = db.Column(db.Numeric(12, 2), default=0.00)
    status = db.Column(db.String(10), default='Active') # Active, Blocked
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    transactions = db.relationship('Transaction', backref='card', lazy='dynamic')

    @property
    def available_credit(self):
        return float(self.credit_limit) - float(self.balance)

    def __repr__(self):
        return f'<CreditCard ****{self.card_number[-4:]}>'

class CreditCardApplication(db.Model):
    __tablename__ = 'card_applications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    income = db.Column(db.Numeric(12, 2), nullable=False)
    employment_status = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(10), default='Pending') # Pending, Approved, Rejected
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    admin_comment = db.Column(db.Text)

    def __repr__(self):
        return f'<Application {self.id} for {self.user_id}>'

class Transaction(db.Model):
    __tablename__ = 'transactions'
    id = db.Column(db.Integer, primary_key=True)
    card_id = db.Column(db.Integer, db.ForeignKey('credit_cards.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaction {self.id}: {self.amount}>'

from app import app
from config import db
from models import User

def setup_db():
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        
        # Check if admin exists
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("Creating admin user...")
            admin = User(username='admin', email='admin@ccms.com', is_admin=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Admin user created (username: admin, password: admin123)")
        else:
            print("Admin user already exists.")

if __name__ == "__main__":
    setup_db()

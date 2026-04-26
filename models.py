from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(200))
    email = db.Column(db.String(200))
    phone = db.Column(db.String(50))
    google_id = db.Column(db.String(100), nullable=True)
    is_admin = db.Column(db.Boolean, default=False)
    is_verified = db.Column(db.Boolean, default=False)
    verification_code = db.Column(db.String(10))
    verification_code_expires = db.Column(db.DateTime)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    appointments = db.relationship('Appointment', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Course(db.Model):
    __tablename__ = 'course'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    hours = db.Column(db.Integer, default=15)
    price = db.Column(db.Float, nullable=False)
    vehicle_type = db.Column(db.String(50))  # 2w, 3w, 4w, 6w
    is_active = db.Column(db.Boolean, default=True)


class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Paid')
    booking_date = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    reference_number = db.Column(db.String(50), unique=True)
    vehicle_type = db.Column(db.String(50), default='4w')
    payment = db.relationship('Payment', backref='appointment', uselist=False, cascade='all, delete-orphan')


class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))
    transaction_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(50), default='Paid')
    payment_date = db.Column(db.DateTime)
    reference_number = db.Column(db.String(50))


class CourseReview(db.Model):
    __tablename__ = 'course_review'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))

    # These relationships let you access user data directly
    course = db.relationship('Course', backref='course_reviews')
    user = db.relationship('User', backref='user_reviews')
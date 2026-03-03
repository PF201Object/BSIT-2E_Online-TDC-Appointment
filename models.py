import datetime
from datetime import timezone
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
    is_admin = db.Column(db.Boolean, default=False)
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
    schedules = db.relationship('Schedule', backref='course', lazy=True)


class Schedule(db.Model):
    __tablename__ = 'schedule'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    session_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.String(10), nullable=False)
    end_time = db.Column(db.String(10), nullable=False)  # Fixed: removed extra '.db'
    available_slots = db.Column(db.Integer, default=20)
    total_slots = db.Column(db.Integer, default=20)
    location = db.Column(db.String(100), default='EcoDrive Main Center')
    appointments = db.relationship('Appointment', backref='schedule', lazy=True)


class Appointment(db.Model):
    __tablename__ = 'appointment'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    schedule_id = db.Column(db.Integer, db.ForeignKey('schedule.id'), nullable=False)
    full_name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    contact_number = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(100))
    status = db.Column(db.String(50), default='Pending')  # Pending, Confirmed, Completed, Cancelled
    booking_date = db.Column(db.DateTime, default=lambda: datetime.datetime.now(timezone.utc))
    reference_number = db.Column(db.String(50), unique=True)
    payment = db.relationship('Payment', backref='appointment', uselist=False, cascade='all, delete-orphan')


class Payment(db.Model):
    __tablename__ = 'payment'
    id = db.Column(db.Integer, primary_key=True)
    appointment_id = db.Column(db.Integer, db.ForeignKey('appointment.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(50))  # GCash, Credit Card, Over-the-Counter, etc.
    transaction_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(50), default='Unpaid')  # Unpaid, Paid, Refunded
    payment_date = db.Column(db.DateTime)
    reference_number = db.Column(db.String(50))
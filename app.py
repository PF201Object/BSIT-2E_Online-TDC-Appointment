import os
import datetime
import random
import string
from datetime import timedelta, timezone, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Course, Schedule, Appointment, Payment
from datetime import datetime, date, timedelta
from sqlalchemy import func
import time
from sqlalchemy.exc import OperationalError

app = Flask(__name__)
app.secret_key = 'eco_drive_theory_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///RonGwafo.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

# Add these lines
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 60,
    'pool_pre_ping': True,
    'connect_args': {
        'timeout': 30,
        'check_same_thread': False
    }
}

db.init_app(app)


# Helper Functions
def generate_reference():
    return 'TDC-' + str(random.randint(2025, 2026)) + '-' + ''.join(random.choices(string.digits, k=4))


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


# Routes
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            session.permanent = True
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')

            if user.is_admin:
                return redirect(url_for('admin_dashboard'))
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')

        if password != confirm:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))

        existing = User.query.filter_by(username=username).first()
        if existing:
            flash('Username already exists', 'danger')
            return redirect(url_for('register'))

        user = User(
            username=username,
            full_name=full_name,
            email=email,
            phone=phone,
            is_admin=False
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(user_id=user.id).order_by(Appointment.booking_date.desc()).all()
    return render_template('dashboard.html', user=user, appointments=appointments)


@app.route('/booking', methods=['GET'])
@login_required
def booking():
    user = User.query.get(session['user_id'])
    courses = Course.query.filter_by(is_active=True).all()

    # Get available dates (tomorrow and next 14 days)
    available_dates = []
    tomorrow = date.today() + timedelta(days=1)

    for i in range(14):  # Show next 14 days
        current_date = tomorrow + timedelta(days=i)
        # Count appointments for this date
        appointment_count = db.session.query(func.count(Appointment.id)).filter(
            func.date(Appointment.booking_date) == current_date
        ).scalar()

        # Max 20 slots per day
        available_slots = max(0, 20 - appointment_count)

        available_dates.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'day': current_date.strftime('%A'),
            'day_num': current_date.strftime('%d'),
            'month': current_date.strftime('%b'),
            'slots': available_slots,
            'full': current_date.strftime('%B %d, %Y')
        })

    return render_template('booking.html',
                           user=user,
                           courses=courses,
                           available_dates=available_dates)


# New route for step 2 - Information
@app.route('/booking/information', methods=['POST'])
@login_required
def booking_information():
    # Store selected date/time in session
    session['booking_date'] = request.form.get('preferred_date')
    session['booking_time'] = request.form.get('preferred_time')

    user = User.query.get(session['user_id'])
    return render_template('booking_info.html', user=user, step=2)  # ← ADD step=2


@app.route('/booking/vehicle', methods=['POST'])
@login_required
def booking_vehicle():
    # Store user info in session
    session['booking_full_name'] = request.form.get('full_name')
    session['booking_email'] = request.form.get('email')
    session['booking_contact'] = request.form.get('contact_number')
    session['booking_location'] = request.form.get('location')

    # IMPORTANT: Fetch courses from database
    courses = Course.query.filter_by(is_active=True).all()

    # Debug: Print to console to verify courses are found
    print(f"Found {len(courses)} courses")
    for course in courses:
        print(f"Course: {course.name}, Vehicle: {course.vehicle_type}, Price: {course.price}")

    return render_template('booking_vehicle.html', courses=courses)


@app.route('/booking/payment', methods=['POST'])
@login_required
def booking_payment():
    # Store vehicle selection
    session['booking_vehicle'] = request.form.get('vehicle_type')
    course = Course.query.filter_by(vehicle_type=session['booking_vehicle']).first()
    session['booking_amount'] = course.price if course else 1500.00

    return render_template('booking_payment.html',
                           amount=session['booking_amount'],
                           vehicle=session['booking_vehicle'],
                           step=4)  # ← ADD step=4


# New route for step 3 - Vehicle
# Process final appointment (pending)
import time
from sqlalchemy.exc import OperationalError


@app.route('/booking/process', methods=['POST'])
@login_required
def booking_process():
    user = User.query.get(session['user_id'])

    # Get payment method from form
    payment_method = request.form.get('payment_method')

    # Generate reference number
    ref = 'TDC-' + datetime.now().strftime('%Y%m%d') + '-' + str(random.randint(1000, 9999))

    # Find or create schedule
    booking_date = datetime.strptime(session.get('booking_date'), '%Y-%m-%d').date()

    # Retry logic for database locking
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create appointment with PENDING status
            appointment = Appointment(
                user_id=user.id,
                schedule_id=1,  # You might want to create proper schedule records
                full_name=session.get('booking_full_name', user.full_name or user.username),
                email=session.get('booking_email', user.email),
                contact_number=session.get('booking_contact', user.phone or ''),
                location=session.get('booking_location', 'EcoDrive Main Center'),
                status='Pending',  # Always pending, admin will approve
                booking_date=datetime.now(),
                reference_number=ref
            )

            db.session.add(appointment)
            db.session.flush()  # Get appointment ID

            # Create payment record (pending)
            payment = Payment(
                appointment_id=appointment.id,
                amount=session.get('booking_amount', 1500.00),
                payment_method=payment_method,
                transaction_id='TXN' + datetime.now().strftime('%Y%m%d%H%M%S'),
                status='Pending',  # Pending until admin approves
                reference_number='PAY-' + ref
            )

            db.session.add(payment)
            db.session.commit()

            # Clear session booking data
            for key in ['booking_date', 'booking_time', 'booking_full_name', 'booking_email',
                        'booking_contact', 'booking_location', 'booking_vehicle', 'booking_amount']:
                session.pop(key, None)

            return redirect(url_for('booking_confirmation', ref=ref))

        except OperationalError as e:
            if 'database is locked' in str(e):
                retry_count += 1
                db.session.rollback()
                time.sleep(1)  # Wait 1 second before retrying
                print(f"Database locked, retrying... ({retry_count}/{max_retries})")
            else:
                raise e

    # If we get here, all retries failed
    flash('The system is busy. Please try again in a moment.', 'danger')
    return redirect(url_for('booking'))

@app.route('/booking/confirmation/<ref>')
@login_required
def booking_confirmation(ref):
    appointment = Appointment.query.filter_by(reference_number=ref).first()
    payment = Payment.query.filter_by(appointment_id=appointment.id).first() if appointment else None

    return render_template('booking_confirmation.html',
                           appointment=appointment,
                           payment=payment)


@app.route('/create_appointment', methods=['POST'])
@login_required
def create_appointment():
    user = User.query.get(session['user_id'])

    full_name = request.form.get('full_name', user.full_name or user.username)
    email = request.form.get('email', user.email)
    contact = request.form.get('contact_number')
    location = request.form.get('location')
    preferred_date = request.form.get('preferred_date')
    preferred_time = request.form.get('preferred_time')

    # Create appointment with pending status
    ref = generate_reference()
    appointment = Appointment(
        user_id=user.id,
        schedule_id=1,  # Default for demo
        full_name=full_name,
        email=email,
        contact_number=contact,
        location=location,
        status='Pending',
        reference_number=ref
    )

    db.session.add(appointment)
    db.session.commit()

    session['pending_appointment'] = appointment.id
    return redirect(url_for('payment', appt_id=appointment.id))


@app.route('/payment/<int:appt_id>', methods=['GET', 'POST'])
@login_required
def payment(appt_id):
    appointment = Appointment.query.get_or_404(appt_id)

    # Ensure user owns this appointment
    if appointment.user_id != session['user_id'] and not session.get('is_admin'):
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        vehicle = request.form.get('vehicle_type')
        payment_method = request.form.get('payment_method')

        # Process payment (simulated)
        amount = 1500.00  # Default price
        if '4w' in vehicle:
            amount = 2500.00

        transaction_id = 'TXN' + ''.join(random.choices(string.digits, k=10))

        payment = Payment(
            appointment_id=appointment.id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            status='Paid',
            payment_date=datetime.datetime.now(timezone.utc),
            reference_number=generate_reference()
        )

        appointment.status = 'Confirmed'

        db.session.add(payment)
        db.session.commit()

        return redirect(url_for('confirmation', appt_id=appointment.id))

    return render_template('payment.html', appointment=appointment)


@app.route('/confirmation/<int:appt_id>')
@login_required
def confirmation(appt_id):
    appointment = Appointment.query.get_or_404(appt_id)
    payment = Payment.query.filter_by(appointment_id=appt_id).first()

    return render_template('confirmation.html', appointment=appointment, payment=payment)


@app.route('/my-appointments')
@login_required
def my_appointments():
    user = User.query.get(session['user_id'])
    appointments = Appointment.query.filter_by(user_id=user.id).order_by(Appointment.booking_date.desc()).all()
    return render_template('my_appointments.html', appointments=appointments)


@app.route('/admin')
@admin_required
def admin_dashboard():
    users_count = User.query.count()
    appointments_count = Appointment.query.count()
    pending_count = Appointment.query.filter_by(status='Pending').count()
    confirmed_count = Appointment.query.filter_by(status='Confirmed').count()

    # Get pending payments (only those with actual payment records)
    pending_payments = Payment.query.filter_by(status='Pending').all()

    recent_appointments = Appointment.query.order_by(Appointment.booking_date.desc()).limit(10).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    return render_template('admin.html',
                           users_count=users_count,
                           appointments_count=appointments_count,
                           pending_count=pending_count,
                           confirmed_count=confirmed_count,
                           pending_payments=pending_payments,  # Make sure this is passed
                           recent_appointments=recent_appointments,
                           recent_users=recent_users)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/appointments')
@admin_required
def admin_appointments():
    appointments = Appointment.query.order_by(Appointment.booking_date.desc()).all()
    return render_template('admin_appointments.html', appointments=appointments)


@app.route('/admin/appointment/<int:appt_id>')
@admin_required
def admin_appointment_detail(appt_id):
    appointment = Appointment.query.get_or_404(appt_id)
    return render_template('admin_appointment_detail.html', appointment=appointment)


@app.route('/admin/approve-payment/<int:payment_id>', methods=['POST'])
@admin_required
def approve_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    payment.status = 'Paid'
    payment.payment_date = datetime.now()

    appointment = Appointment.query.get(payment.appointment_id)
    appointment.status = 'Confirmed'

    db.session.commit()
    flash(f'Payment approved for {appointment.full_name}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/manage-schedules')
@admin_required
def manage_schedules():
    # For demo, create sample schedules if none exist
    if Schedule.query.count() == 0:
        course = Course.query.first()
        if not course:
            course = Course(name='TDC - 15 Hours', description='Theoretical Driving Course', hours=15, price=1500.00,
                            vehicle_type='4w')
            db.session.add(course)
            db.session.commit()

        for i in range(1, 11):
            d = date.today() + timedelta(days=i)
            schedule = Schedule(
                course_id=course.id,
                session_date=d,
                start_time='08:00 AM',
                end_time='11:00 AM',
                available_slots=20,
                total_slots=20,
                location='EcoDrive Main Center'
            )
            db.session.add(schedule)
        db.session.commit()

    schedules = Schedule.query.order_by(Schedule.session_date).all()
    return render_template('manage_schedules.html', schedules=schedules)

@app.route('/courses')
def courses():
    """Display available courses"""
    from models import Course
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('courses.html', courses=courses)


# Initialize database and sample data
@app.cli.command('init-db')
def init_db():
    db.create_all()

    # Create admin user
    admin = User(
        username='admin',
        full_name='System Administrator',
        email='admin@ecodrive.com',
        phone='09123456789',
        is_admin=True
    )
    admin.set_password('admin123')
    db.session.add(admin)

    # Create sample courses
    courses = [
        Course(name='TDC - Motorcycle (2 wheels)', description='Theoretical Driving Course for motorcycles', hours=15,
               price=1200.00, vehicle_type='2w'),
        Course(name='TDC - Tricycle (3 wheels)', description='Theoretical Driving Course for tricycles', hours=15,
               price=1350.00, vehicle_type='3w'),
        Course(name='TDC - Car (4 wheels)', description='Theoretical Driving Course for cars and SUVs', hours=15,
               price=1500.00, vehicle_type='4w'),
        Course(name='TDC - Truck/Bus (6+ wheels)', description='Theoretical Driving Course for heavy vehicles',
               hours=15, price=2000.00, vehicle_type='6w'),
    ]

    for course in courses:
        db.session.add(course)

    db.session.commit()
    print("Database initialized with admin user and sample courses.")

@app.teardown_appcontext
def shutdown_session(exception=None):
    db.session.remove()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
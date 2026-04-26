import os
import datetime
import random
import string
import threading
from datetime import time
from datetime import timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from models import db, User, Course, Appointment, Payment
from datetime import date, timedelta
from sqlalchemy import func
from flask_mail import Mail, Message
from authlib.integrations.flask_client import OAuth
from flask import jsonify


app = Flask(__name__)
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.secret_key = 'eco_drive_theory_secret_key_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///RonGwafo.db?timeout=30'
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

# ===== EMAIL CONFIGURATION =====
# Gmail SMTP Settings
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
# IMPORTANT: Replace these with your actual credentials
app.config['MAIL_USERNAME'] = 'ecodrive.support@gmail.com'  # ← REPLACE WITH YOUR GMAIL
app.config['MAIL_PASSWORD'] = 'afhe lxbt pjce nqle'     # ← REPLACE WITH APP PASSWORD
app.config['MAIL_DEFAULT_SENDER'] = 'ronbell112323@gmail.com'  # ← REPLACE WITH YOUR GMAIL

# Initialize Mail
mail = Mail(app)
# ===== END EMAIL CONFIGURATION =====

# ===== VERIFICATION CODE HELPER FUNCTIONS =====
import secrets
from datetime import datetime, timedelta

def generate_verification_code():
    """Generate a 6-digit verification code"""
    return f"{secrets.randbelow(1000000):06d}"

def send_verification_email(user_email, code):
    """Send 6-digit verification code to user's email"""
    try:
        msg = Message(
            subject="🔐 Email Verification - EcoDrive Theory",
            recipients=[user_email],
            html=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Email Verification</title>
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 500px; margin: 0 auto; padding: 20px; }}
                    .header {{ background: linear-gradient(135deg, #0f5e7a, #1a4b63); color: white; padding: 20px; text-align: center; border-radius: 15px 15px 0 0; }}
                    .content {{ background: #f5fcff; padding: 25px; border-radius: 0 0 15px 15px; }}
                    .code {{ font-size: 32px; font-weight: bold; color: #0f5e7a; text-align: center; padding: 20px; letter-spacing: 5px; }}
                    .footer {{ text-align: center; padding: 15px; color: #666; font-size: 12px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h2>🔐 Email Verification</h2>
                    </div>
                    <div class="content">
                        <p>Hello,</p>
                        <p>Thank you for registering with EcoDrive Theory! Please use the verification code below to complete your registration:</p>
                        <div class="code">{code}</div>
                        <p>This code will expire in <strong>10 minutes</strong>.</p>
                        <p>If you didn't request this, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>© 2026 EcoDrive Theory | LTO Accredited Driving School</p>
                    </div>
                </div>
            </body>
            </html>
            """
        )
        mail.send(msg)
        print(f"✅ Verification email sent to {user_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send verification email: {e}")
        return False
# ===== END VERIFICATION CODE HELPER FUNCTIONS =====

# ===== GOOGLE OAUTH CONFIGURATION =====
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id='480746447250-jjds880rmdlum3mo3povm8kk5a4ccmb7.apps.googleusercontent.com',  # ← Replace with your actual Client ID
    client_secret='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',  # ← Replace with your actual Client Secret
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)
# ===== END GOOGLE OAUTH CONFIGURATION =====

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
        user = db.session.get(User, session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)

    return decorated_function


# ===== GOOGLE LOGIN ROUTES =====

@app.before_request
def update_last_seen():
    """Update user's last seen timestamp on every request"""
    if 'user_id' in session:
        user = db.session.get(User, session['user_id'])
        if user:
            user.last_seen = datetime.now()
            db.session.commit()

@app.route('/login/google')
def google_login():
    """Redirect to Google OAuth login page"""
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/login/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get user info from Google
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token, nonce=None)

        email = user_info.get('email')
        name = user_info.get('name')
        google_id = user_info.get('sub')

        print(f"🔐 Google login attempt: email={email}, google_id={google_id}")

        # Check if user exists by email OR google_id
        user = User.query.filter_by(email=email).first()
        
        # If user exists but no google_id, update it
        if user and not user.google_id:
            user.google_id = google_id
            db.session.commit()
            print(f"✅ Updated google_id for existing user: {email}")

        if not user:
            # Create new user
            username = email.split('@')[0]
            counter = 1
            original_username = username
            while User.query.filter_by(username=username).first():
                username = f"{original_username}{counter}"
                counter += 1

            print(f"📝 Creating new user: username={username}, email={email}")

            user = User(
                username=username,
                email=email,
                full_name=name,
                phone='',
                is_admin=False,
                is_verified=True,
                google_id=google_id
            )
            random_password = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
            user.set_password(random_password)

            db.session.add(user)
            db.session.commit()

            flash(f'Welcome {name}! Your account has been created.', 'success')
        else:
            flash(f'Welcome back, {user.full_name or user.username}!', 'success')

        session['user_id'] = user.id
        session['username'] = user.username
        session['is_admin'] = user.is_admin
        session.permanent = True

        print(f"✅ User logged in: {user.username}")

        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"❌ Google login error: {e}")
        import traceback
        traceback.print_exc()
        flash('Google login failed. Please try again.', 'danger')
        return redirect(url_for('login'))


# ===== END GOOGLE LOGIN ROUTES =====

# ===== EMAIL HELPER FUNCTION =====
def send_booking_email_background(user_email, user_name, booking_details):
    """Send booking confirmation email in background (non-blocking)"""

    def send():
        with app.app_context():
            try:
                # Create message inside app context
                vehicle_names = {'2w': 'Motorcycle', '3w': 'Tricycle', '4w': 'Car', '6w': 'Truck/Bus'}
                vehicle_display = vehicle_names.get(booking_details.get('vehicle_code', '4w'), 'Car')

                msg = Message(
                    subject="✅ Booking Confirmation - EcoDrive Theory",
                    recipients=[user_email],
                    html=f"""
                    <!DOCTYPE html>
                    <html>
                    <head><meta charset="UTF-8"><title>Booking Confirmation</title>
                    <style>
                        body {{ font-family: 'Segoe UI', Arial, sans-serif; }}
                        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: linear-gradient(135deg, #0f5e7a, #1a4b63); color: white; padding: 25px; text-align: center; }}
                        .content {{ background: #f5fcff; padding: 25px; }}
                        .details {{ background: white; padding: 20px; border-radius: 12px; margin: 20px 0; }}
                        .amount {{ font-size: 28px; font-weight: bold; color: #28a745; }}
                        .checkmark {{ font-size: 48px; margin-bottom: 10px; }}
                        .status-badge {{ background: #28a745; color: white; padding: 5px 15px; border-radius: 20px; }}
                    </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="header"><div class="checkmark">✅</div><h2>Booking Confirmed!</h2></div>
                            <div class="content">
                                <p>Dear <strong>{user_name}</strong>,</p>
                                <p>Thank you for choosing EcoDrive Theory! Your booking has been confirmed.</p>
                                <div class="details">
                                    <p><strong>Reference:</strong> {booking_details['reference']}</p>
                                    <p><strong>Booking Date:</strong> {booking_details['booking_date']}</p>
                                    <p><strong>Vehicle Type:</strong> {vehicle_display}</p>
                                    <p><strong>Location:</strong> {booking_details['location']}</p>
                                    <p><strong>Amount Paid:</strong> <span class="amount">₱{booking_details['amount']}</span></p>
                                    <p><strong>Status:</strong> <span class="status-badge">✅ Booked</span></p>
                                </div>
                                <p>Present this email on your appointment date. Arrive 15 minutes early.</p>
                            </div>
                        </div>
                    </body>
                    </html>
                    """
                )
                mail.send(msg)
                print(f"✅ Background email sent to {user_email}")
                with open('/tmp/ecodrive_email_error.log', 'a') as log:
                    log.write(f"✅ Email sent successfully to {user_email}\n")
            except Exception as e:
                print(f"❌ Background email error: {e}")
                with open('/tmp/ecodrive_email_error.log', 'a') as log:
                    log.write(f"ERROR: {str(e)}\n")
                    import traceback
                    traceback.print_exc(file=log)

    thread = threading.Thread(target=send)
    thread.start()
    return True


def send_booking_confirmation_email(user_email, user_name, booking_details):
    """Legacy function - kept for compatibility"""
    # Just call the background function
    return send_booking_email_background(user_email, user_name, booking_details)


# ===== END EMAIL HELPER FUNCTION =====

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
            # Update last_seen timestamp
            user.last_seen = datetime.now()
            db.session.commit()

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

        # Check if username already exists (regardless of verification status)
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            flash('Username already exists. Please choose another username.', 'danger')
            return redirect(url_for('register'))

        # Check if email is already verified
        existing_verified_email = User.query.filter_by(email=email, is_verified=True).first()
        if existing_verified_email:
            flash('This email is already registered and verified. Please login instead.', 'danger')
            return redirect(url_for('login'))

        # Check if there's an existing unverified account with this email
        existing_unverified = User.query.filter_by(email=email, is_verified=False).first()

        if existing_unverified:
            # Delete the old unverified account
            db.session.delete(existing_unverified)
            db.session.commit()
            flash('Previous unverified account removed. Please register again.', 'info')

        # Generate verification code
        verification_code = generate_verification_code()
        code_expires = datetime.now() + timedelta(minutes=10)

        # Create new user with unverified status
        user = User(
            username=username,
            full_name=full_name,
            email=email,
            phone=phone,
            is_admin=False,
            is_verified=False,
            verification_code=verification_code,
            verification_code_expires=code_expires
        )
        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Send verification email
        if send_verification_email(email, verification_code):
            # Store user ID in session for verification
            session['pending_verification_user_id'] = user.id
            flash('Verification code sent to your email. Please enter it below.', 'info')
            return redirect(url_for('verify_email'))
        else:
            # If email fails, delete the user to avoid orphaned accounts
            db.session.delete(user)
            db.session.commit()
            flash('Failed to send verification email. Please try again.', 'danger')
            return redirect(url_for('register'))

    return render_template('register.html')


@app.route('/verify-email', methods=['GET', 'POST'])
def verify_email():
    """Page to enter 6-digit verification code"""
    if 'pending_verification_user_id' not in session:
        flash('Please register first', 'warning')
        return redirect(url_for('register'))

    user_id = session['pending_verification_user_id']
    user = User.query.get(user_id)

    if not user:
        session.pop('pending_verification_user_id', None)
        flash('Registration session expired. Please register again.', 'danger')
        return redirect(url_for('register'))

    if request.method == 'POST':
        entered_code = request.form.get('verification_code')

        # Check if code matches and not expired
        if user.verification_code == entered_code:
            if datetime.now() <= user.verification_code_expires:
                # Code is correct and not expired
                user.is_verified = True
                user.verification_code = None
                user.verification_code_expires = None
                db.session.commit()

                session.pop('pending_verification_user_id', None)
                flash('Email verified successfully! Please login.', 'success')
                return redirect(url_for('login'))
            else:
                flash('Verification code has expired. Please request a new one.', 'danger')
        else:
            flash('Invalid verification code. Please try again.', 'danger')

    return render_template('verify_email.html', email=user.email)


@app.route('/resend-code', methods=['POST'])
def resend_code():
    """Resend verification code"""
    if 'pending_verification_user_id' not in session:
        flash('Please register first', 'warning')
        return redirect(url_for('register'))

    user_id = session['pending_verification_user_id']
    user = User.query.get(user_id)

    if not user:
        session.pop('pending_verification_user_id', None)
        flash('Registration session expired. Please register again.', 'danger')
        return redirect(url_for('register'))

    # Generate new code
    new_code = generate_verification_code()
    user.verification_code = new_code
    user.verification_code_expires = datetime.now() + timedelta(minutes=10)
    db.session.commit()

    # Send new code
    if send_verification_email(user.email, new_code):
        flash('New verification code sent to your email!', 'success')
    else:
        flash('Failed to send verification email. Please try again.', 'danger')

    return redirect(url_for('verify_email'))


@app.route('/check-email')
def check_email():
    """API endpoint to check if email exists (verified OR unverified)"""
    email = request.args.get('email', '')
    if not email:
        return jsonify({'exists': False, 'verified': False})

    # Check for any account with this email (verified or not)
    user = User.query.filter_by(email=email).first()

    if user:
        # If email exists but is verified, suggest login
        if user.is_verified:
            return jsonify({'exists': True, 'verified': True, 'message': 'Email already registered. Please login.'})
        else:
            # Email exists but not verified - we'll allow re-registration
            return jsonify(
                {'exists': False, 'verified': False, 'message': 'Previous unverified account will be replaced.'})

    return jsonify({'exists': False, 'verified': False})


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

    # Get available dates (starting from tomorrow, weekdays only, 30 days ahead)
    available_dates = []
    today = date.today()
    start_date = today + timedelta(days=1)  # Start from tomorrow
    end_date = today + timedelta(days=30)  # Show next 30 days

    current_date = start_date
    while current_date <= end_date:
        # Skip weekends (Saturday = 5, Sunday = 6 in Python's weekday where Monday=0)
        # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4, Saturday=5, Sunday=6
        if current_date.weekday() < 5:  # 0-4 = Monday to Friday
            # Count appointments for this date
            appointment_count = db.session.query(func.count(Appointment.id)).filter(
                func.date(Appointment.booking_date) == current_date
            ).scalar() or 0

            # Max 20 slots per day
            available_slots = max(0, 20 - appointment_count)

            # Only show dates that are not fully booked OR future dates
            if available_slots > 0 or current_date > today:
                available_dates.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day': current_date.strftime('%A'),
                    'day_num': current_date.strftime('%d'),
                    'month': current_date.strftime('%b'),
                    'month_full': current_date.strftime('%B'),
                    'year': current_date.strftime('%Y'),
                    'slots': available_slots,
                    'full': current_date.strftime('%B %d, %Y'),
                    'is_available': available_slots > 0,
                    'is_weekend': False
                })
        current_date += timedelta(days=1)

    return render_template('booking.html',
                           user=user,
                           courses=courses,
                           available_dates=available_dates,
                           today=today)


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
    # DEBUG: Print all form data received
    print("=" * 50)
    print("FORM DATA RECEIVED:")
    print(f"vehicle_type: {request.form.get('vehicle_type')}")
    print(f"amount: {request.form.get('amount')}")
    print("=" * 50)

    # Store vehicle selection
    session['booking_vehicle'] = request.form.get('vehicle_type')

    # Get the amount from the form
    amount = request.form.get('amount')

    # If amount wasn't passed, get it from the course
    if amount:
        session['booking_amount'] = float(amount)
    else:
        course = Course.query.filter_by(vehicle_type=session['booking_vehicle']).first()
        session['booking_amount'] = course.price if course else 1500.00

    print(f"SESSION AFTER:")
    print(f"booking_vehicle: {session.get('booking_vehicle')}")
    print(f"booking_amount: {session.get('booking_amount')}")

    # Get the current user
    user = db.session.get(User, session['user_id'])

    return render_template('booking_payment.html',
                           amount=session['booking_amount'],
                           vehicle=session['booking_vehicle'],
                           user=user,
                           step=4)
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

    # Get selected date
    booking_date_str = session.get('booking_date')
    if not booking_date_str:
        flash('Please select a date', 'danger')
        return redirect(url_for('booking'))

    booking_date = datetime.strptime(booking_date_str, '%Y-%m-%d').date()

    # Check if date is valid (not past, not weekend)
    today = date.today()
    if booking_date <= today:
        flash('Cannot book for past dates', 'danger')
        return redirect(url_for('booking'))

    if booking_date.weekday() >= 5:  # Saturday or Sunday
        flash('Bookings are only available on weekdays (Monday to Friday)', 'danger')
        return redirect(url_for('booking'))

    # Check available slots for this date
    appointment_count = db.session.query(func.count(Appointment.id)).filter(
        func.date(Appointment.booking_date) == booking_date
    ).scalar() or 0

    if appointment_count >= 20:
        flash('This date is fully booked. Please select another date.', 'danger')
        return redirect(url_for('booking'))

    # Generate reference number
    ref = 'TDC-' + datetime.now().strftime('%Y%m%d') + '-' + str(random.randint(1000, 9999))

    # Get vehicle type from session
    vehicle_type = session.get('booking_vehicle', '4w')

    # Generate transaction ID
    transaction_id = 'TXN' + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(100, 999))

    print(f"📝 Saving appointment with vehicle_type: {vehicle_type}")
    print(f"📝 Transaction ID: {transaction_id}")

    # Retry logic for database locking
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            # Create appointment
            appointment = Appointment(
                user_id=user.id,
                full_name=session.get('booking_full_name', user.full_name or user.username),
                email=session.get('booking_email', user.email),
                contact_number=session.get('booking_contact', user.phone or ''),
                location=session.get('booking_location', 'EcoDrive Main Center'),
                status='Paid',
                booking_date=datetime.combine(booking_date, datetime.now().time()),
                reference_number=ref,
                vehicle_type=vehicle_type
            )

            db.session.add(appointment)
            db.session.flush()

            # Create payment record with transaction_id and payment_date
            payment = Payment(
                appointment_id=appointment.id,
                amount=session.get('booking_amount', 1500.00),
                payment_method=payment_method,
                transaction_id=transaction_id,  # ← Generated transaction ID
                status='Paid',
                payment_date=datetime.now(),  # ← Current date and time
                reference_number='PAY-' + ref
            )

            db.session.add(payment)
            db.session.commit()

            # ===== SEND EMAIL NOTIFICATION =====
            # Prepare booking details for email
            booking_details = {
                'reference': ref,
                'transaction_id': transaction_id,
                'booking_date': booking_date.strftime('%B %d, %Y'),
                'vehicle_code': vehicle_type,
                'location': session.get('booking_location', 'EcoDrive Main Center'),
                'amount': f"{session.get('booking_amount', 1500.00):.2f}",
                'payment_method': payment_method
            }

            # Get user email and name from session
            user_email = session.get('booking_email', user.email)
            user_name = session.get('booking_full_name', user.full_name or user.username)

            # Send email (doesn't block if it fails)
            try:
                import sys; sys.stdout.flush(); print(f"📧 ATTEMPTING to send email to {user_email}")
                send_booking_email_background(user_email, user_name, booking_details)
                print(f"📧 Email function completed for {user_email}")
            except Exception as email_error:
                print(f"⚠️ Email error: {email_error}")
            # ===== END EMAIL NOTIFICATION =====

            # Clear session booking data
            for key in ['booking_date', 'booking_time', 'booking_full_name', 'booking_email',
                        'booking_contact', 'booking_location', 'booking_vehicle', 'booking_amount']:
                session.pop(key, None)

            return redirect(url_for('booking_receipt', ref=ref))

        except OperationalError as e:
            if 'database is locked' in str(e):
                retry_count += 1
                db.session.rollback()
                time.sleep(1)
                print(f"Database locked, retrying... ({retry_count}/{max_retries})")
            else:
                raise e

    flash('The system is busy. Please try again in a moment.', 'danger')
    return redirect(url_for('booking'))

@app.route('/booking/receipt/<ref>')
@login_required
def booking_receipt(ref):
    """Display printable receipt after payment"""
    from datetime import datetime
    appointment = Appointment.query.filter_by(reference_number=ref).first()
    if not appointment:
        flash('Receipt not found', 'danger')
        return redirect(url_for('dashboard'))

    payment = Payment.query.filter_by(appointment_id=appointment.id).first()

    return render_template('booking_receipt.html',
                           appointment=appointment,
                           payment=payment,
                           datetime=datetime)


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

    # Generate reference number
    ref = generate_reference()

    appointment = Appointment(
        user_id=user.id,
        full_name=full_name,
        email=email,
        contact_number=contact,
        location=location,
        status='Pending',
        booking_date=datetime.now(),
        reference_number=ref,
        vehicle_type='4w'  # Default vehicle type
    )

    db.session.add(appointment)
    db.session.commit()

    session['pending_appointment'] = appointment.id
    return redirect(url_for('payment', appt_id=appointment.id))


@app.route('/course/<int:course_id>')
def course_detail(course_id):
    """Display detailed information about a specific course"""
    from models import CourseReview

    course = Course.query.get_or_404(course_id)
    reviews = CourseReview.query.filter_by(course_id=course_id).order_by(CourseReview.created_at.desc()).all()

    # Attach user names to each review
    for review in reviews:
        user = User.query.get(review.user_id)
        review.user_name = user.full_name if user else 'Student'

    # Calculate average rating
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
    else:
        avg_rating = 0

    # Check if user has already reviewed
    has_reviewed = False
    if 'user_id' in session:
        has_reviewed = CourseReview.query.filter_by(
            course_id=course_id,
            user_id=session['user_id']
        ).first() is not None

    return render_template('course_detail.html',
                           course=course,
                           reviews=reviews,
                           avg_rating=avg_rating,
                           has_reviewed=has_reviewed)


@app.route('/course/<int:course_id>/review', methods=['POST'])
@login_required
def add_review(course_id):
    """Add a review for a course"""
    from models import CourseReview

    rating = request.form.get('rating')
    comment = request.form.get('comment')

    if not rating or not comment:
        flash('Please provide both rating and comment', 'danger')
        return redirect(url_for('course_detail', course_id=course_id))

    # Check if user already reviewed
    existing_review = CourseReview.query.filter_by(
        course_id=course_id,
        user_id=session['user_id']
    ).first()

    if existing_review:
        flash('You have already reviewed this course', 'warning')
        return redirect(url_for('course_detail', course_id=course_id))

    review = CourseReview(
        course_id=course_id,
        user_id=session['user_id'],
        rating=int(rating),
        comment=comment
    )

    db.session.add(review)
    db.session.commit()

    flash('Thank you for your review!', 'success')
    return redirect(url_for('course_detail', course_id=course_id))


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
    from datetime import datetime, timedelta
    from sqlalchemy import func, extract

    users_count = User.query.count()
    appointments_count = Appointment.query.count()

    # Get today's date
    today = date.today()
    first_day_of_month = date(today.year, today.month, 1)

    # Get Booked appointments (Paid status - automatically booked)
    booked_count = Appointment.query.filter_by(status='Paid').count()

    # Today's booked appointments
    today_booked = Appointment.query.filter(
        func.date(Appointment.booking_date) == today,
        Appointment.status == 'Paid'
    ).count()

    # Total revenue from Paid appointments
    total_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'Paid'
    ).scalar() or 0

    # Today's revenue
    today_revenue = db.session.query(func.sum(Payment.amount)).filter(
        func.date(Payment.payment_date) == today,
        Payment.status == 'Paid'
    ).scalar() or 0

    # This month's revenue
    monthly_revenue = db.session.query(func.sum(Payment.amount)).filter(
        Payment.status == 'Paid',
        func.date(Payment.payment_date) >= first_day_of_month
    ).scalar() or 0

    # Get pending payments (if any - for manual approval, but now auto-booked)
    pending_payments = Payment.query.filter_by(status='Pending').all()

    # Recent appointments (last 10)
    recent_appointments = Appointment.query.order_by(Appointment.booking_date.desc()).limit(10).all()

    # Recent users (last 10)
    recent_users = User.query.order_by(User.created_at.desc()).limit(10).all()

    for user in recent_users:
        if user.last_seen:
            try:
                time_diff = (datetime.now() - user.last_seen).total_seconds()
                user.is_online = time_diff < 300  # Online if active within last 5 minutes
            except:
                user.is_online = False
        else:
            user.is_online = False

    # Get daily revenue for last 7 days (for chart)
    daily_revenue = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        revenue = db.session.query(func.sum(Payment.amount)).filter(
            func.date(Payment.payment_date) == day,
            Payment.status == 'Paid'
        ).scalar() or 0
        daily_revenue.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%Y-%m-%d'),
            'revenue': float(revenue)
        })

    # Get vehicle type distribution (using session booking_vehicle or default)
    vehicle_counts = {}
    for apt in Appointment.query.filter(Appointment.status == 'Paid').all():
        vehicle = apt.vehicle_type if apt.vehicle_type else '4w'
        vehicle_counts[vehicle] = vehicle_counts.get(vehicle, 0) + 1

    vehicle_data = {}
    vehicle_names = {'2w': 'Motorcycle', '3w': 'Tricycle', '4w': 'Car', '6w': 'Truck/Bus'}
    for vehicle, count in vehicle_counts.items():
        vehicle_data[vehicle_names.get(vehicle, vehicle)] = count

    return render_template('admin.html',
                           users_count=users_count,
                           appointments_count=appointments_count,
                           booked_count=booked_count,
                           today_booked=today_booked,
                           total_revenue=total_revenue,
                           today_revenue=today_revenue,
                           monthly_revenue=monthly_revenue,
                           pending_payments=pending_payments,
                           recent_appointments=recent_appointments,
                           recent_users=recent_users,
                           daily_revenue=daily_revenue,
                           vehicle_data=vehicle_data,
                           today=today,
                           now=datetime.now())  # ← ADD THIS LINE

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

@app.route('/courses')
def courses():
    """Display available courses"""
    from models import Course
    courses = Course.query.filter_by(is_active=True).all()
    return render_template('courses.html', courses=courses)


@app.route('/api/booking/<reference_number>')
@login_required
def api_booking_details(reference_number):
    """API endpoint to get booking details for modal"""
    from flask import jsonify

    appointment = Appointment.query.filter_by(reference_number=reference_number).first()

    if not appointment:
        return jsonify({'success': False, 'message': 'Booking not found'})

    if appointment.user_id != session['user_id'] and not session.get('is_admin'):
        return jsonify({'success': False, 'message': 'Unauthorized'})

    payment = Payment.query.filter_by(appointment_id=appointment.id).first()

    return jsonify({
        'success': True,
        'booking': {
            'reference_number': appointment.reference_number,
            'full_name': appointment.full_name,
            'email': appointment.email,
            'contact_number': appointment.contact_number,
            'booking_date': appointment.booking_date.isoformat() if appointment.booking_date else None,
            'vehicle_type': appointment.vehicle_type,
            'location': appointment.location,
            'status': appointment.status,
            'payment_amount': payment.amount if payment else 0,
            'payment_method': payment.payment_method if payment else None,
            'transaction_id': payment.transaction_id if payment else 'N/A',
            'payment_date': payment.payment_date.isoformat() if payment and payment.payment_date else None
        }
    })

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

@app.route('/test-logo')
def test_logo():
    from flask import send_from_directory
    import os
    logo_path = os.path.join(app.static_folder, 'images', 'logo.png')
    if os.path.exists(logo_path):
        return f"Logo found at: {logo_path}"
    else:
        return f"Logo NOT found at: {logo_path}. Please check the file location."

# ===== ADD THIS NEW ROUTE =====
@app.route('/logo.png')
def favicon():
    """Serve favicon for browser tab"""
    from flask import send_from_directory
    return send_from_directory(
        os.path.join(app.static_folder, 'images'),
        'logo.png',
        mimetype='image/vnd.microsoft.icon'
    )
# ===== END OF NEW ROUTE =====
@app.route('/test-email')
def test_email():
    from flask_mail import Message
    try:
        msg = Message(
            subject="Test Email from EcoDrive Theory",
            recipients=['ronbell112323@gmail.com'],  # Send to yourself
            body="This is a test email to verify SMTP configuration is working correctly."
        )
        mail.send(msg)
        return "✅ TEST EMAIL SENT SUCCESSFULLY! Check your inbox."
    except Exception as e:
        return f"❌ ERROR: {e}"

# CHANGED: For production VPS
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    # CHANGED: Use 0.0.0.0 to make it publicly accessible
    app.run(host='0.0.0.0', debug=False, port=5000)

// EcoDrive Theory - Main JavaScript

// Initialize tooltips and animations
document.addEventListener('DOMContentLoaded', function() {
    // Auto-hide alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Add smooth scrolling to all links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({ behavior: 'smooth' });
            }
        });
    });

    // Initialize date picker if exists
    const dateInputs = document.querySelectorAll('.date-picker');
    dateInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.type = 'date';
        });
    });

    // Vehicle selection
    const vehicleCards = document.querySelectorAll('.vehicle-card');
    vehicleCards.forEach(card => {
        card.addEventListener('click', function() {
            vehicleCards.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');

            const hiddenInput = document.querySelector('input[name="vehicle_type"]');
            if (hiddenInput) {
                hiddenInput.value = this.dataset.vehicle;
            }
        });
    });

    // Payment method selection
    const paymentOptions = document.querySelectorAll('.payment-option');
    paymentOptions.forEach(option => {
        option.addEventListener('click', function() {
            paymentOptions.forEach(o => o.classList.remove('selected'));
            this.classList.add('selected');

            const hiddenInput = document.querySelector('input[name="payment_method"]');
            if (hiddenInput) {
                hiddenInput.value = this.dataset.method;
            }
        });
    });

    // Schedule selection
    const scheduleCards = document.querySelectorAll('.schedule-card');
    scheduleCards.forEach(card => {
        card.addEventListener('click', function() {
            scheduleCards.forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');

            document.getElementById('preferred_date').value = this.dataset.date;
            document.getElementById('preferred_time').value = this.dataset.time;
        });
    });

    // Form validation
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        });
    });

    // Password strength meter
    const passwordInput = document.querySelector('input[type="password"][name="password"]');
    const strengthMeter = document.querySelector('.password-strength');

    if (passwordInput && strengthMeter) {
        passwordInput.addEventListener('input', function() {
            const strength = calculatePasswordStrength(this.value);
            updateStrengthMeter(strength);
        });
    }

    // Confirm password match
    const confirmInput = document.querySelector('input[name="confirm_password"]');
    if (passwordInput && confirmInput) {
        confirmInput.addEventListener('input', function() {
            if (passwordInput.value !== this.value) {
                this.setCustomValidity('Passwords do not match');
            } else {
                this.setCustomValidity('');
            }
        });
    }
});

// Password strength calculator
function calculatePasswordStrength(password) {
    let strength = 0;

    if (password.length >= 8) strength += 1;
    if (password.match(/[a-z]+/)) strength += 1;
    if (password.match(/[A-Z]+/)) strength += 1;
    if (password.match(/[0-9]+/)) strength += 1;
    if (password.match(/[$@#&!]+/)) strength += 1;

    return strength;
}

// Update strength meter
function updateStrengthMeter(strength) {
    const meter = document.querySelector('.password-strength');
    if (!meter) return;

    const colors = ['#dc3545', '#ffc107', '#ffc107', '#28a745', '#28a745'];
    const texts = ['Very Weak', 'Weak', 'Fair', 'Good', 'Strong'];

    meter.style.width = (strength * 20) + '%';
    meter.style.backgroundColor = colors[strength - 1] || '#dc3545';
    meter.textContent = texts[strength - 1] || 'Very Weak';
}

// Format currency
function formatCurrency(amount) {
    return '₱' + parseFloat(amount).toFixed(2).replace(/\d(?=(\d{3})+\.)/g, '$&,');
}

// Generate reference number
function generateReference() {
    const prefix = 'TDC';
    const year = new Date().getFullYear();
    const random = Math.floor(1000 + Math.random() * 9000);
    return `${prefix}-${year}-${random}`;
}

// Print confirmation
function printConfirmation() {
    window.print();
}

// Toggle mobile menu
function toggleMenu() {
    const navLinks = document.querySelector('.nav-links');
    if (navLinks) {
        navLinks.classList.toggle('show');
    }
}

function selectVehicle(vehicle, amount, element) {
    document.querySelectorAll('.vehicle-card').forEach(card => {
        card.classList.remove('selected');
        card.querySelector('.selected-indicator').style.display = 'none';
    });

    element.classList.add('selected');
    element.querySelector('.selected-indicator').style.display = 'block';

    document.getElementById('selected_vehicle').value = vehicle;
    document.getElementById('selected_amount').value = amount;
    document.getElementById('continueBtn').disabled = false;
}
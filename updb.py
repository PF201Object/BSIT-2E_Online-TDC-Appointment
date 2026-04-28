import threading
import requests
import json

# Your Brevo API key
BREVO_API_KEY = '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'

def send_email_via_brevo(to_email, subject, html_content, sender_name='EcoDrive Theory'):
    """Send email using Brevo API (works over HTTPS - port 443)"""
    def send():
        try:
            print(f"📧 Sending email to {to_email} via Brevo API...")
            
            url = "https://api.brevo.com/v3/smtp/email"
            
            payload = {
                "sender": {
                    "name": sender_name,
                    "email": "ronbell112323@gmail.com"
                },
                "to": [
                    {
                        "email": to_email,
                        "name": "User"
                    }
                ],
                "subject": subject,
                "htmlContent": html_content
            }
            
            headers = {
                "accept": "application/json",
                "api-key": BREVO_API_KEY,
                "content-type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 201, 202]:
                print(f"✅ Brevo email sent successfully to {to_email}")
                result = response.json()
                if 'messageId' in result:
                    print(f"   Message ID: {result['messageId']}")
            else:
                print(f"❌ Brevo API error: {response.status_code}")
                print(f"   Response: {response.text}")
        except Exception as e:
            print(f"❌ Brevo error sending to {to_email}: {e}")
    
    thread = threading.Thread(target=send)
    thread.start()
    return True

def create_verification_email(code):
    """Create HTML email for verification"""
    return f"""
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
                <p>Thank you for registering with EcoDrive Theory! Please use the verification code below:</p>
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
"""
CartGuard AI - Notification Service
Handles email (SendGrid & SMTP), SMS/WhatsApp (Twilio) notifications with full error diagnostics.
Respects TRAI/DND and consent rules.
"""
import os
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional
import httpx


def _load_env_file():
    """Ensure .env file variables are loaded into os.environ."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    env_path = os.path.join(base_dir, ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'").strip('"')
                    if k not in os.environ or not os.environ[k]:
                        os.environ[k] = v

_load_env_file()


class NotificationService:
    def __init__(self):
        self.reload_credentials()

    def reload_credentials(self):
        _load_env_file()
        self.sendgrid_key = os.getenv("SENDGRID_API_KEY", "").strip()
        self.twilio_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from = os.getenv("TWILIO_FROM_NUMBER", "").strip()
        self.from_email = os.getenv("FROM_EMAIL", "noreply@cartguard.ai").strip()

        # Optional SMTP fallback credentials
        self.smtp_host = os.getenv("SMTP_HOST", "").strip()
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "").strip()
        self.smtp_password = os.getenv("SMTP_PASSWORD", "").strip()

    async def send_notification(self, session_data: Dict[str, Any], action: Dict[str, Any]):
        """Send notification based on action channel."""
        self.reload_credentials()
        channel = action.get("channel", "IN_APP")
        message = action.get("message", "")
        
        if not message or channel == "DO_NOTHING" or channel == "IN_APP":
            return {"status": "skipped", "reason": "in-app or no action"}

        # Consent check
        if not self._check_consent(session_data, channel):
            return {"status": "skipped", "reason": "consent not given or DND registered"}

        if channel == "EMAIL":
            return await self.send_email(
                to_email=session_data.get("user_email", ""),
                subject="Your cart is waiting! 🛒",
                message=message,
                discount=action.get("discount_amount", 0),
            )
        elif channel in ["SMS", "WHATSAPP"]:
            return await self.send_sms(
                to_number=session_data.get("user_phone", ""),
                message=message,
                channel=channel,
            )
        
        return {"status": "no_action"}

    def _check_consent(self, session_data: Dict, channel: str) -> bool:
        """TRAI/DND compliance check."""
        if session_data.get("is_dnd_registered", False) and channel == "SMS":
            return False
        if channel == "EMAIL" and not session_data.get("email_opt_in", True):
            return False
        if channel == "WHATSAPP" and not session_data.get("whatsapp_opt_in", False):
            return False
        return True

    async def send_email(
        self,
        to_email: str,
        subject: str,
        message: str,
        discount: float = 0,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sendgrid_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send cart recovery email via SMTP or SendGrid.
        """
        self.reload_credentials()
        
        sg_key = sendgrid_key or self.sendgrid_key
        host = smtp_host or self.smtp_host
        port = smtp_port or self.smtp_port
        user = smtp_user or self.smtp_user
        pwd = smtp_password or self.smtp_password

        discount_html = ""
        if discount > 0:
            discount_html = f'<p style="color:#e53e3e;font-weight:bold;font-size:18px;">🎁 Save ₹{discount:.0f} with promo code: <strong>SAVE{int(discount)}</strong></p>'

        html_content = f"""
        <html><body style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:20px;">
        <div style="background:linear-gradient(135deg,#0f172a,#1e293b);padding:30px;border-radius:10px;text-align:center;color:white;">
            <h1>🛒 CartGuard AI — Cart Recovery</h1>
        </div>
        <div style="padding:20px;background:#f9f9f9;border-radius:0 0 10px 10px;border:1px solid #e2e8f0;">
            <p style="font-size:16px;color:#334155;line-height:1.6;">{message}</p>
            {discount_html}
            <div style="text-align:center;margin-top:25px;">
                <a href="#" style="background:#0f172a;color:white;padding:14px 28px;border-radius:8px;text-decoration:none;display:inline-block;font-weight:bold;">
                    Complete Your Purchase Now →
                </a>
            </div>
        </div>
        <p style="color:#94a3b8;font-size:12px;text-align:center;margin-top:20px;">
            CartGuard AI Automated Remediation Engine
        </p>
        </body></html>
        """

        # 1. Try SMTP if credentials exist
        if host and user and pwd:
            try:
                msg = MIMEMultipart("alternative")
                msg["Subject"] = subject
                msg["From"] = user
                msg["To"] = to_email
                msg.attach(MIMEText(html_content, "html"))

                def _send_smtp():
                    if port == 465:
                        with smtplib.SMTP_SSL(host, port, timeout=10) as server:
                            server.login(user, pwd)
                            server.sendmail(user, [to_email], msg.as_string())
                    else:
                        with smtplib.SMTP(host, port, timeout=10) as server:
                            server.starttls()
                            server.login(user, pwd)
                            server.sendmail(user, [to_email], msg.as_string())

                await asyncio.to_thread(_send_smtp)
                print(f"[SMTP EMAIL SUCCESS] Sent to {to_email}")
                return {"status": "sent", "channel": "email", "provider": "smtp", "recipient": to_email}
            except Exception as e:
                print(f"[SMTP EMAIL ERROR] {e}")
                return {"status": "error", "provider": "smtp", "error": str(e)}

        # 2. Try SendGrid API if key exists and is valid
        if sg_key and not sg_key.startswith("your_"):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://api.sendgrid.com/v3/mail/send",
                        headers={
                            "Authorization": f"Bearer {sg_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "personalizations": [{"to": [{"email": to_email}]}],
                            "from": {"email": self.from_email, "name": "CartGuard AI"},
                            "subject": subject,
                            "content": [{"type": "text/html", "value": html_content}],
                        },
                        timeout=10.0,
                    )
                    if response.status_code in [200, 201, 202]:
                        return {"status": "sent", "channel": "email", "provider": "sendgrid", "status_code": response.status_code}
                    else:
                        return {"status": "error", "provider": "sendgrid", "status_code": response.status_code, "error": response.text}
            except Exception as e:
                return {"status": "error", "provider": "sendgrid", "error": str(e)}

        # 3. Fallback mock response with setup diagnostic guidance
        safe_subj = subject.encode('ascii', 'replace').decode('ascii')
        safe_msg = message.encode('ascii', 'replace').decode('ascii')
        print(f"[EMAIL MOCK LOG] To: {to_email} | Subject: {safe_subj} | Message: {safe_msg}")
        return {
            "status": "mock_sent",
            "channel": "email",
            "to_email": to_email,
            "message": "Mock email logged. To send live emails, set valid SENDGRID_API_KEY or SMTP_USER/SMTP_PASSWORD in .env file."
        }

    async def send_sms(
        self,
        to_number: str,
        message: str,
        channel: str = "SMS",
        sid: Optional[str] = None,
        token: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send SMS/WhatsApp via Twilio with full API error reporting.
        """
        self.reload_credentials()

        tw_sid = sid or self.twilio_sid
        tw_token = token or self.twilio_token
        tw_from = from_number or self.twilio_from

        if not tw_sid or not tw_token or not to_number or not tw_from or tw_from == "+1234567890":
            print(f"[{channel} MOCK] To: {to_number} | Message: {message}")
            return {
                "status": "mock_sent",
                "channel": channel.lower(),
                "to_number": to_number,
                "reason": "Missing or placeholder Twilio credentials. Configure TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_FROM_NUMBER in .env"
            }

        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{tw_sid}/Messages.json"
            sender = f"whatsapp:{tw_from}" if channel == "WHATSAPP" and not tw_from.startswith("whatsapp:") else tw_from
            recipient = f"whatsapp:{to_number}" if channel == "WHATSAPP" and not to_number.startswith("whatsapp:") else to_number

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    auth=(tw_sid, tw_token),
                    data={"From": sender, "To": recipient, "Body": message},
                    timeout=10.0,
                )
                data = response.json()
                
                if response.status_code in [200, 201]:
                    return {
                        "status": "sent",
                        "channel": channel.lower(),
                        "sid": data.get("sid"),
                        "message_status": data.get("status"),
                        "to": data.get("to")
                    }
                else:
                    print(f"[TWILIO ERROR {response.status_code}] Code: {data.get('code')} | Message: {data.get('message')}")
                    return {
                        "status": "twilio_error",
                        "http_status": response.status_code,
                        "code": data.get("code"),
                        "message": data.get("message"),
                        "more_info": data.get("more_info"),
                        "channel": channel.lower()
                    }
        except Exception as e:
            return {"status": "error", "error": str(e), "channel": channel.lower()}


notification_service = NotificationService()

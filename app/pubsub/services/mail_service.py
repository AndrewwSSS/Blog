import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings
from app.schemas.user import UserInDB

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, user: UserInDB) -> None:
        self.user = user
        self.smtp_server = smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT
        )
        self.smtp_server.set_debuglevel(True)
        self.smtp_server.starttls()
        self.smtp_server.login(settings.SMTP_USER, settings.SMTP_USER_PASSWORD)

    async def _send_mail(self, message: MIMEMultipart) -> dict:
        return self.smtp_server.sendmail(
            settings.SMTP_USER,
            self.user.email,
            message.as_string()
        )

    async def send_welcome_email(self):
        message = self._generate_welcome_email()

        response = await self._send_mail(message)

        return self._handle_response(response)

    async def send_verification_email(self, verification_url: str) -> bool:
        message = self._generate_verification_email(
            verification_url
        )
        response = await self._send_mail(message)
        return self._handle_response(response)

    def _handle_response(self, response: dict) -> bool:
        if response:
            logger.error(f"Failed to send email to {self.user.email} "
                         f"Response {response}")
            return False
        return True

    def _generate_verification_email(self, verification_url: str) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["From"] = settings.SMTP_USER
        message["To"] = self.user.email
        message["Subject"] = "Welcome to Blog service"

        part = MIMEText(
            self._generate_verification_email_html(verification_url),
            "html"
        )

        message.attach(part)
        return message

    def _generate_welcome_email(self) -> MIMEMultipart:
        message = MIMEMultipart("alternative")
        message["From"] = settings.SMTP_USER
        message["To"] = self.user.email
        message["Subject"] = "Account verification"

        part = MIMEText(
            self._generate_welcome_email_html(),
            "html"
        )

        message.attach(part)
        return message

    def _generate_verification_email_html(self, verification_url) -> str:
        return f"""
            <html>
                <body>
                    <p>Hello {self.user.username},</p>
                    <p>Please verify your email address by clicking the link below:</p>
                    <a href="{verification_url}">Verify Email</a>
                </body>
            </html>
        """

    def _generate_welcome_email_html(self) -> str:
        return f"""
            <html>
            <body>
                <h1>Welcome, {self.user.username}!</h1>
                <p>We're thrilled to have you join our Blog Service. Here's to creating and sharing amazing content together!</p>
                <p>If you have any questions or need assistance, feel free to reach out to our support team.</p>
                <br>
                <p>Happy blogging,</p>
                <p>The Blog Service Team</p>
            </body>
            </html>
        """

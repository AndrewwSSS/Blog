import smtplib

import pytest
from tenacity import wait_none

from app.pubsub.services import mail_service
from app.pubsub.services.mail_service import EmailService, is_transient_smtp_error


class FlakySMTP:
    """Fails with the queued errors one connection at a time, then succeeds."""

    errors: list[Exception] = []
    connections = 0

    def __init__(self, host, port) -> None:
        FlakySMTP.connections += 1

    def __enter__(self) -> "FlakySMTP":
        return self

    def __exit__(self, *exc) -> None:
        pass

    def starttls(self) -> None:
        if FlakySMTP.errors:
            raise FlakySMTP.errors.pop(0)

    def login(self, user, password) -> None:
        pass

    def sendmail(self, sender, recipient, body) -> dict:
        return {}


@pytest.fixture
def flaky_smtp(monkeypatch) -> type[FlakySMTP]:
    FlakySMTP.errors = []
    FlakySMTP.connections = 0
    monkeypatch.setattr(mail_service.smtplib, "SMTP", FlakySMTP)
    monkeypatch.setattr(EmailService, "retry_wait", wait_none())
    return FlakySMTP


async def test_transient_failures_are_retried(flaky_smtp, test_user):
    flaky_smtp.errors = [
        smtplib.SMTPServerDisconnected("dropped"),
        smtplib.SMTPResponseException(421, b"try later"),
    ]

    assert await EmailService(test_user).send_welcome_email() is True
    assert flaky_smtp.connections == 3


async def test_permanent_failure_is_not_retried(flaky_smtp, test_user):
    flaky_smtp.errors = [smtplib.SMTPAuthenticationError(535, b"bad credentials")]

    with pytest.raises(smtplib.SMTPAuthenticationError):
        await EmailService(test_user).send_welcome_email()
    assert flaky_smtp.connections == 1


async def test_gives_up_after_max_attempts(flaky_smtp, test_user):
    flaky_smtp.errors = [ConnectionRefusedError()] * 5

    with pytest.raises(ConnectionRefusedError):
        await EmailService(test_user).send_verification_email("http://x")
    assert flaky_smtp.connections == EmailService.SEND_ATTEMPTS


@pytest.mark.parametrize(
    ("error", "transient"),
    [
        (smtplib.SMTPConnectError(421, b"busy"), True),
        (smtplib.SMTPServerDisconnected(), True),
        (smtplib.SMTPResponseException(451, b"local error"), True),
        (smtplib.SMTPResponseException(550, b"no such mailbox"), False),
        (smtplib.SMTPRecipientsRefused({}), False),
        (TimeoutError(), True),
        (ValueError(), False),
    ],
)
def test_transient_error_classification(error, transient):
    assert is_transient_smtp_error(error) is transient

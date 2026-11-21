import logging

import pytest

import app.main  # noqa: F401  (installs the access log filter)
from app.core.log_filters import mask_verification_token


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/api/v1/users/verification/abc.DEF-123_x", "/api/v1/users/verification/***"),
        ("/api/v1/users/verification/abc?next=1", "/api/v1/users/verification/***?next=1"),
        ("/api/v1/users/verification/resend", "/api/v1/users/verification/resend"),
        ("/api/v1/users/verification/resendXYZ", "/api/v1/users/verification/***"),
        ("/api/v1/posts/", "/api/v1/posts/"),
    ],
)
def test_masks_only_verification_tokens(path, expected):
    assert mask_verification_token(path) == expected


def test_uvicorn_access_log_does_not_contain_the_token(caplog):
    token = "secret.verification-token"

    with caplog.at_level(logging.INFO, logger="uvicorn.access"):
        logging.getLogger("uvicorn.access").info(
            '%s - "%s %s HTTP/%s" %d',
            "203.0.113.7:5000",
            "GET",
            f"/api/v1/users/verification/{token}",
            "1.1",
            200,
        )

    assert token not in caplog.text
    assert '"GET /api/v1/users/verification/*** HTTP/1.1" 200' in caplog.text

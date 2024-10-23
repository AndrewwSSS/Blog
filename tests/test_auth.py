import pytest

from tests.conftest import client, async_session_maker


def test_registration():
    create_user = {
        "username": "test_user_auth",
        "email": "<EMAIL>@gmail.com",
        "password": "<PASSW3OR43D>",
    }
    response = client.post("/api/v1/users/register", json=create_user)
    response_data = response.json()
    assert response.status_code == 201
    assert response_data["username"] == create_user["username"]
    assert response_data["email"] == create_user["email"]


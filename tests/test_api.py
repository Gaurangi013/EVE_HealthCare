import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

fd, temp_db_path = tempfile.mkstemp(suffix=".db")
os.close(fd)
Path(temp_db_path).unlink(missing_ok=True)
os.environ["EVE_DATABASE_URL"] = f"sqlite:///{temp_db_path}"

from app.main import app

client = TestClient(app)


def test_signup_and_login_and_me():
    response = client.post(
        "/auth/signup",
        json={"email": "alice@example.com", "password": "securepass"},
    )
    assert response.status_code == 201, response.text

    login_response = client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "securepass"},
    )
    assert login_response.status_code == 200, login_response.text
    token = login_response.json()["access_token"]

    me_response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "alice@example.com"


def test_create_centre_and_tests_and_booking():
    signup_response = client.post(
        "/auth/signup",
        json={"email": "bob@example.com", "password": "securepass"},
    )
    assert signup_response.status_code == 201

    token = client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "securepass"},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    centre_response = client.post(
        "/diagnostic-centres",
        json={"name": "City Health Lab", "location": "Bristol"},
        headers=headers,
    )
    assert centre_response.status_code == 201
    centre_id = centre_response.json()["id"]

    test_response = client.post(
        f"/diagnostic-centres/{centre_id}/tests",
        json={"name": "Blood Test", "price": 99.99},
        headers=headers,
    )
    assert test_response.status_code == 201
    test_id = test_response.json()["id"]

    booking_response = client.post(
        "/bookings",
        json={
            "patient_name": "Bob Smith",
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": "2026-10-05T12:00:00",
        },
        headers=headers,
    )
    assert booking_response.status_code == 201, booking_response.text
    booking_id = booking_response.json()["id"]
    assert booking_response.json()["status"] == "PENDING"

    webhook_response = client.post(
        "/payments",
        json={
            "booking_id": booking_id,
            "provider_event_id": "evt-123",
            "status": "SUCCESS",
        },
        headers=headers,
    )
    assert webhook_response.status_code == 200
    assert webhook_response.json()["payment_status"] == "SUCCESS"

    updated_booking = client.get("/bookings", headers=headers)
    assert updated_booking.status_code == 200
    assert any(item["id"] == booking_id and item["status"] == "CONFIRMED" for item in updated_booking.json())

    duplicate = client.post(
        "/payments/webhook",
        json={
            "booking_id": booking_id,
            "provider_event_id": "evt-123",
            "status": "SUCCESS",
        },
        headers=headers,
    )
    assert duplicate.status_code == 200
    assert duplicate.json()["message"] == "Duplicate webhook ignored"

    cancel_response = client.post(f"/bookings/{booking_id}/cancel", headers=headers)
    assert cancel_response.status_code == 200
    assert cancel_response.json()["status"] == "CANCELLED"

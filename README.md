# EVE Healthcare Backend

A FastAPI service for managing diagnostic centres, appointments, and payment webhook processing.

## Features

- JWT-based authentication for patients
- Diagnostic centre catalogue and test listings
- Booking creation and retrieval
- Simulated payment provider webhook flow with idempotency protection
- SQLite persistence with SQLAlchemy

## Local setup

1. Create a virtual environment:

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the API:

```bash
uvicorn app.main:app --reload
```

4. Open docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8002/)

## API overview

- `POST /auth/signup` – create an account
- `POST /auth/login` – log in and receive a JWT
- `GET /auth/me` – fetch the authenticated user
- `GET /diagnostic-centres` – list centres and their tests
- `POST /diagnostic-centres` – create a centre
- `POST /diagnostic-centres/{centre_id}/tests` – add a test to a centre
- `POST /bookings` – create a booking for a patient
- `GET /bookings` – list bookings for the current user
- `POST /bookings/{booking_id}/cancel` – cancel a booking for the patient
- `POST /payments` and `POST /payments/webhook` – process payment events idempotently

### Example request flow

```bash
curl -X POST http://127.0.0.1:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@example.com","password":"securepass"}'

curl -X POST http://127.0.0.1:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"patient@example.com","password":"securepass"}'

curl -X GET http://127.0.0.1:8000/diagnostic-centres
curl -X POST http://127.0.0.1:8000/bookings \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"patient_name":"Jane Doe","centre_id":1,"test_id":1,"appointment_datetime":"2026-10-10T09:30:00"}'

curl -X POST http://127.0.0.1:8000/payments \
  -H "Content-Type: application/json" \
  -d '{"booking_id":1,"provider_event_id":"evt-101","status":"SUCCESS"}'
```

## Database design

The project uses SQLite and SQLAlchemy with these core entities:

- `User`: account credentials and identity
- `DiagnosticCentre`: facility name and location
- `DiagnosticTest`: test offered by a centre with a price
- `Booking`: appointment reservation linked to a user, centre and test
- `PaymentWebhookEvent`: avoids duplicate webhook processing by recording provider event IDs

## Important assumptions

- The backend stores data in a local SQLite file named `eve_healthcare.db` by default.
- Payment simulation is intentional and deterministic; the webhook either returns `SUCCESS` or `FAILED`.
- Duplicate webhook events do not create duplicate payments or mutate booking state repeatedly.

## What to improve next

- Add admin-only routes for centre management
- Move to a stricter role model
- Add background jobs or audit logs
- Replace SQLite with Postgres for production workloads

- Author

Gaurangi Gaur
B.Tech Computer Science Engineering

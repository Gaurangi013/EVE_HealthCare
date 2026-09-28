from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth import authenticate_user, create_access_token, get_current_user, hash_password
from app.database import get_db, init_db
from app.models import Booking, DiagnosticCentre, DiagnosticTest, PaymentWebhookEvent, User
from app.schemas import (
    BookingCreate,
    BookingOut,
    DiagnosticCentreCreate,
    DiagnosticCentreOut,
    DiagnosticTestCreate,
    DiagnosticTestOut,
    PaymentWebhookRequest,
    PaymentWebhookResponse,
    Token,
    UserCreate,
    UserOut,
)

app = FastAPI(title="EVE Healthcare")

BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

init_db()


@app.on_event("startup")
def startup_event() -> None:
    init_db()


def process_payment_event(db: Session, booking_id: int, provider_event_id: str, status: str) -> PaymentWebhookResponse:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    existing = (
        db.query(PaymentWebhookEvent)
        .filter(PaymentWebhookEvent.booking_id == booking_id)
        .filter(PaymentWebhookEvent.provider_event_id == provider_event_id)
        .first()
    )
    if existing:
        return PaymentWebhookResponse(
            booking_id=booking_id,
            payment_status=existing.status,
            status=existing.status,
            message="Duplicate webhook ignored",
        )

    normalized = status.upper()
    booking_statuses = {"SUCCESS": "CONFIRMED", "FAILED": "FAILED"}
    if normalized not in booking_statuses:
        raise HTTPException(status_code=400, detail="Unsupported payment status")

    booking.status = booking_statuses[normalized]
    event = PaymentWebhookEvent(
        booking_id=booking_id,
        provider_event_id=provider_event_id,
        status=normalized,
    )
    db.add(event)
    db.commit()
    db.refresh(booking)

    return PaymentWebhookResponse(
        booking_id=booking_id,
        payment_status=normalized,
        status=booking.status,
        message="Payment webhook processed successfully",
    )


@app.post("/auth/signup", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(user: UserCreate, db: Session = Depends(get_db)) -> User:
    existing = db.query(User).filter(User.email == user.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    role = user.role.lower() if user.role else "patient"
    if role not in {"patient", "admin"}:
        raise HTTPException(status_code=400, detail="Unsupported user role")

    db_user = User(email=user.email, password_hash=hash_password(user.password), role=role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


@app.post("/auth/login", response_model=Token)
def login(user: UserCreate, db: Session = Depends(get_db)) -> dict[str, str]:
    auth_user = authenticate_user(db, user.email, user.password)
    if not auth_user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(auth_user.email)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@app.get("/diagnostic-centres", response_model=list[DiagnosticCentreOut])
def list_centres(db: Session = Depends(get_db), q: str | None = Query(default=None)) -> list[DiagnosticCentre]:
    query = db.query(DiagnosticCentre)
    if q:
        query = query.filter(DiagnosticCentre.name.ilike(f"%{q}%"))
    return query.order_by(DiagnosticCentre.name).all()


@app.post("/diagnostic-centres", response_model=DiagnosticCentreOut, status_code=status.HTTP_201_CREATED)
def create_centre(centre: DiagnosticCentreCreate, db: Session = Depends(get_db)) -> DiagnosticCentre:
    db_centre = DiagnosticCentre(name=centre.name, location=centre.location)
    db.add(db_centre)
    db.commit()
    db.refresh(db_centre)
    return db_centre


@app.post("/diagnostic-centres/{centre_id}/tests", response_model=DiagnosticTestOut, status_code=status.HTTP_201_CREATED)
def create_test_for_centre(
    centre_id: int,
    test: DiagnosticTestCreate,
    db: Session = Depends(get_db),
) -> DiagnosticTest:
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    db_test = DiagnosticTest(name=test.name, price=test.price, centre_id=centre_id)
    db.add(db_test)
    db.commit()
    db.refresh(db_test)
    return db_test


@app.get("/diagnostic-centres/{centre_id}/tests", response_model=list[DiagnosticTestOut])
def get_tests_for_centre(centre_id: int, db: Session = Depends(get_db)) -> list[DiagnosticTest]:
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")
    return db.query(DiagnosticTest).filter(DiagnosticTest.centre_id == centre_id).all()


@app.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == booking.centre_id).first()
    if not centre:
        raise HTTPException(status_code=404, detail="Diagnostic centre not found")

    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == booking.test_id).first()
    if not test or test.centre_id != booking.centre_id:
        raise HTTPException(status_code=404, detail="Diagnostic test not found for this centre")

    db_booking = Booking(
        patient_name=booking.patient_name,
        user_id=current_user.id,
        centre_id=booking.centre_id,
        test_id=booking.test_id,
        appointment_datetime=booking.appointment_datetime,
        amount=float(test.price),
        status="PENDING",
    )
    db.add(db_booking)
    db.commit()
    db.refresh(db_booking)
    return db_booking


@app.get("/bookings", response_model=list[BookingOut])
def list_bookings(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)) -> list[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.id)
        .order_by(Booking.appointment_datetime.desc())
        .all()
    )


@app.post("/payments", response_model=PaymentWebhookResponse)
@app.post("/payments/webhook", response_model=PaymentWebhookResponse)
def payment_webhook(
    payload: PaymentWebhookRequest,
    db: Session = Depends(get_db),
) -> PaymentWebhookResponse:
    return process_payment_event(
        db,
        payload.booking_id,
        payload.provider_event_id,
        payload.status,
    )


@app.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .filter(Booking.user_id == current_user.id)
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    booking.status = "CANCELLED"
    db.commit()
    db.refresh(booking)
    return booking


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

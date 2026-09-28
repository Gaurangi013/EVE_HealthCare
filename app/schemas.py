from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = "patient"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DiagnosticCentreCreate(BaseModel):
    name: str
    location: str


class DiagnosticCentreOut(DiagnosticCentreCreate):
    id: int

    model_config = {"from_attributes": True}


class DiagnosticTestCreate(BaseModel):
    name: str
    price: float


class DiagnosticTestOut(DiagnosticTestCreate):
    id: int
    centre_id: int

    model_config = {"from_attributes": True}


class BookingCreate(BaseModel):
    patient_name: str
    centre_id: int
    test_id: int
    appointment_datetime: datetime


class BookingOut(BaseModel):
    id: int
    patient_name: str
    centre_id: int
    test_id: int
    appointment_datetime: datetime
    amount: float
    status: str

    model_config = {"from_attributes": True}


class PaymentWebhookRequest(BaseModel):
    booking_id: int
    provider_event_id: str
    status: str


class PaymentWebhookResponse(BaseModel):
    booking_id: int
    payment_status: str
    status: str | None = None
    message: str

    model_config = {"populate_by_name": True}

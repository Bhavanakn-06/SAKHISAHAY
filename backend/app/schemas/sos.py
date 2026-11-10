"""Pydantic schemas for Emergency SOS Assistance."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class GeoLocation(BaseModel):
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    accuracy: float | None = Field(None, ge=0.0)


class SOSTriggerRequest(BaseModel):
    latitude: float = Field(default=12.9716, ge=-90.0, le=90.0)
    longitude: float = Field(default=77.5946, ge=-180.0, le=180.0)
    accuracy: float | None = Field(None, ge=0.0)
    message: str | None = Field(
        default="I need urgent assistance. Please contact me immediately. My location has been sent.",
        max_length=500,
    )
    recipient_email: str | None = None

    @model_validator(mode="before")
    @classmethod
    def normalize_input(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # If coordinates object is supplied by frontend
            coords = data.get("coordinates")
            if isinstance(coords, dict):
                if "latitude" in coords and coords["latitude"] is not None:
                    data["latitude"] = coords["latitude"]
                if "longitude" in coords and coords["longitude"] is not None:
                    data["longitude"] = coords["longitude"]
                if "accuracy" in coords and coords["accuracy"] is not None:
                    data["accuracy"] = coords["accuracy"]

            # If notes is provided instead of message
            if not data.get("message") and data.get("notes"):
                data["message"] = data["notes"]
        return data


class ContactAlertSnapshot(BaseModel):
    name: str
    phone: str
    relationship: str
    dispatch_status: str = "SENT"


class SOSResponse(BaseModel):
    id: str
    user_id: str
    status: Literal["ACTIVE", "RESOLVED", "CANCELLED"] = "ACTIVE"
    location: GeoLocation
    message: str | None = None
    contacts_notified: list[ContactAlertSnapshot] = []
    triggered_at: datetime
    resolved_at: datetime | None = None
    resolution_note: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SOSResolveRequest(BaseModel):
    resolution_note: str | None = Field(
        default="Resolved safely by user", max_length=500
    )


class ActiveSOSStatus(BaseModel):
    has_active_sos: bool
    sos: SOSResponse | None = None

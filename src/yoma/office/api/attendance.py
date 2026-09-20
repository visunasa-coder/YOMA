from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.attendance import AttendanceService


router = APIRouter(
    prefix="/office/attendance",
    tags=["YOMA Office Attendance"],
)

service = AttendanceService()


class AttendanceEventRequest(BaseModel):
    employee_id: str
    event_type: str
    timestamp: str
    source: str
    device_id: str | None = None
    confidence: float | None = None
    metadata: dict | None = None


@router.post("/normalize")
def normalize_attendance_event(
    request: AttendanceEventRequest,
):
    try:
        event = service.normalize_event(request.model_dump())
        return {
            "employee_id": event.employee_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "source": event.source,
            "device_id": event.device_id,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

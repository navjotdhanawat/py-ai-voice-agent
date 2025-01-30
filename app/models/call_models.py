from enum import Enum
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class CallState(str, Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    FAILED = "failed"
    USER_BUSY = "user-busy"

class CallRecord(BaseModel):
    call_uuid: str
    from_number: str
    to_number: str
    direction: str  # inbound or outbound
    state: CallState
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    s3_recording_path: Optional[str] = None
    error_message: Optional[str] = None

    class Config:
        use_enum_values = True
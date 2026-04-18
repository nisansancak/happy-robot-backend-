from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Mode(str, Enum):
    b2c = "small_business"
    b2b = "enterprise"

class CallEvent(BaseModel):
    call_id: str
    phone_number: str
    transcript: str
    language: str = "en"
    voice_gender: str = "female"   # a/b test signal
    mode: Mode = Mode.b2c

class Lead(BaseModel):
    caller_id: str
    phone_number: str
    name: Optional[str] = None
    company: Optional[str] = None
    meeting_time: Optional[str] = None
    lead_score: Optional[int] = None  # 1-5
    call_summary: Optional[str] = None

class ScoreResult(BaseModel):
    score: int         # 1-5
    reasoning: str
    sms_triggered: bool

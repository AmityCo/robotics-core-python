"""
Shared models for the robotics core system
"""
from pydantic import BaseModel
from typing import List, Optional
from enum import Enum


class SSEStatus(str, Enum):
    """
    Enumeration of status values for SSE status messages in the answer pipeline
    """
    STARTING = "starting"
    VALIDATING = "validating"
    SEARCHING_KM = "searching_km"
    GENERATING_ANSWER = "generating_answer"
    COMPLETE = "complete"
    ERROR = "error"


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
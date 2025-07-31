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
    STARTING = "START"
    VALIDATING = "VALIDATOR_START"
    SEARCHING_KM = "SEARCH_START"
    GENERATING_ANSWER = "GENERATOR_START"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
"""
GSM Call Router POC Application

A simple FastAPI application for handling GSM calls with Asterisk integration.
"""

__version__ = "1.0.0"

from .models import CallEvent, CallState, CallType
from .asterisk_manager import asterisk_manager

__all__ = [
    "CallEvent",
    "CallState", 
    "CallType",
    "asterisk_manager"
] 
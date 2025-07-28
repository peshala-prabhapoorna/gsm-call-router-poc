import json
from enum import Enum
from typing import Dict, List, Optional
from datetime import datetime

class CallState(Enum):
    RINGING = "ringing"
    ANSWERED = "answered"
    HANGUP = "hangup"

class CallType(Enum):
    INCOMING_GSM = "incoming_gsm"
    INTERNAL = "internal"
    SIP_TRUNK = "sip_trunk"

class CallEvent:
    def __init__(self, event_type: str, channel: str, caller_id: str = "", 
                 extension: str = "", unique_id: str = "", timestamp: str = "",
                 call_state: CallState = None, call_type: CallType = None):
        self.event_type = event_type
        self.channel = channel
        self.caller_id = caller_id
        self.extension = extension
        self.unique_id = unique_id
        self.timestamp = timestamp
        self.call_state = call_state
        self.call_type = call_type
    
    def to_dict(self):
        return {
            "event_type": self.event_type,
            "channel": self.channel,
            "caller_id": self.caller_id,
            "extension": self.extension,
            "unique_id": self.unique_id,
            "timestamp": self.timestamp,
            "call_state": self.call_state.value if self.call_state else None,
            "call_type": self.call_type.value if self.call_type else None
        } 
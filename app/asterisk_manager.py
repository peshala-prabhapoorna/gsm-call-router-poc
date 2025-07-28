import asyncio
import json
import logging
from typing import Dict, List, Optional
from asterisk.ami import AMIClient, SimpleAction
from fastapi import WebSocket

from .models import CallEvent, CallState, CallType

logger = logging.getLogger(__name__)

class AsteriskManager:
    def __init__(self, host: str = "localhost", port: int = 5038, 
                 username: str = "admin", password: str = "admin"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client: Optional[AMIClient] = None
        self.connected = False
        self.websocket_clients: List[WebSocket] = []
        self.active_calls: Dict[str, CallEvent] = {}
        
    async def connect(self) -> bool:
        """Connect to Asterisk AMI"""
        try:
            self.client = AMIClient(self.host, self.port)
            self.client.login(self.username, self.password)
            self.connected = True
            logger.info(f"Connected to Asterisk AMI at {self.host}:{self.port}")
            
            # Set up event listeners
            self.client.add_event_listener(self._handle_ami_event)
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Asterisk AMI: {e}")
            self.connected = False
            return False
    
    def disconnect(self):
        """Disconnect from Asterisk AMI"""
        if self.client:
            self.client.logoff()
            self.connected = False
            logger.info("Disconnected from Asterisk AMI")
    
    def _handle_ami_event(self, event):
        """Handle incoming AMI events"""
        try:
            event_type = event.get('Event', '')
            channel = event.get('Channel', '')
            caller_id = event.get('CallerIDNum', '')
            extension = event.get('Extension', '')
            unique_id = event.get('Uniqueid', '')
            
            # Determine call type
            call_type = self._determine_call_type(channel, event.get('Context', ''))
            
            # Determine call state
            call_state = self._determine_call_state(event_type, event.get('ChannelState', ''))
            
            call_event = CallEvent(
                event_type=event_type,
                channel=channel,
                caller_id=caller_id,
                extension=extension,
                unique_id=unique_id,
                timestamp=event.get('Timestamp', ''),
                call_state=call_state,
                call_type=call_type
            )
            
            # Handle specific call events
            if event_type == 'Newchannel':
                self.active_calls[unique_id] = call_event
                logger.info(f"New {call_type.value} call: {caller_id} -> {extension}")
                
                # Handle GSM call routing
                if call_type == CallType.INCOMING_GSM:
                    asyncio.create_task(self._handle_incoming_gsm_call(call_event))
                    
            elif event_type == 'Newstate':
                if event.get('ChannelState') == '6':  # Up
                    logger.info(f"Call answered: {channel}")
                    if unique_id in self.active_calls:
                        self.active_calls[unique_id].call_state = CallState.ANSWERED
                    
            elif event_type == 'Hangup':
                if unique_id in self.active_calls:
                    del self.active_calls[unique_id]
                logger.info(f"Call ended: {channel}")
                
            # Broadcast event to all WebSocket clients
            asyncio.create_task(self._broadcast_event(call_event))
            
        except Exception as e:
            logger.error(f"Error handling AMI event: {e}")
    
    def _determine_call_type(self, channel: str, context: str) -> CallType:
        """Determine the type of call"""
        if 'gsm' in channel.lower() or context == 'from-gsm':
            return CallType.INCOMING_GSM
        elif context == 'from-bevatel':
            return CallType.SIP_TRUNK
        elif context == 'from-internal':
            return CallType.INTERNAL
        else:
            return CallType.INCOMING_GSM  # Default to GSM
    
    def _determine_call_state(self, event_type: str, channel_state: str) -> CallState:
        """Determine the call state"""
        if event_type == 'Newchannel':
            return CallState.RINGING
        elif event_type == 'Newstate' and channel_state == '6':
            return CallState.ANSWERED
        elif event_type == 'Hangup':
            return CallState.HANGUP
        return CallState.RINGING
    
    async def _handle_incoming_gsm_call(self, call_event: CallEvent):
        """Handle incoming GSM call - simple routing to extension 1000"""
        try:
            logger.info(f"Routing GSM call from {call_event.caller_id} to extension 1000")
            await self._route_call(call_event.channel, "1000")
        except Exception as e:
            logger.error(f"Error handling incoming GSM call: {e}")
    
    async def _route_call(self, channel: str, destination: str):
        """Route a call to the specified destination"""
        if not self.connected or not self.client:
            logger.error("Not connected to Asterisk AMI")
            return False
            
        try:
            action = SimpleAction(
                'Redirect',
                Channel=channel,
                Context='from-internal',
                Exten=destination,
                Priority=1
            )
            
            response = self.client.send_action(action)
            logger.info(f"Routed call {channel} to {destination}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to route call: {e}")
            return False
    
    async def _broadcast_event(self, event: CallEvent):
        """Broadcast call event to all connected WebSocket clients"""
        if not self.websocket_clients:
            return
            
        message = json.dumps(event.to_dict())
        disconnected_clients = []
        
        for websocket in self.websocket_clients:
            try:
                await websocket.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send to WebSocket: {e}")
                disconnected_clients.append(websocket)
        
        # Remove disconnected clients
        for websocket in disconnected_clients:
            self.websocket_clients.remove(websocket)
    
    def add_websocket_client(self, websocket: WebSocket):
        """Add a new WebSocket client"""
        self.websocket_clients.append(websocket)
        logger.info(f"WebSocket client added. Total clients: {len(self.websocket_clients)}")
    
    def remove_websocket_client(self, websocket: WebSocket):
        """Remove a WebSocket client"""
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)
            logger.info(f"WebSocket client removed. Total clients: {len(self.websocket_clients)}")
    
    def get_active_calls(self) -> List[Dict]:
        """Get list of active calls"""
        return [call.to_dict() for call in self.active_calls.values()]
    
    def get_status(self) -> Dict:
        """Get Asterisk manager status"""
        return {
            "connected": self.connected,
            "host": self.host,
            "port": self.port,
            "active_calls": len(self.active_calls),
            "websocket_clients": len(self.websocket_clients)
        }

# Global instance
asterisk_manager = AsteriskManager(
    host="localhost",
    port=5038,
    username="admin",
    password="admin123"
) 
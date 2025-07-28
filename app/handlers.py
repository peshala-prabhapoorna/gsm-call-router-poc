import asyncio
import json
import logging
from typing import Dict, List, Optional
from asterisk.ami import AMIClient, SimpleAction
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class CallEvent:
    def __init__(self, event_type: str, channel: str, caller_id: str = "", 
                 extension: str = "", unique_id: str = "", timestamp: str = ""):
        self.event_type = event_type
        self.channel = channel
        self.caller_id = caller_id
        self.extension = extension
        self.unique_id = unique_id
        self.timestamp = timestamp
    
    def to_dict(self):
        return {
            "event_type": self.event_type,
            "channel": self.channel,
            "caller_id": self.caller_id,
            "extension": self.extension,
            "unique_id": self.unique_id,
            "timestamp": self.timestamp
        }

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
            
            call_event = CallEvent(
                event_type=event_type,
                channel=channel,
                caller_id=caller_id,
                extension=extension,
                unique_id=unique_id,
                timestamp=event.get('Timestamp', '')
            )
            
            # Handle specific call events
            if event_type == 'Newchannel':
                self.active_calls[unique_id] = call_event
                logger.info(f"New call started: {caller_id} -> {extension}")
                
            elif event_type == 'Newstate':
                if event.get('ChannelState') == '6':  # Up
                    logger.info(f"Call answered: {channel}")
                    
            elif event_type == 'Hangup':
                if unique_id in self.active_calls:
                    del self.active_calls[unique_id]
                logger.info(f"Call ended: {channel}")
                
            elif event_type == 'Dial':
                logger.info(f"Call dialing: {channel}")
                
            # Broadcast event to all WebSocket clients
            asyncio.create_task(self._broadcast_event(call_event))
            
        except Exception as e:
            logger.error(f"Error handling AMI event: {e}")
    
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
    
    async def originate_call(self, to_number: str, from_number: str, context: str = "from-internal") -> bool:
        """Originate a call via Asterisk AMI"""
        if not self.connected or not self.client:
            logger.error("Not connected to Asterisk AMI")
            return False
            
        try:
            action = SimpleAction(
                'Originate',
                Channel=f'SIP/{to_number}',
                Context=context,
                Exten=to_number,
                Callerid=from_number,
                Priority=1
            )
            
            response = self.client.send_action(action)
            logger.info(f"Originated call: {from_number} -> {to_number}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to originate call: {e}")
            return False
    
    async def hangup_call(self, channel: str) -> bool:
        """Hang up a call via Asterisk AMI"""
        if not self.connected or not self.client:
            logger.error("Not connected to Asterisk AMI")
            return False
            
        try:
            action = SimpleAction(
                'Hangup',
                Channel=channel
            )
            
            response = self.client.send_action(action)
            logger.info(f"Hung up call: {channel}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to hang up call: {e}")
            return False
    
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

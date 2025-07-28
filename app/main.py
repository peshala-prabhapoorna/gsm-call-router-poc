from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
from app.handlers import asterisk_manager
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    logger.info("Starting GSM Call Router POC...")
    success = await asterisk_manager.connect()
    if success:
        logger.info("Successfully connected to Asterisk AMI")
    else:
        logger.warning("Failed to connect to Asterisk AMI. Some features may not work.")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GSM Call Router POC...")
    asterisk_manager.disconnect()

app = FastAPI(
    title="GSM Call Router POC", 
    description="Asterisk call handling with WebSockets",
    lifespan=lifespan
)

@app.websocket("/ws/calls")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    asterisk_manager.add_websocket_client(websocket)
    
    try:
        # Send initial status
        status = asterisk_manager.get_status()
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": status
        }))
        
        # Send current active calls
        active_calls = asterisk_manager.get_active_calls()
        await websocket.send_text(json.dumps({
            "type": "active_calls",
            "data": active_calls
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        asterisk_manager.remove_websocket_client(websocket)

async def handle_websocket_message(websocket: WebSocket, message: dict):
    """Handle incoming WebSocket messages"""
    message_type = message.get("type")
    
    if message_type == "originate_call":
        to_number = message.get("to_number")
        from_number = message.get("from_number")
        
        if not to_number or not from_number:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Missing to_number or from_number"
            }))
            return
            
        success = await asterisk_manager.originate_call(to_number, from_number)
        await websocket.send_text(json.dumps({
            "type": "originate_response",
            "success": success,
            "to_number": to_number,
            "from_number": from_number
        }))
        
    elif message_type == "hangup_call":
        channel = message.get("channel")
        
        if not channel:
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Missing channel"
            }))
            return
            
        success = await asterisk_manager.hangup_call(channel)
        await websocket.send_text(json.dumps({
            "type": "hangup_response",
            "success": success,
            "channel": channel
        }))
        
    elif message_type == "get_status":
        status = asterisk_manager.get_status()
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": status
        }))
        
    elif message_type == "get_active_calls":
        active_calls = asterisk_manager.get_active_calls()
        await websocket.send_text(json.dumps({
            "type": "active_calls",
            "data": active_calls
        }))
        
    else:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Unknown message type: {message_type}"
        }))

# REST API endpoints
@app.get("/")
async def root():
    return {"message": "GSM Call Router POC", "status": "running"}

@app.get("/status")
async def get_status():
    """Get Asterisk manager status"""
    return asterisk_manager.get_status()

@app.get("/calls/active")
async def get_active_calls():
    """Get list of active calls"""
    return {"active_calls": asterisk_manager.get_active_calls()}

@app.post("/calls/originate")
async def originate_call(to_number: str, from_number: str, context: str = "from-internal"):
    """Originate a call via REST API"""
    success = await asterisk_manager.originate_call(to_number, from_number, context)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to originate call")
    return {"success": True, "to_number": to_number, "from_number": from_number}

@app.post("/calls/hangup")
async def hangup_call(channel: str):
    """Hang up a call via REST API"""
    success = await asterisk_manager.hangup_call(channel)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to hang up call")
    return {"success": True, "channel": channel}

# Simple HTML test page
@app.get("/test", response_class=HTMLResponse)
async def test_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GSM Call Router Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .container { max-width: 800px; margin: 0 auto; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .events { height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; }
            .controls { margin: 20px 0; }
            input, button { margin: 5px; padding: 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>GSM Call Router Test</h1>
            <div id="status" class="status disconnected">Connecting...</div>
            
            <div class="controls">
                <h3>Originate Call</h3>
                <input type="text" id="toNumber" placeholder="To Number">
                <input type="text" id="fromNumber" placeholder="From Number">
                <button onclick="originateCall()">Originate Call</button>
            </div>
            
            <div class="controls">
                <h3>Hangup Call</h3>
                <input type="text" id="channel" placeholder="Channel">
                <button onclick="hangupCall()">Hangup Call</button>
            </div>
            
            <h3>Call Events</h3>
            <div id="events" class="events"></div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws/calls');
            
            ws.onopen = function() {
                document.getElementById('status').textContent = 'Connected';
                document.getElementById('status').className = 'status connected';
            };
            
            ws.onclose = function() {
                document.getElementById('status').textContent = 'Disconnected';
                document.getElementById('status').className = 'status disconnected';
            };
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                const eventsDiv = document.getElementById('events');
                const timestamp = new Date().toLocaleTimeString();
                
                eventsDiv.innerHTML += `<div>[${timestamp}] ${JSON.stringify(data)}</div>`;
                eventsDiv.scrollTop = eventsDiv.scrollHeight;
            };
            
            function originateCall() {
                const toNumber = document.getElementById('toNumber').value;
                const fromNumber = document.getElementById('fromNumber').value;
                
                if (toNumber && fromNumber) {
                    ws.send(JSON.stringify({
                        type: 'originate_call',
                        to_number: toNumber,
                        from_number: fromNumber
                    }));
                }
            }
            
            function hangupCall() {
                const channel = document.getElementById('channel').value;
                
                if (channel) {
                    ws.send(JSON.stringify({
                        type: 'hangup_call',
                        channel: channel
                    }));
                }
            }
        </script>
    </body>
    </html>
    """

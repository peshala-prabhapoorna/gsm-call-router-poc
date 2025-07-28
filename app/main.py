from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import logging
import json

from .asterisk_manager import asterisk_manager

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
        logger.warning("Failed to connect to Asterisk AMI")
    
    yield
    
    # Shutdown
    logger.info("Shutting down GSM Call Router POC...")
    asterisk_manager.disconnect()

app = FastAPI(
    title="GSM Call Router POC",
    lifespan=lifespan
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "GSM Call Router POC", "status": "running"}

@app.get("/status")
async def get_status():
    """Get status"""
    return asterisk_manager.get_status()

@app.get("/calls/active")
async def get_active_calls():
    """Get active calls"""
    return {"active_calls": asterisk_manager.get_active_calls()}

@app.websocket("/ws/calls")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time call events"""
    await websocket.accept()
    asterisk_manager.add_websocket_client(websocket)
    
    try:
        # Send initial status
        status = asterisk_manager.get_status()
        await websocket.send_text(json.dumps({
            "type": "status",
            "data": status
        }))
        
        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Just echo back for now
            await websocket.send_text(json.dumps({
                "type": "echo",
                "message": data
            }))
                
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        asterisk_manager.remove_websocket_client(websocket)

@app.get("/test", response_class=HTMLResponse)
async def test_page():
    """Simple test page"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>GSM Call Router Test</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .connected { background-color: #d4edda; color: #155724; }
            .disconnected { background-color: #f8d7da; color: #721c24; }
            .events { height: 300px; overflow-y: scroll; border: 1px solid #ccc; padding: 10px; }
        </style>
    </head>
    <body>
        <h1>GSM Call Router Test</h1>
        <div id="status" class="status disconnected">Connecting...</div>
        <h3>Call Events</h3>
        <div id="events" class="events"></div>
        
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
        </script>
    </body>
    </html>
    """

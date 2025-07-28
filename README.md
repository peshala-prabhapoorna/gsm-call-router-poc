# GSM Call Router POC

This proof-of-concept demonstrates handling GSM calls using FastAPI (with WebSockets), Asterisk, and Bevatel SIP.

## Architecture

- **Asterisk**: Telephony server, handles SIP (Bevatel) and GSM calls.
- **FastAPI**: Backend with WebSocket endpoint for real-time call events.
- **WebSockets**: Real-time communication for call events.
- **Bevatel SIP**: SIP trunk/provider for call routing.

## Setup

### 1. Python Backend

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

WebSocket endpoint: `ws://localhost:8000/ws/calls`

### 2. Asterisk Configuration

#### Enable AMI (Asterisk Manager Interface)

Add to `/etc/asterisk/manager.conf`:

```
[general]
enabled = yes
port = 5038
bindaddr = 0.0.0.0

[admin]
secret = admin123
deny=0.0.0.0/0
permit=127.0.0.1/255.255.255.0
read = all
write = all
```

#### Example Bevatel SIP Trunk

Add to `/etc/asterisk/sip.conf`:

```
[bevatel]
type=peer
host=sip.bevatel.com
username=YOUR_BEVATEL_USERNAME
secret=YOUR_BEVATEL_PASSWORD
fromuser=YOUR_BEVATEL_USERNAME
context=from-bevatel
insecure=invite,port
qualify=yes
```

#### Example GSM Channel (using chan_dongle or similar)

Add to `/etc/asterisk/dongle.conf`:

```
[defaults]
default_context=from-gsm

[dongle0]
imei=YOUR_DONGLE_IMEI
imsi=YOUR_DONGLE_IMSI
context=from-gsm
```

#### Example Dialplan

Add to `/etc/asterisk/extensions.conf`:

```
[from-bevatel]
exten => _X.,1,NoOp(Incoming SIP from Bevatel)
 same => n,Dial(Dongle/dongle0/${EXTEN})
 same => n,Hangup()

[from-gsm]
exten => _X.,1,NoOp(Incoming GSM call)
 same => n,Dial(SIP/bevatel/${EXTEN})
 same => n,Hangup()

[from-internal]
exten => _X.,1,NoOp(Internal call)
 same => n,Dial(SIP/bevatel/${EXTEN})
 same => n,Hangup()
```

### 3. Usage

#### WebSocket API

Connect to `ws://localhost:8000/ws/calls` and send JSON messages:

**Originate a call:**
```json
{
    "type": "originate_call",
    "to_number": "1234567890",
    "from_number": "0987654321"
}
```

**Hangup a call:**
```json
{
    "type": "hangup_call",
    "channel": "SIP/1234567890-00000001"
}
```

**Get status:**
```json
{
    "type": "get_status"
}
```

**Get active calls:**
```json
{
    "type": "get_active_calls"
}
```

#### REST API

- `GET /status` - Get Asterisk manager status
- `GET /calls/active` - Get list of active calls
- `POST /calls/originate?to_number=123&from_number=456` - Originate a call
- `POST /calls/hangup?channel=SIP/123-00000001` - Hangup a call

#### Test Interface

Visit `http://localhost:8000/test` for a simple web interface to test the functionality.

### 4. Call Events

The system monitors and broadcasts these Asterisk events:
- `Newchannel` - New call started
- `Newstate` - Call state changed (answered, ringing, etc.)
- `Dial` - Call dialing
- `Hangup` - Call ended

## Notes
- This is a POC. Security, error handling, and production hardening are not included.
- You must have Asterisk and required modules (chan_sip, chan_dongle, etc.) installed.
- Default AMI credentials are admin/admin123. Change these in production.
- The system automatically connects to Asterisk AMI on startup and disconnects on shutdown.
- If systemd service fails, use manual startup: `sudo -u asterisk asterisk -f &` 
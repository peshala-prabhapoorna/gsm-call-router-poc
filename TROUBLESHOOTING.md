# Troubleshooting Guide - GSM Call Router POC

## Quick Fixes

### 1. Asterisk Won't Start

**Symptoms:** `Connection refused` when FastAPI tries to connect to AMI

**Solution:**
```bash
# Check if Asterisk is running
sudo systemctl status asterisk

# If not running, try manual startup
sudo -u asterisk asterisk -f &

# Check if it's running
ps aux | grep asterisk | grep -v grep
```

### 2. Database Permission Issues

**Symptoms:** `ASTdb initialization failed` in logs

**Solution:**
```bash
# Fix database permissions
sudo chmod 640 /var/lib/asterisk/astdb.sqlite3
sudo chown asterisk:asterisk /var/lib/asterisk/astdb.sqlite3
```

### 3. AMI Connection Failed

**Symptoms:** FastAPI shows `Failed to connect to Asterisk AMI`

**Solution:**
```bash
# Test AMI connection manually
echo "Action: Login
Username: admin
Secret: admin123

Action: Ping

Action: Logoff" | nc localhost 5038
```

### 4. Systemd Service Issues

**Symptoms:** Service keeps restarting or won't start

**Solution:**
```bash
# Use manual startup instead
sudo pkill -f "asterisk -f"  # Stop any running instances
sudo -u asterisk asterisk -f &

# Check logs
sudo journalctl -u asterisk -f
```

## Common Commands

```bash
# Check Asterisk status
sudo systemctl status asterisk

# View Asterisk logs
sudo tail -f /var/log/asterisk/messages

# Connect to Asterisk CLI
sudo asterisk -r

# Test AMI connection
nc localhost 5038

# Check FastAPI connection
curl http://localhost:8000/status
```

## Configuration Files

- **AMI Config:** `/etc/asterisk/manager.conf`
- **SIP Config:** `/etc/asterisk/sip.conf`
- **Dialplan:** `/etc/asterisk/extensions.conf`
- **Service:** `/etc/systemd/system/asterisk.service`

## Default Credentials

- **AMI Username:** admin
- **AMI Password:** admin123
- **AMI Port:** 5038
- **SIP Port:** 5060

## FastAPI Endpoints

- **Status:** `GET http://localhost:8000/status`
- **Active Calls:** `GET http://localhost:8000/calls/active`
- **WebSocket:** `ws://localhost:8000/ws/calls`
- **Test Interface:** `http://localhost:8000/test` 
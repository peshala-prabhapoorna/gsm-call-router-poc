# Asterisk Configuration Guide for GSM Call Router POC

This guide walks you through setting up Asterisk with real configurations for the GSM Call Router POC.

## Prerequisites

- Linux system (Ubuntu/Debian or CentOS/RHEL)
- Root or sudo access
- Internet connection
- Bevatel SIP account credentials

## Step 1: Install Asterisk

### Option A: Automated Installation (Recommended)

```bash
# Make the setup script executable
chmod +x asterisk-setup.sh

# Run the automated setup
sudo ./asterisk-setup.sh
```

### Option B: Manual Installation

#### For Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install -y build-essential wget libssl-dev libncurses5-dev libnewt-dev libxml2-dev linux-headers-$(uname -r) libsqlite3-dev uuid-dev libjansson-dev libcurl4-openssl-dev

cd /tmp
wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-22-current.tar.gz
tar -xzf asterisk-22-current.tar.gz
cd asterisk-22.*

./configure --with-jansson-bundled
make menuselect.makeopts
menuselect/menuselect --enable CORE-SOUNDS-EN-WAV menuselect.makeopts
menuselect/menuselect --enable CORE-SOUNDS-EN-GSM menuselect.makeopts
menuselect/menuselect --enable res_ami menuselect.makeopts
menuselect/menuselect --enable res_ami_config menuselect.makeopts
menuselect/menuselect --enable chan_sip menuselect.makeopts
menuselect/menuselect --enable pbx_config menuselect.makeopts
menuselect/menuselect --enable res_pjsip menuselect.makeopts
menuselect/menuselect --enable res_pjsip_config menuselect.makeopts

make -j$(nproc)
sudo make install
sudo make samples
sudo make config
```

#### For CentOS/RHEL:
```bash
sudo yum groupinstall -y "Development Tools"
sudo yum install -y wget openssl-devel ncurses-devel newt-devel libxml2-devel kernel-devel sqlite-devel libuuid-devel jansson-devel libcurl-devel

# Follow the same download and build steps as above
```

## Step 2: Configure Asterisk

### 2.1 Copy Configuration Files

```bash
# Copy the provided configuration files
sudo cp asterisk-config/*.conf /etc/asterisk/

# Set proper permissions
sudo chown -R asterisk:asterisk /etc/asterisk
sudo chmod -R 640 /etc/asterisk
sudo chmod 750 /etc/asterisk
```

### 2.2 Fix Database Permissions

```bash
# Fix database file permissions
sudo chmod 640 /var/lib/asterisk/astdb.sqlite3
sudo chown asterisk:asterisk /var/lib/asterisk/astdb.sqlite3
```

### 2.2 Update Bevatel SIP Configuration

Edit `/etc/asterisk/sip.conf` and replace the Bevatel section:

```ini
[bevatel]
type=peer
host=sip.bevatel.com
username=YOUR_ACTUAL_BEVATEL_USERNAME
secret=YOUR_ACTUAL_BEVATEL_PASSWORD
fromuser=YOUR_ACTUAL_BEVATEL_USERNAME
context=from-bevatel
insecure=invite,port
qualify=yes
nat=force_rport,comedia
canreinvite=no
dtmfmode=rfc2833
disallow=all
allow=ulaw
allow=alaw
```

### 2.3 Create Asterisk User (if not exists)

```bash
sudo useradd -r -d /var/lib/asterisk -c "Asterisk PBX" asterisk
sudo chown -R asterisk:asterisk /var/lib/asterisk /var/spool/asterisk /var/log/asterisk /var/run/asterisk
```

## Step 3: Start Asterisk

### 3.1 Create Systemd Service

```bash
sudo tee /etc/systemd/system/asterisk.service > /dev/null <<EOF
[Unit]
Description=Asterisk PBX
After=network.target

[Service]
Type=simple
User=asterisk
Group=asterisk
ExecStart=/usr/sbin/asterisk -f
ExecStop=/usr/sbin/asterisk -rx "core stop now"
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
```

### 3.2 Start and Enable Asterisk

```bash
sudo systemctl daemon-reload
sudo systemctl enable asterisk
sudo systemctl start asterisk
```

## Step 4: Verify Configuration

### 4.1 Check Asterisk Status

```bash
sudo systemctl status asterisk
```

### 4.2 Test AMI Connection

```bash
# Test AMI login
echo "Action: Login
Username: admin
Secret: admin123

Action: Ping

Action: Logoff" | nc localhost 5038
```

Expected output:
```
Response: Success
Message: Authentication accepted

Response: Success
Ping: Pong

Response: Goodbye
Message: Thanks for all the fish.
```

### 4.3 Connect to Asterisk CLI

```bash
sudo asterisk -r
```

### 4.4 Check SIP Peers

In Asterisk CLI:
```bash
asterisk*CLI> sip show peers
```

### 4.5 Check AMI Status

In Asterisk CLI:
```bash
asterisk*CLI> manager show status
```

## Step 5: Test the Setup

### 5.1 Test Internal Extension

```bash
# From Asterisk CLI
asterisk*CLI> dialplan show from-internal
asterisk*CLI> core show channels
```

### 5.2 Test SIP Registration

```bash
# Check if Bevatel SIP trunk is registered
asterisk*CLI> sip show peers
asterisk*CLI> sip show registry
```

### 5.3 Test Call Origination

```bash
# From Asterisk CLI, originate a test call
asterisk*CLI> channel originate SIP/bevatel/1234567890 extension 999@from-internal
```

## Step 6: Configure Firewall

```bash
# Allow Asterisk ports
sudo ufw allow 5060/udp  # SIP
sudo ufw allow 5060/tcp  # SIP
sudo ufw allow 5038/tcp  # AMI
sudo ufw allow 10000:20000/udp  # RTP media
```

## Troubleshooting

### Common Issues and Solutions

#### 1. Asterisk Won't Start (Database Permission Issues)
```bash
# Check if Asterisk can access the database
sudo ls -la /var/lib/asterisk/astdb.sqlite3

# Fix database permissions if needed
sudo chmod 640 /var/lib/asterisk/astdb.sqlite3
sudo chown asterisk:asterisk /var/lib/asterisk/astdb.sqlite3

# Check systemd service status
sudo systemctl status asterisk

# View detailed logs
sudo journalctl -u asterisk -f
```

#### 2. AMI Connection Failed
```bash
# Check if AMI is enabled
sudo asterisk -rx "manager show status"

# Check manager.conf
sudo cat /etc/asterisk/manager.conf

# Check logs
sudo tail -f /var/log/asterisk/messages
```

#### 2. SIP Registration Failed
```bash
# Check SIP peers
sudo asterisk -rx "sip show peers"

# Check SIP registry
sudo asterisk -rx "sip show registry"

# Check SIP debug
sudo asterisk -rx "sip set debug on"
```

#### 3. Asterisk Won't Start
```bash
# Check configuration syntax
sudo asterisk -C /etc/asterisk/asterisk.conf -x "core show version"

# Check for missing modules
sudo asterisk -rx "module show"

# Check logs
sudo journalctl -u asterisk -f
```

#### 4. Permission Issues
```bash
# Fix ownership
sudo chown -R asterisk:asterisk /var/lib/asterisk /var/spool/asterisk /var/log/asterisk /var/run/asterisk /etc/asterisk

# Fix permissions
sudo chmod -R 640 /etc/asterisk
sudo chmod 750 /etc/asterisk

# Fix database permissions specifically
sudo chmod 640 /var/lib/asterisk/astdb.sqlite3
sudo chown asterisk:asterisk /var/lib/asterisk/astdb.sqlite3
```

#### 5. Systemd Service Issues
```bash
# If systemd service fails, try manual startup
sudo -u asterisk asterisk -f &

# Check if Asterisk is running
ps aux | grep asterisk | grep -v grep

# Test AMI connection manually
echo "Action: Login
Username: admin
Secret: admin123

Action: Ping

Action: Logoff" | nc localhost 5038
```

### Useful Commands

```bash
# View real-time logs
sudo tail -f /var/log/asterisk/messages

# Check channel status
sudo asterisk -rx "core show channels"

# Check dialplan
sudo asterisk -rx "dialplan show"

# Reload configuration
sudo asterisk -rx "core reload"

# Stop Asterisk gracefully
sudo asterisk -rx "core stop now"

# Restart Asterisk
sudo systemctl restart asterisk
```

## Next Steps

1. **Update your FastAPI application** to use the correct AMI credentials (already done in the code):
   ```python
   asterisk_manager = AsteriskManager(
       host="localhost",
       port=5038,
       username="admin",
       password="admin123"
   )
   ```

2. **Test the complete system**:
   ```bash
   # Start your FastAPI app
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   
   # Visit the test interface
   http://localhost:8000/test
   ```

3. **Monitor call events** in real-time through the WebSocket interface.

## Configuration Files Summary

- **manager.conf**: AMI configuration for FastAPI connection
- **sip.conf**: SIP trunk and extension configuration
- **extensions.conf**: Dialplan for call routing
- **asterisk.conf**: Basic Asterisk settings
- **modules.conf**: Required modules to load
- **logger.conf**: Logging configuration

All configuration files are provided in the `asterisk-config/` directory and should be copied to `/etc/asterisk/` during setup. 
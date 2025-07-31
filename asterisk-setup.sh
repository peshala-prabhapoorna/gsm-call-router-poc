#!/bin/bash

# Asterisk Setup Script for GSM Call Router POC
# This script helps install and configure Asterisk

set -e

echo "=== Asterisk Setup for GSM Call Router POC ==="

# Detect OS
if [ -f /etc/debian_version ]; then
    OS="debian"
elif [ -f /etc/redhat-release ]; then
    OS="redhat"
else
    echo "Unsupported OS. Please install Asterisk manually."
    exit 1
fi

echo "Detected OS: $OS"

# Install dependencies
echo "Installing dependencies..."
if [ "$OS" = "debian" ]; then
    sudo apt-get update
    sudo apt-get install -y build-essential wget libssl-dev libncurses5-dev libnewt-dev libxml2-dev linux-headers-$(uname -r) libsqlite3-dev uuid-dev libjansson-dev libcurl4-openssl-dev
elif [ "$OS" = "redhat" ]; then
    sudo yum groupinstall -y "Development Tools"
    sudo yum install -y wget openssl-devel ncurses-devel newt-devel libxml2-devel kernel-devel sqlite-devel libuuid-devel jansson-devel libcurl-devel
fi

# Download and install Asterisk 22.5 LTS
echo "Downloading Asterisk 22.5 LTS..."
cd /tmp
wget https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-22-current.tar.gz
tar -xzf asterisk-22-current.tar.gz
cd asterisk-22.*

echo "Configuring Asterisk..."
./configure --with-jansson-bundled

echo "Building Asterisk 22.5 LTS..."
make menuselect.makeopts
menuselect/menuselect --enable CORE-SOUNDS-EN-WAV menuselect.makeopts
menuselect/menuselect --enable CORE-SOUNDS-EN-GSM menuselect.makeopts
menuselect/menuselect --enable res_ami menuselect.makeopts
menuselect/menuselect --enable res_ami_config menuselect.makeopts
menuselect/menuselect --enable pbx_config menuselect.makeopts
menuselect/menuselect --enable res_pjsip menuselect.makeopts
menuselect/menuselect --enable res_pjsip_config menuselect.makeopts
menuselect/menuselect --enable chan_pjsip menuselect.makeopts

make -j$(nproc)
sudo make install
sudo make samples
sudo make config

# Create asterisk user
echo "Creating asterisk user..."
sudo useradd -r -d /var/lib/asterisk -c "Asterisk PBX" asterisk
sudo chown -R asterisk:asterisk /var/lib/asterisk /var/spool/asterisk /var/log/asterisk /var/run/asterisk

# Copy configuration files
echo "Copying configuration files..."
sudo cp asterisk-config/*.conf /etc/asterisk/

# Set permissions
sudo chown -R asterisk:asterisk /etc/asterisk
sudo chmod -R 640 /etc/asterisk
sudo chmod 750 /etc/asterisk

# Create systemd service
echo "Creating systemd service..."
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

# Enable and start Asterisk
echo "Starting Asterisk..."
sudo systemctl daemon-reload
sudo systemctl enable asterisk
sudo systemctl start asterisk

# Wait for Asterisk to start
sleep 5

# Test AMI connection
echo "Testing AMI connection..."
if echo "Action: Login
Username: admin
Secret: admin123

Action: Ping

Action: Logoff" | nc localhost 5038 | grep -q "Response: Success"; then
    echo "✅ AMI connection successful!"
else
    echo "❌ AMI connection failed. Please check configuration."
fi

echo ""
echo "=== Setup Complete ==="
echo "Asterisk 22.5 LTS is now running with the following configuration:"
echo "- AMI enabled on port 5038"
echo "- PJSIP enabled on port 5060 (modern SIP stack)"
echo "- Admin credentials: admin/admin123"
echo ""
echo "Next steps:"
echo "1. Update /etc/asterisk/pjsip.conf with your Bevatel credentials"
echo "2. Test the connection: sudo asterisk -rx 'pjsip show endpoints'"
echo "3. Start your FastAPI application"
echo ""
echo "Useful commands:"
echo "- Connect to Asterisk CLI: sudo asterisk -r"
echo "- Check PJSIP endpoints: sudo asterisk -rx 'pjsip show endpoints'"
echo "- Check AMI status: sudo asterisk -rx 'manager show status'"
echo "- View logs: sudo tail -f /var/log/asterisk/messages" 
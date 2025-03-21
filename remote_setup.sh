#!/bin/bash

# Update system
sudo apt-get update
sudo apt-get upgrade -y

# Install Python and dependencies
sudo apt-get install -y python3-pip python3-venv

# Create service user
sudo useradd -r -s /bin/false tasksync || true

# Create application directory
sudo mkdir -p /opt/tasksync
sudo chown tasksync:tasksync /opt/tasksync

# Setup virtual environment
cd /opt/tasksync
sudo -u tasksync python3 -m venv venv
sudo -u tasksync ./venv/bin/pip install -r requirements.txt

# Setup systemd service
sudo cp tasksync.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tasksync
sudo systemctl start tasksync

echo "Deployment complete! Checking service status..."
sudo systemctl status tasksync

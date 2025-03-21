#!/bin/bash

# Check if instance IP is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
ZONE="europe-west1-b"
INSTANCE_NAME="task-sync"

echo "Deploying to instance: $INSTANCE_IP"

# Create remote setup script
cat > remote_setup.sh << 'EOF'
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
EOF

# Copy files to instance
echo "Copying files to instance..."
gcloud compute scp --recurse \
    src \
    config \
    requirements.txt \
    deploy/tasksync.service \
    remote_setup.sh \
    $INSTANCE_NAME:/tmp/ \
    --zone=$ZONE

# Execute remote setup
echo "Running remote setup..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- "
    cd /tmp && \
    chmod +x remote_setup.sh && \
    sudo systemctl stop tasksync && \
    sudo rm -rf /opt/tasksync/src/* /opt/tasksync/config/* && \
    sudo cp -r src/* /opt/tasksync/src/ && \
    sudo cp -r config/* /opt/tasksync/config/ && \
    sudo cp requirements.txt /opt/tasksync/ && \
    sudo cp tasksync.service /opt/tasksync/ && \
    sudo chown -R tasksync:tasksync /opt/tasksync && \
    ./remote_setup.sh
"

# Cleanup
rm remote_setup.sh

echo "Deployment complete!"
echo "To check logs: gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- 'sudo journalctl -u tasksync -f'"

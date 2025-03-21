#!/bin/bash

# Check if project ID is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <project-id>"
    exit 1
fi

PROJECT_ID=$1
INSTANCE_NAME="task-sync"
ZONE="europe-west1-b"

echo "Setting up GCP project: $PROJECT_ID"

# Initialize gcloud and set project
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable compute.googleapis.com
s
# Create VM instance
echo "Creating e2-micro instance..."
gcloud compute instances create $INSTANCE_NAME \
    --machine-type=e2-micro \
    --zone=$ZONE \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=10GB \
    --tags=http-server

# Create firewall rule for SSH
echo "Setting up firewall rules..."
gcloud compute firewall-rules create allow-ssh \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:22 \
    --source-ranges=0.0.0.0/0

# Get instance IP
INSTANCE_IP=$(gcloud compute instances describe $INSTANCE_NAME \
    --zone=$ZONE \
    --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo "Setup complete!"
echo "Instance IP: $INSTANCE_IP"
echo "Next step: Run ./2_deploy.sh $INSTANCE_IP"

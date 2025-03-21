#!/bin/bash

# Check if instance IP is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
ZONE="europe-west1-b"
INSTANCE_NAME="task-sync"

echo "Updating application on instance: $INSTANCE_IP"

# Copy updated files
echo "Copying updated files..."
gcloud compute scp --recurse \
    ../src \
    ../config \
    $INSTANCE_NAME:/tmp/update \
    --zone=$ZONE

# Apply updates
echo "Applying updates..."
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- "
    sudo cp -r /tmp/update/src/* /opt/tasksync/src/ && \
    sudo cp -r /tmp/update/config/* /opt/tasksync/config/ && \
    sudo chown -R tasksync:tasksync /opt/tasksync/src /opt/tasksync/config && \
    sudo systemctl restart tasksync && \
    sudo systemctl status tasksync
"

echo "Update complete!"

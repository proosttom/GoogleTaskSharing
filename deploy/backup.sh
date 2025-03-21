#!/bin/bash

# Check if instance IP is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <instance-ip>"
    exit 1
fi

INSTANCE_IP=$1
ZONE="europe-west1-b"
INSTANCE_NAME="task-sync"
BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create local backup directory
mkdir -p $BACKUP_DIR

echo "Creating backup from instance: $INSTANCE_IP"

# Create backup on instance
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- "
    sudo tar czf /tmp/tasksync-backup-$DATE.tar.gz /opt/tasksync/config
"

# Copy backup locally
gcloud compute scp \
    $INSTANCE_NAME:/tmp/tasksync-backup-$DATE.tar.gz \
    $BACKUP_DIR/ \
    --zone=$ZONE

# Cleanup remote backup
gcloud compute ssh $INSTANCE_NAME --zone=$ZONE -- "
    sudo rm /tmp/tasksync-backup-$DATE.tar.gz
"

echo "Backup complete! Saved to $BACKUP_DIR/tasksync-backup-$DATE.tar.gz"

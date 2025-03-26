import os
import time
import yaml
import logging
from googleapiclient.errors import HttpError
from auth import get_credentials
from tasks_manager import TasksManager, sync_tasks

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def update_sync_interval(current_interval: int, base_interval: int, min_interval: int, max_interval: int, 
                        backoff_multiplier: int, sync_success: bool) -> int:
    """Update the sync interval based on sync success/failure.
    
    Args:
        current_interval: Current sync interval in seconds
        base_interval: Base sync interval in seconds
        min_interval: Minimum allowed sync interval in seconds
        max_interval: Maximum allowed sync interval in seconds
        backoff_multiplier: Factor to multiply/divide interval by on failure/success
        sync_success: Whether the last sync was successful
    
    Returns:
        Updated sync interval in seconds
    """
    if sync_success:
        # On success, gradually reduce interval back to base
        new_interval = max(min_interval, current_interval // backoff_multiplier)
        if new_interval != base_interval:
            logging.info(f"Sync successful, reducing interval to {new_interval} seconds")
    else:
        # On failure, increase interval
        new_interval = min(max_interval, current_interval * backoff_multiplier)
        logging.warning(f"Sync had errors, increasing interval to {new_interval} seconds")
    
    return new_interval

def main():
    # Load configuration
    config_path = os.path.join('config', 'config.yaml')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at {config_path}")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Initialize credentials and task managers
    credentials_path = os.path.join('config', 'credentials.json')
    token_dir = os.path.join('config', 'tokens')
    user_managers = {}

    # Create task managers for each user
    for user in config['users']:
        email = user['email']
        try:
            credentials = get_credentials(email, credentials_path, token_dir)
            user_managers[email] = TasksManager(credentials, email)
            logging.info(f"Successfully initialized TasksManager for {email}")
        except Exception as e:
            logging.error(f"Failed to initialize TasksManager for {email}: {e}")
            continue

    # Get sync configuration
    base_sync_interval = config.get('sync_interval_seconds', 300)
    current_sync_interval = base_sync_interval
    backoff_multiplier = 2
    max_sync_interval = 3600  # Maximum 1 hour
    min_sync_interval = base_sync_interval

    logging.info(f"Starting sync with interval: {base_sync_interval} seconds")

    while True:
        try:
            sync_success = True  # Track if all syncs in this iteration succeeded
            # Sync tasks for each user
            for user in config['users']:
                email = user['email']
                task_lists = user.get('task_lists', [])

                if email not in user_managers:
                    logging.warning(f"Skipping sync for {email} - no valid task manager")
                    sync_success = False
                    continue

                for list_name in task_lists:
                    try:
                        # Sync with each shared user
                        share_with = list_name.get('share_with', [])
                        for target_email in share_with:
                            if target_email in user_managers:
                                try:
                                    logging.info(f"Syncing '{list_name['name']}' from {email} to {target_email}")
                                    sync_tasks(user_managers[email], user_managers[target_email], list_name['name'])
                                except Exception as e:
                                    logging.error(f"Failed to sync '{list_name['name']}' from {email} to {target_email}: {e}")
                                    sync_success = False
                            else:
                                logging.warning(f"Cannot sync with {target_email} - no valid task manager")
                                sync_success = False
                    except Exception as e:
                        logging.error(f"Failed to process task list '{list_name}' for {email}: {e}")
                        sync_success = False

            # Adjust sync interval based on success/failure
            current_sync_interval = update_sync_interval(
                current_sync_interval,
                base_sync_interval,
                min_sync_interval,
                max_sync_interval,
                backoff_multiplier,
                sync_success
            )

            time.sleep(current_sync_interval)

        except Exception as e:
            logging.error(f"Unexpected error during sync: {e}")
            # On unexpected error, increase interval
            current_sync_interval = min(
                max_sync_interval,
                current_sync_interval * backoff_multiplier
            )
            logging.warning(f"Unexpected error, increasing interval to {current_sync_interval} seconds")
            time.sleep(current_sync_interval)

if __name__ == '__main__':
    main()

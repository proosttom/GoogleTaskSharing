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
    format='%(asctime)s - %(levelname)s - %(message)s'
)

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
    min_sync_interval = 5    # Minimum 5 seconds

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
            if sync_success:
                # On success, gradually reduce interval back to base
                current_sync_interval = max(
                    min_sync_interval,
                    current_sync_interval // backoff_multiplier
                )
                if current_sync_interval != base_sync_interval:
                    logging.info(f"Sync successful, reducing interval to {current_sync_interval} seconds")
            else:
                # On failure, increase interval
                current_sync_interval = min(
                    max_sync_interval,
                    current_sync_interval * backoff_multiplier
                )
                logging.warning(f"Sync had errors, increasing interval to {current_sync_interval} seconds")

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

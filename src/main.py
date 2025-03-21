import os
import time
import yaml
import logging
from googleapiclient.errors import HttpError
from auth import get_credentials
from tasks_manager import TasksManager

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
    base_sync_interval = config.get('sync_interval_seconds', 300)  # Default 5 minutes
    current_sync_interval = base_sync_interval
    backoff_multiplier = 2
    max_sync_interval = 3600  # Maximum 1 hour

    logging.info(f"Starting sync with interval: {base_sync_interval} seconds")

    while True:
        try:
            # Sync tasks for each user
            for user in config['users']:
                email = user['email']
                share_with = user.get('share_with', [])
                task_lists = user.get('task_lists', [])

                if email not in user_managers:
                    logging.warning(f"Skipping sync for {email} - no valid task manager")
                    continue

                # Sync each task list
                for list_name in task_lists:
                    logging.info(f"Syncing list '{list_name}' for {email}")
                    
                    # Sync with each shared user
                    for target_email in share_with:
                        if target_email in user_managers:
                            try:
                                user_managers[email].sync_task_list(
                                    list_name, 
                                    user_managers[target_email]
                                )
                                logging.info(f"Successfully synced '{list_name}' from {email} to {target_email}")
                            except Exception as sync_error:
                                logging.error(f"Failed to sync '{list_name}' from {email} to {target_email}: {sync_error}")
            
            # Reset sync interval on successful sync
            if current_sync_interval != base_sync_interval:
                logging.info(f"Resetting sync interval to {base_sync_interval} seconds")
                current_sync_interval = base_sync_interval

        except HttpError as e:
            error_content = e.content.decode('utf-8') if hasattr(e, 'content') else str(e)
            error_reason = e.reason if hasattr(e, 'reason') else 'Unknown reason'
            error_status = e.resp.status if hasattr(e, 'resp') else 'Unknown status'
            error_uri = e.uri if hasattr(e, 'uri') else 'Unknown URI'
            
            logging.error(
                f"HTTP Error:\n"
                f"Status: {error_status}\n"
                f"Reason: {error_reason}\n"
                f"URI: {error_uri}\n"
                f"Content: {error_content}"
            )
            
            if e.resp.status in [401, 403]:
                logging.error("Authentication error - attempting to refresh all tokens")
                # Refresh all tokens
                for email, manager in user_managers.items():
                    try:
                        if manager.credentials.expired:
                            manager.credentials.refresh(Request())
                            logging.info(f"Successfully refreshed token for {email}")
                    except Exception as refresh_error:
                        logging.error(f"Failed to refresh token for {email}: {refresh_error}")
                        # Reinitialize the task manager
                        try:
                            credentials = get_credentials(email, credentials_path, token_dir)
                            user_managers[email] = TasksManager(credentials, email)
                            logging.info(f"Successfully reinitialized TasksManager for {email}")
                        except Exception as reinit_error:
                            logging.error(f"Failed to reinitialize TasksManager for {email}: {reinit_error}")

        except Exception as e:
            logging.error(f"Error during sync: {e}")

        time.sleep(current_sync_interval)

if __name__ == '__main__':
    main()

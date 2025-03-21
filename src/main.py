import yaml
import time
from auth import AuthManager
from tasks_manager import TasksManager
import logging
from googleapiclient.errors import HttpError

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_config():
    with open('config/config.yaml', 'r') as f:
        return yaml.safe_load(f)

def main():
    config = load_config()
    auth_manager = AuthManager()
    base_sync_interval = config.get('sync_interval_seconds', 300)  # Default 5 minutes
    current_sync_interval = base_sync_interval
    backoff_multiplier = 2
    max_sync_interval = 3600  # Max 1 hour

    # Initialize task managers for all users
    user_managers = {}
    for user in config['users']:
        email = user['email']
        credentials = auth_manager.get_credentials(email)
        user_managers[email] = TasksManager(credentials, email)

    logging.info("Task sync service started")

    while True:
        try:
            # Process each user's task lists
            for user in config['users']:
                email = user['email']
                for task_list in user.get('task_lists', []):
                    list_name = task_list['name']
                    share_with = task_list.get('share_with', [])

                    logging.info(f"Syncing task list '{list_name}' from {email}")
                    
                    # Sync with each shared user
                    for target_email in share_with:
                        if target_email in user_managers:
                            user_managers[email].sync_task_list(
                                list_name, 
                                user_managers[target_email]
                            )
            
            # Reset sync interval on successful sync
            if current_sync_interval != base_sync_interval:
                logging.info(f"Resetting sync interval to {base_sync_interval} seconds")
                current_sync_interval = base_sync_interval

        except HttpError as e:
            if e.resp.status == 403 and 'quotaExceeded' in str(e):
                # Increase sync interval with exponential backoff
                current_sync_interval = min(current_sync_interval * backoff_multiplier, max_sync_interval)
                logging.warning(f"Quota exceeded. Increasing sync interval to {current_sync_interval} seconds")
            else:
                logging.error(f"Error during sync: {e}")

        except Exception as e:
            logging.error(f"Error during sync: {e}")

        time.sleep(current_sync_interval)

if __name__ == '__main__':
    main()

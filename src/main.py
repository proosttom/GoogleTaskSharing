import yaml
import time
from auth import AuthManager
from tasks_manager import TasksManager
import logging

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
    sync_interval = config.get('sync_interval_seconds', 30)

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
                    source_manager = user_managers[email]

                    # Sync with each shared user
                    for target_email in share_with:
                        if target_email in user_managers:
                            target_manager = user_managers[target_email]
                            source_manager.sync_task_list(list_name, target_manager)
                            logging.info(f"Synced '{list_name}' with {target_email}")

            time.sleep(sync_interval)

        except Exception as e:
            logging.error(f"Error during sync: {str(e)}")
            time.sleep(5)  # Wait a bit before retrying

if __name__ == '__main__':
    main()

import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

SCOPES = ['https://www.googleapis.com/auth/tasks']
TOKEN_DIR = os.path.join('config', 'tokens')

class AuthManager:
    def __init__(self):
        self.credentials_path = os.path.join('config', 'credentials.json')
        os.makedirs(TOKEN_DIR, exist_ok=True)

    def get_credentials(self, user_email):
        """Get valid credentials for the given user."""
        token_path = os.path.join(TOKEN_DIR, f'{user_email}.token')
        creds = None

        # Verify credentials file exists
        if not os.path.exists(self.credentials_path):
            raise FileNotFoundError(f"Credentials file not found at {self.credentials_path}")

        if os.path.exists(token_path):
            try:
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Error loading token file: {e}")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, SCOPES)
                    # Set port to a specific number and add more parameters for debugging
                    creds = flow.run_local_server(
                        port=8080,
                        authorization_prompt_message='Please authenticate in your browser',
                        success_message='Authentication successful! You may close this window.'
                    )
                except Exception as e:
                    raise RuntimeError(f"Authentication flow failed: {e}")

            try:
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
            except Exception as e:
                print(f"Warning: Failed to save token: {e}")

        return creds

if __name__ == '__main__':
    import yaml
    
    # Load config to get user emails
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    auth_manager = AuthManager()
    
    # Authenticate each user
    for user in config['users']:
        print(f"Authenticating {user['email']}...")
        auth_manager.get_credentials(user['email'])
        print(f"Successfully authenticated {user['email']}")

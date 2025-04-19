import os
import logging
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle

SCOPES = ['https://www.googleapis.com/auth/tasks']

def get_credentials(email, credentials_path, token_dir):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.
    """
    if not os.path.exists(token_dir):
        os.makedirs(token_dir)
        
    token_path = os.path.join(token_dir, f"{email}.token")
    creds = None

    if os.path.exists(token_path):
        logging.info(f"Loading existing token for {email} from {token_path}")
        try:
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
            logging.info(f"Successfully loaded token for {email}")
        except Exception as e:
            logging.error(f"Error loading token for {email}: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            logging.info(f"Token expired for {email}, attempting refresh")
            try:
                creds.refresh(Request())
                logging.info(f"Successfully refreshed token for {email}")
            except Exception as e:
                logging.error(f"Failed to refresh token for {email}: {e}")
                # Force a new token flow
                creds = None
        
        if not creds:
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"credentials.json not found at {credentials_path}. "
                    "Please download it from the Google Cloud Console "
                    "and place it in the config directory."
                )
            
            logging.info(f"No valid credentials found for {email}, starting new OAuth flow")
            flow = InstalledAppFlow.from_client_secrets_file(
                credentials_path, SCOPES)
            creds = flow.run_local_server(port=0, access_type='offline', prompt='consent')
            logging.info(f"Successfully obtained new token for {email}")

        # Save the credentials for the next run
        logging.info(f"Saving token for {email} to {token_path}")
        try:
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
            logging.info(f"Successfully saved token for {email}")
        except Exception as e:
            logging.error(f"Failed to save token for {email}: {e}")

    # Verify the credentials are valid
    if not creds or not creds.valid:
        raise RuntimeError(f"Failed to obtain valid credentials for {email}")
        
    return creds

if __name__ == '__main__':
    import yaml
    
    # Load config to get user emails
    with open('config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    credentials_path = os.path.join('config', 'credentials.json')
    token_dir = os.path.join('config', 'tokens')
    
    # Authenticate each user
    for user in config['users']:
        print(f"Authenticating {user['email']}...")
        get_credentials(user['email'], credentials_path, token_dir)
        print(f"Successfully authenticated {user['email']}")

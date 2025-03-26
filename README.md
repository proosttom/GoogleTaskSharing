# Google Tasks Sync Service

A service that enables sharing and synchronization of Google Tasks lists between users. When changes are made to a shared task list by any user, the changes are automatically synchronized to all other users who have access to that list.

## Prerequisites

- Docker
- Visual Studio Code with Dev Containers extension (formerly Remote - Containers)
- Google Cloud Platform account

## Setup Instructions

### 1. Google Cloud Platform Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable the Google Tasks API for your project
4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - Select "Desktop app" as application type
   - Download the credentials file and rename it to `credentials.json`
   - Place it in the `config` directory

### 2. Development Environment Setup

1. Clone this repository
2. Install the "Dev Containers" extension in VS Code
3. Open the project in VS Code
4. When prompted, click "Reopen in Container" 
   - If not prompted: 
     1. Press F1 or Cmd+Shift+P
     2. Type "Dev Containers: Reopen in Container"
     3. Select this option
5. The container will automatically:
   - Set up Python 3.12
   - Install all project dependencies
   - Configure the development environment

### 3. Configuration

1. Copy `config/config.example.yaml` to `config/config.yaml`
2. Edit `config.yaml` to add the users and task lists to sync:
```yaml
users:
  - email: "user1@example.com"
    task_lists:
      - name: "shared_list_name"
        share_with:
          - "user2@example.com"
```

### 4. First Run Authentication

1. Run the authentication script:
```bash
python src/auth.py
```
2. Follow the OAuth flow in your browser for each user
3. Token files will be saved in the `config/tokens` directory

### 5. Running the Service

```bash
python src/main.py
```

The service will start monitoring the configured task lists and synchronize any changes between users.

### 6. GCP Deployment

#### A. Install Google Cloud SDK
```bash
# macOS with Homebrew
brew install --cask google-cloud-sdk

# Initialize and authenticate
gcloud init
gcloud auth login
```

#### B. Deploy to GCP e2-micro (Cost-effective Option)
```bash
# 1. Enable Compute Engine API
gcloud services enable compute.googleapis.com

# 2. Create VM and deploy application
./deploy/1_setup_gcp.sh your-project-id
./deploy/2_deploy.sh <instance-ip>  # IP will be shown after previous command

# 3. Verify deployment
gcloud compute ssh task-sync --zone=europe-west1-b -- 'sudo systemctl status tasksync'
```

#### C. Monitoring and Management

View logs in real-time:
```bash
# View service logs
gcloud compute ssh task-sync --zone=europe-west1-b -- 'sudo journalctl -u tasksync -f'

# Check service status
gcloud compute ssh task-sync --zone=europe-west1-b -- 'sudo systemctl status tasksync'

# Restart service
gcloud compute ssh task-sync --zone=europe-west1-b -- 'sudo systemctl restart tasksync'

# View system resources
gcloud compute ssh task-sync --zone=europe-west1-b -- 'top -b -n 1'
```

# Stop service
gcloud compute ssh task-sync --zone=europe-west1-b -- 'sudo systemctl stop tasksync'
```

Create backup:
```bash
./deploy/backup.sh <instance-ip>
```

Update application:
```bash
./deploy/update.sh <instance-ip>
```

### Costs
- e2-micro instance: ~$3-4/month
- Network egress: Free for first 1GB/month
- Total estimated cost: ~$4/month

## Development

### Dependency Management
The project uses a single source of truth for dependencies:
- `requirements.txt` contains all project dependencies with pinned versions
- `setup.py` reads from `requirements.txt` for package installation
- Docker and deployment scripts use `requirements.txt` for consistency
- Development environment setup uses `requirements.txt`

To add or update dependencies:
1. Update `requirements.txt` with the new package and version
2. The change will automatically propagate to all installation methods
3. Commit both `requirements.txt` and `setup.py` to version control

### Running Tests
Run the test suite:

```bash
pytest
```

## Project Structure

```
.
├── src/
│   ├── auth.py          # OAuth2 authentication and token management
│   ├── tasks_manager.py # Core task synchronization logic
│   └── main.py         # Service entry point and sync loop
├── config/
│   ├── config.example.yaml  # Configuration template
│   ├── credentials.json     # (to be added by user)
│   └── tokens/             # (auto-generated)
├── tests/
│   └── test_tasks_manager.py
└── .devcontainer/
    ├── devcontainer.json   # VS Code dev container config
    └── Dockerfile          # Python 3.12 with UV
```

## Dependencies

Main project dependencies:
- google-api-python-client==2.118.0
- google-auth-oauthlib==1.2.0
- google-auth-httplib2==0.2.0
- pyyaml==6.0.1
- pytest==8.0.0
- watchdog==3.0.0

## Architecture

The service consists of several components:
- Authentication Manager: Handles OAuth2 authentication and token refresh
- Task Sync Manager: Monitors and synchronizes tasks between users
- Change Detection: Uses the Google Tasks API to detect and propagate changes

## Troubleshooting

If dependencies are missing or not properly installed:
1. Ensure you are running inside the dev container (check VS Code's bottom-left corner)
2. If not in the container, use "Dev Containers: Reopen in Container" command
3. The container will automatically install all required dependencies

## License

MIT

import time
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import logging

def sync_tasks(source_manager, target_manager, list_name: str) -> None:
    """Sync tasks from source list to target list, handling completed tasks and duplicates."""
    source_tasks = source_manager.get_tasks(list_name)
    target_tasks = target_manager.get_tasks(list_name)

    logging.info(f"[{source_manager.email}] Syncing {len(source_tasks)} source tasks with {len(target_tasks)} target tasks")
    
    # Group tasks by title and due date to detect duplicates
    source_tasks_by_key = source_manager.tasks_by_key(source_tasks)
    target_tasks_by_key = target_manager.tasks_by_key(target_tasks)
    
    for key, content in source_tasks_by_key.items():
        # Handle completed tasks from source
        source_status = content[0].get('status')
        source_updated = content[0].get('updated')
        if source_status == 'completed':
            # Check in target list
            if key in target_tasks_by_key:
                target_status = target_tasks_by_key[key][0].get('status')
                target_updated = target_tasks_by_key[key][0].get('updated')
                if target_status == 'needsAction':
                    # Complete in target if more recent
                    if source_updated > target_updated:
                        target_manager.complete_task(list_name, target_tasks_by_key[key][0]['id'])
                elif target_status == 'completed':
                    # Skip
                    continue
            else:
                # Delete from source if completed and not present in target
                source_manager.delete_task(list_name, content[0]['id'])

        # Handle active tasks from source
        elif source_status == 'needsAction':
            # Check in target list
            if key in target_tasks_by_key:
                target_status = target_tasks_by_key[key][0].get('status')
                target_updated = target_tasks_by_key[key][0].get('updated')
                # Compare 'updated' update oldest to most recent
                if source_updated > target_updated:
                    # Create a new task if we are comparing to a completed task
                    if target_status == 'completed':
                        target_manager.create_task(list_name, content[0])
                    else:
                        target_manager.update_task(list_name, target_tasks_by_key[key][0]['id'], content[0])
            else:
                # Add to target
                target_manager.create_task(list_name, content[0])


class TasksManager:
    def __init__(self, credentials: Credentials, email: str):
        self.credentials = credentials
        self.email = email
        # Ensure credentials are fresh
        if self.credentials.expired and self.credentials.refresh_token:
            logging.info(f"Refreshing expired credentials for {email}")
            try:
                self.credentials.refresh(Request())
                logging.info(f"Successfully refreshed credentials for {email}")
            except Exception as e:
                logging.error(f"Failed to refresh credentials for {email}: {e}")
                raise

        # Build service with fresh credentials
        self.service = build('tasks', 'v1', credentials=self.credentials)

    def get_task_list_id(self, list_name: str) -> str:
        # List all task lists
        task_lists = self.service.tasklists().list().execute().get('items', [])
        
        # Find matching list
        for task_list in task_lists:
            if task_list['title'] == list_name:
                return task_list['id']

        # If list doesn't exist, create it
        new_list = self.service.tasklists().insert(body={'title': list_name}).execute()
        return new_list['id']

    def get_task_title(self, list_name: str, task_id: str) -> str:
        task = self.get_task(list_name, task_id)
        return task.get('title', '')

    def get_tasks(self, list_name: str) -> List[Dict]:
        list_id = self.get_task_list_id(list_name)
        tasks = []
        page_token = None
        while True:
            # list(tasklist, completedMax=None, completedMin=None, dueMax=None, dueMin=None, maxResults=None, pageToken=None, showAssigned=None, showCompleted=None, showDeleted=None, showHidden=None, updatedMin=None, x__xgafv=None)
            response = self.service.tasks().list(
                tasklist=list_id,
                pageToken=page_token,
                showCompleted=True,
                showHidden=True,
            ).execute()
            tasks.extend(response.get('items', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break
        return tasks

    def get_task(self, list_name: str, task_id: str) -> Dict:
        list_id = self.get_task_list_id(list_name)
        return self.service.tasks().get(
            tasklist=list_id,
            task=task_id
        ).execute()

    def create_task(self, list_name: str, task_data: Dict) -> Dict:
        list_id = self.get_task_list_id(list_name)
        logging.info(f"[{self.email}] Creating task '{task_data.get('title', '')}' in list '{list_name}'")
        task = self.service.tasks().insert(
            tasklist=list_id,
            body=task_data
        ).execute()


    def update_task(self, list_name: str, task_id: str, task_data: Dict) -> None:
        """Update an existing task, merging new data with existing data."""
        list_id = self.get_task_list_id(list_name)
        
        # Get existing task data
        old_data = self.get_task(list_name, task_id)
        
        # Compare and get merged data if changes exist
        merged_data = self._align_data(task_data, old_data)
        if merged_data:
            logging.info(f"[{self.email}] Updating task '{merged_data.get('title', '')}' in list '{list_name}'")
            self.service.tasks().update(
                tasklist=list_id,
                task=task_id,
                body=merged_data
        ).execute()

    def delete_task(self, list_name: str, task_id: str) -> None:
        # Delete a task from the specified list
        list_id = self.get_task_list_id(list_name)
        logging.info(f"[{self.email}] Deleting task '{self.get_task_title(list_name, task_id)}' from list '{list_name}'")
        self.service.tasks().delete(
            tasklist=list_id,
            task=task_id
        ).execute()

    def complete_task(self, list_name: str, task_id: str) -> None:
        """Mark a task as completed."""
        list_id = self.get_task_list_id(list_name)
        logging.info(f"[{self.email}] Marking task '{self.get_task_title(list_name, task_id)}' as completed in list '{list_name}'")
        self.service.tasks().patch(
            tasklist=list_id,
            task=task_id,
            body={'status': 'completed'}
        ).execute()

    @staticmethod
    def _align_data(source_data: Dict, target_data: Dict) -> Optional[Dict]:
        """Compare tasks and return updated data if there are changes in changeable fields.
        
        Args:
            source_data: Source task data
            target_data: Target task data to compare against
            
        Returns:
            Dict with updated data if changes exist, None if no changes
        """
        changeable_fields = {'due', 'notes', 'title', 'status'}
        
        # Start with copy of target data
        merged_data = target_data.copy()
        has_changes = False
        
        # Check each field that can be changed
        for field in changeable_fields:
            source_value = source_data.get(field)
            if source_value is not None and source_value != target_data.get(field):
                merged_data[field] = source_value
                has_changes = True
        
        return merged_data if has_changes else None

    def tasks_by_key(self, task_list: list) -> Dict[str, Dict]:
        tasks_by_key = {}
        for task in task_list:
            key = (task.get('title', ''))
            tasks_by_key[key] = tasks_by_key.get(key, []) + [task]
        return tasks_by_key

    @staticmethod
    def _tasks_differ(task1: Dict, task2: Dict) -> bool:
        """Compare two tasks to see if they have different content."""
        fields_to_compare = ['title', 'notes', 'status', 'due', 'completed']
        for field in fields_to_compare:
            if task1.get(field) != task2.get(field):
                return True
        return False

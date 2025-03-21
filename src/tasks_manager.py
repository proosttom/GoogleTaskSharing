import time
from typing import Dict, List, Optional
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
import logging

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
        self._task_list_cache = {}  # Cache for task list IDs
        self._tasks_cache = {}      # Cache for tasks
        self._cache_ttl = 60        # Cache TTL in seconds
        self._last_cache_time = {}  # Last cache update time

    def _is_cache_valid(self, cache_key: str) -> bool:
        return (cache_key in self._last_cache_time and 
                time.time() - self._last_cache_time[cache_key] < self._cache_ttl)

    def get_task_list_id(self, list_name: str) -> str:
        # Check cache first
        cache_key = f"list_{list_name}"
        if self._is_cache_valid(cache_key):
            return self._task_list_cache.get(cache_key)

        # Ensure credentials are fresh before making request
        if self.credentials.expired:
            logging.info(f"Refreshing expired credentials for {self.email} before tasklist request")
            self.credentials.refresh(Request())
            # Rebuild service with fresh credentials
            self.service = build('tasks', 'v1', credentials=self.credentials)

        # If not in cache or expired, fetch from API
        response = self.service.tasklists().list().execute()
        for task_list in response.get('items', []):
            if task_list['title'] == list_name:
                # Update cache
                self._task_list_cache[cache_key] = task_list['id']
                self._last_cache_time[cache_key] = time.time()
                return task_list['id']

        # If list doesn't exist, create it
        new_list = self.service.tasklists().insert(body={'title': list_name}).execute()
        list_id = new_list['id']
        # Update cache
        self._task_list_cache[cache_key] = list_id
        self._last_cache_time[cache_key] = time.time()
        return list_id

    def get_tasks(self, list_name: str) -> List[Dict]:
        list_id = self.get_task_list_id(list_name)
        cache_key = f"tasks_{list_id}"
        
        # Check cache first
        if self._is_cache_valid(cache_key):
            return self._tasks_cache.get(cache_key, [])

        # Ensure credentials are fresh before making request
        if self.credentials.expired:
            logging.info(f"Refreshing expired credentials for {self.email} before tasks request")
            self.credentials.refresh(Request())
            # Rebuild service with fresh credentials
            self.service = build('tasks', 'v1', credentials=self.credentials)

        # If not in cache or expired, fetch from API
        tasks = []
        page_token = None
        while True:
            response = self.service.tasks().list(
                tasklist=list_id,
                pageToken=page_token
            ).execute()
            tasks.extend(response.get('items', []))
            page_token = response.get('nextPageToken')
            if not page_token:
                break

        # Update cache
        self._tasks_cache[cache_key] = tasks
        self._last_cache_time[cache_key] = time.time()
        return tasks

    def create_task(self, list_name: str, task_data: Dict) -> Dict:
        # Ensure credentials are fresh before making request
        if self.credentials.expired:
            logging.info(f"Refreshing expired credentials for {self.email} before create task")
            self.credentials.refresh(Request())
            # Rebuild service with fresh credentials
            self.service = build('tasks', 'v1', credentials=self.credentials)

        list_id = self.get_task_list_id(list_name)
        task = self.service.tasks().insert(
            tasklist=list_id,
            body=task_data
        ).execute()
        # Invalidate tasks cache
        cache_key = f"tasks_{list_id}"
        self._last_cache_time.pop(cache_key, None)
        return task

    def update_task(self, list_name: str, task_id: str, task_data: Dict) -> Dict:
        # Ensure credentials are fresh before making request
        if self.credentials.expired:
            logging.info(f"Refreshing expired credentials for {self.email} before update task")
            self.credentials.refresh(Request())
            # Rebuild service with fresh credentials
            self.service = build('tasks', 'v1', credentials=self.credentials)

        list_id = self.get_task_list_id(list_name)
        task = self.service.tasks().update(
            tasklist=list_id,
            task=task_id,
            body=task_data
        ).execute()
        # Invalidate tasks cache
        cache_key = f"tasks_{list_id}"
        self._last_cache_time.pop(cache_key, None)
        return task

    def delete_task(self, list_name: str, task_id: str) -> None:
        # Ensure credentials are fresh before making request
        if self.credentials.expired:
            logging.info(f"Refreshing expired credentials for {self.email} before delete task")
            self.credentials.refresh(Request())
            # Rebuild service with fresh credentials
            self.service = build('tasks', 'v1', credentials=self.credentials)

        list_id = self.get_task_list_id(list_name)
        self.service.tasks().delete(
            tasklist=list_id,
            task=task_id
        ).execute()
        # Invalidate tasks cache
        cache_key = f"tasks_{list_id}"
        self._last_cache_time.pop(cache_key, None)

    def sync_task_list(self, source_list_name: str, target_manager) -> None:
        """Sync tasks from source list to target list, preventing duplicates."""
        source_tasks = self.get_tasks(source_list_name)
        target_tasks = target_manager.get_tasks(source_list_name)

        # Create lookup dictionaries
        target_tasks_by_id = {task['id']: task for task in target_tasks}
        target_tasks_by_content = {
            self._task_content_key(task): task 
            for task in target_tasks
        }

        # Track which target tasks have been processed
        processed_target_tasks = set()

        # Process each source task
        for source_task in source_tasks:
            task_id = source_task['id']
            content_key = self._task_content_key(source_task)

            # First try to find a match by ID
            if task_id in target_tasks_by_id:
                target_task = target_tasks_by_id[task_id]
                if self._tasks_differ(source_task, target_task):
                    target_manager.update_task(source_list_name, task_id, source_task)
                processed_target_tasks.add(task_id)
            
            # Then try to find a match by content
            elif content_key in target_tasks_by_content:
                target_task = target_tasks_by_content[content_key]
                target_id = target_task['id']
                if self._tasks_differ(source_task, target_task):
                    target_manager.update_task(source_list_name, target_id, source_task)
                processed_target_tasks.add(target_id)
            
            # If no match found, create new task
            else:
                # Create a new task without the source ID
                new_task = source_task.copy()
                new_task.pop('id', None)  # Remove source ID to let Google generate a new one
                target_manager.create_task(source_list_name, new_task)

        # Delete tasks that don't exist in source and weren't processed
        for target_task in target_tasks:
            target_id = target_task['id']
            if target_id not in processed_target_tasks:
                target_manager.delete_task(source_list_name, target_id)

    @staticmethod
    def _task_content_key(task: Dict) -> str:
        """Create a unique key for a task based on its content."""
        relevant_fields = ['title', 'notes', 'status', 'due']
        return '|'.join(str(task.get(field, '')) for field in relevant_fields)

    @staticmethod
    def _tasks_differ(task1: Dict, task2: Dict) -> bool:
        """Check if two tasks have different content."""
        relevant_fields = ['title', 'notes', 'status', 'due']
        return any(task1.get(field) != task2.get(field) for field in relevant_fields)

from googleapiclient.discovery import build
from datetime import datetime
import time
from typing import Dict, List, Optional

class TasksManager:
    def __init__(self, credentials, user_email):
        self.service = build('tasks', 'v1', credentials=credentials)
        self.user_email = user_email
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

        # If not in cache or expired, fetch from API
        task_lists = self.service.tasklists().list().execute()
        for task_list in task_lists.get('items', []):
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
        list_id = self.get_task_list_id(list_name)
        self.service.tasks().delete(
            tasklist=list_id,
            task=task_id
        ).execute()
        # Invalidate tasks cache
        cache_key = f"tasks_{list_id}"
        self._last_cache_time.pop(cache_key, None)

    def sync_task_list(self, source_list_name: str, target_manager) -> None:
        source_tasks = self.get_tasks(source_list_name)
        target_tasks = target_manager.get_tasks(source_list_name)

        # Create lookup dictionary for target tasks
        target_tasks_dict = {task['id']: task for task in target_tasks}

        for source_task in source_tasks:
            task_id = source_task['id']
            if task_id in target_tasks_dict:
                # Update existing task if different
                if self._tasks_differ(source_task, target_tasks_dict[task_id]):
                    target_manager.update_task(source_list_name, task_id, source_task)
            else:
                # Create new task
                target_manager.create_task(source_list_name, source_task)

        # Delete tasks that don't exist in source
        source_task_ids = {task['id'] for task in source_tasks}
        for target_task in target_tasks:
            if target_task['id'] not in source_task_ids:
                target_manager.delete_task(source_list_name, target_task['id'])

    @staticmethod
    def _tasks_differ(task1: Dict, task2: Dict) -> bool:
        relevant_fields = ['title', 'notes', 'status', 'due']
        return any(task1.get(field) != task2.get(field) for field in relevant_fields)

from googleapiclient.discovery import build
from datetime import datetime
import time

class TasksManager:
    def __init__(self, credentials, user_email):
        self.service = build('tasks', 'v1', credentials=credentials)
        self.user_email = user_email
        self.task_lists_cache = {}

    def get_task_list_id(self, list_name):
        """Get or create a task list with the given name."""
        if list_name in self.task_lists_cache:
            return self.task_lists_cache[list_name]

        task_lists = self.service.tasklists().list().execute()
        for task_list in task_lists.get('items', []):
            if task_list['title'] == list_name:
                self.task_lists_cache[list_name] = task_list['id']
                return task_list['id']

        # Create new task list if it doesn't exist
        new_list = self.service.tasklists().insert(body={
            'title': list_name
        }).execute()
        self.task_lists_cache[list_name] = new_list['id']
        return new_list['id']

    def get_tasks(self, list_name):
        """Get all tasks from a task list."""
        list_id = self.get_task_list_id(list_name)
        tasks = self.service.tasks().list(tasklist=list_id).execute()
        return tasks.get('items', [])

    def create_task(self, list_name, task_data):
        """Create a new task in the specified list."""
        list_id = self.get_task_list_id(list_name)
        return self.service.tasks().insert(
            tasklist=list_id,
            body=task_data
        ).execute()

    def update_task(self, list_name, task_id, task_data):
        """Update an existing task."""
        list_id = self.get_task_list_id(list_name)
        return self.service.tasks().update(
            tasklist=list_id,
            task=task_id,
            body=task_data
        ).execute()

    def delete_task(self, list_name, task_id):
        """Delete a task."""
        list_id = self.get_task_list_id(list_name)
        self.service.tasks().delete(
            tasklist=list_id,
            task=task_id
        ).execute()

    def sync_task_list(self, source_list_name, target_manager):
        """Sync tasks from this manager to target manager."""
        source_tasks = self.get_tasks(source_list_name)
        target_tasks = target_manager.get_tasks(source_list_name)

        # Create lookup dictionaries
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
    def _tasks_differ(task1, task2):
        """Compare two tasks to determine if they're different."""
        relevant_fields = ['title', 'notes', 'status', 'due']
        return any(task1.get(field) != task2.get(field) for field in relevant_fields)

import pytest
from unittest.mock import MagicMock, patch
from src.tasks_manager import TasksManager

@pytest.fixture
def mock_service():
    return MagicMock()

@pytest.fixture
def tasks_manager(mock_service):
    with patch('src.tasks_manager.build', return_value=mock_service):
        manager = TasksManager(MagicMock(), 'test@example.com')
        return manager

def test_get_task_list_id_existing(tasks_manager):
    # Mock the API response for existing task list
    tasks_manager.service.tasklists().list().execute.return_value = {
        'items': [{'id': 'list123', 'title': 'Test List'}]
    }

    list_id = tasks_manager.get_task_list_id('Test List')
    assert list_id == 'list123'

def test_get_task_list_id_create_new(tasks_manager):
    # Mock empty list response and new list creation
    tasks_manager.service.tasklists().list().execute.return_value = {'items': []}
    tasks_manager.service.tasklists().insert().execute.return_value = {
        'id': 'newlist123'
    }

    list_id = tasks_manager.get_task_list_id('New List')
    assert list_id == 'newlist123'

def test_sync_task_list(tasks_manager):
    source_tasks = [
        {'id': '1', 'title': 'Task 1', 'status': 'needsAction'},
        {'id': '2', 'title': 'Task 2', 'status': 'completed'}
    ]
    target_tasks = [
        {'id': '1', 'title': 'Task 1', 'status': 'completed'},  # Different status
        {'id': '3', 'title': 'Task 3', 'status': 'needsAction'}  # Should be deleted
    ]

    # Mock source tasks
    tasks_manager.get_tasks = MagicMock(return_value=source_tasks)

    # Create mock target manager
    target_manager = MagicMock()
    target_manager.get_tasks = MagicMock(return_value=target_tasks)

    # Perform sync
    tasks_manager.sync_task_list('Test List', target_manager)

    # Verify that task 1 was updated
    target_manager.update_task.assert_called_with('Test List', '1', source_tasks[0])

    # Verify that task 2 was created
    target_manager.create_task.assert_called_with('Test List', source_tasks[1])

    # Verify that task 3 was deleted
    target_manager.delete_task.assert_called_with('Test List', '3')

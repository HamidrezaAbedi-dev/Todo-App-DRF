from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.todos.models import Task


User = get_user_model()
TASKS_URL = "/todos/api/v1/tasks-list/"
STATS_URL = "/todos/api/v1/task/stats/"
BULK_COMPLETE_URL = "/todos/api/v1/task/bulk-complete/"
BULK_DELETE_URL = "/todos/api/v1/task/bulk-delete/"
TASK_HISTORY_URL = "/todos/api/v1/task/history/"
TASK_DETAIL_URL = "/todos/api/v1/task/{}/"


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="todo-owner@example.com",
        password="Strong#TodoPass123",
    )


@pytest.fixture
def authenticated_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def other_user(db):
    return User.objects.create_user(
        email="other-owner@example.com",
        password="Strong#TodoPass123",
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("method", "url", "data"),
    [
        ("get", TASKS_URL, None),
        ("post", TASKS_URL, {"title": "Anonymous task"}),
        ("get", STATS_URL, None),
        ("patch", BULK_COMPLETE_URL, {"ids": [1]}),
        ("delete", BULK_DELETE_URL, {"ids": [1]}),
        ("get", TASK_DETAIL_URL.format(1), None),
    ],
)
def test_task_endpoints_require_authentication(client, method, url, data):
    response = getattr(client, method)(url, data or {}, format="json")

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_list_retrieve_update_and_soft_delete_task(authenticated_client, user):
    create_response = authenticated_client.post(
        TASKS_URL,
        {
            "title": "Write API tests",
            "description": "Cover the task lifecycle",
            "priority": "high",
        },
        format="json",
    )

    assert create_response.status_code == 201
    task_id = create_response.data["id"]
    assert create_response.data["user"] == user.pk
    detail_url = TASK_DETAIL_URL.format(task_id)

    list_response = authenticated_client.get(TASKS_URL)
    assert list_response.status_code == 200
    assert list_response.data["total"] == 1
    assert list_response.data["results"][0]["id"] == task_id

    retrieve_response = authenticated_client.get(detail_url)
    assert retrieve_response.status_code == 200
    assert retrieve_response.data["title"] == "Write API tests"

    update_response = authenticated_client.patch(
        detail_url,
        {"title": "Write complete API tests", "is_completed": True},
        format="json",
    )
    assert update_response.status_code == 200
    assert update_response.data["is_completed"] is True

    replace_response = authenticated_client.put(
        detail_url,
        {
            "title": "Replace task",
            "description": "Complete replacement",
            "is_completed": False,
            "priority": "medium",
            "due_date": None,
        },
        format="json",
    )
    assert replace_response.status_code == 200
    assert replace_response.data["title"] == "Replace task"
    assert replace_response.data["is_completed"] is False

    delete_response = authenticated_client.delete(detail_url)
    assert delete_response.status_code == 204
    task = Task.objects.get(pk=task_id)
    assert task.deleted_at is not None
    assert authenticated_client.get(detail_url).status_code == 404
    assert authenticated_client.get(TASKS_URL).data["total"] == 0


@pytest.mark.django_db
def test_task_endpoints_only_expose_the_owners_tasks(
    authenticated_client, user, other_user
):
    own_task = Task.objects.create(user=user, title="Private task")
    other_task = Task.objects.create(user=other_user, title="Other task")

    list_response = authenticated_client.get(TASKS_URL)
    assert list_response.data["total"] == 1
    assert list_response.data["results"][0]["id"] == own_task.pk
    assert (
        authenticated_client.get(TASK_DETAIL_URL.format(other_task.pk)).status_code
        == 404
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "payload",
    [
        {"title": ""},
        {"title": "Invalid priority", "priority": "urgent"},
        {
            "title": "Past due",
            "due_date": (timezone.now() - timedelta(days=1)).isoformat(),
        },
    ],
)
def test_create_task_rejects_invalid_fields(authenticated_client, payload):
    response = authenticated_client.post(TASKS_URL, payload, format="json")

    assert response.status_code == 400
    assert Task.objects.count() == 0


@pytest.mark.django_db
def test_list_search_filter_ordering_and_pagination(authenticated_client, user):
    Task.objects.create(
        user=user,
        title="Buy groceries",
        priority="low",
        is_completed=False,
    )
    Task.objects.create(
        user=user,
        title="Read API docs",
        priority="high",
        is_completed=True,
    )
    Task.objects.create(
        user=user,
        title="More API practice",
        priority="high",
        is_completed=False,
    )
    Task.objects.create(
        user=user,
        title="Other API guide",
        priority="high",
        is_completed=False,
    )

    first_page = authenticated_client.get(
        TASKS_URL,
        {
            "search": "API",
            "priority": "high",
            "is_completed": "false",
            "ordering": "-title",
            "page_size": 1,
            "page": 1,
        },
    )

    assert first_page.status_code == 200
    assert first_page.data["total"] == 2
    assert first_page.data["pages"] == 2
    assert first_page.data["page"] == 1
    assert first_page.data["page_size"] == 1
    assert first_page.data["results"][0]["title"] == "Other API guide"
    assert first_page.data["links"]["next"] is not None

    second_page = authenticated_client.get(
        TASKS_URL,
        {
            "search": "API",
            "priority": "high",
            "is_completed": "false",
            "ordering": "-title",
            "page_size": 1,
            "page": 2,
        },
    )

    assert second_page.status_code == 200
    assert second_page.data["page"] == 2
    assert second_page.data["results"][0]["title"] == "More API practice"
    assert second_page.data["links"]["previous"] is not None
    assert second_page.data["links"]["next"] is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("query", "expected_code"),
    [
        ({"priority": "urgent"}, "INVALID_FILTER"),
        ({"ordering": "unknown_field"}, "INVALID_SORT_FIELD"),
    ],
)
def test_list_rejects_invalid_filter_and_ordering(
    authenticated_client, query, expected_code
):
    response = authenticated_client.get(TASKS_URL, query)

    assert response.status_code == 400
    assert response.data["error"]["code"] == expected_code


@pytest.mark.django_db
def test_bulk_complete_updates_all_requested_owned_tasks(authenticated_client, user):
    tasks = [
        Task.objects.create(user=user, title=f"Task {index}") for index in range(2)
    ]

    response = authenticated_client.patch(
        BULK_COMPLETE_URL,
        {"ids": [task.pk for task in tasks]},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["updated_count"] == 2
    assert not Task.objects.filter(
        pk__in=[task.pk for task in tasks],
        is_completed=False,
    ).exists()


@pytest.mark.django_db
def test_bulk_delete_soft_deletes_all_requested_owned_tasks(authenticated_client, user):
    tasks = [
        Task.objects.create(user=user, title=f"Task {index}") for index in range(2)
    ]
    task_ids = [task.pk for task in tasks]

    response = authenticated_client.delete(
        BULK_DELETE_URL,
        {"ids": task_ids},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["deleted_count"] == 2
    assert Task.objects.filter(pk__in=task_ids, deleted_at__isnull=False).count() == 2
    assert authenticated_client.get(TASKS_URL).data["total"] == 0


@pytest.mark.django_db
def test_deleted_task_history_only_lists_the_authenticated_users_deleted_tasks(
    authenticated_client, user, other_user
):
    deleted_task = Task.objects.create(
        user=user,
        title="Deleted task",
        deleted_at=timezone.now(),
    )
    Task.objects.create(user=user, title="Active task")
    Task.objects.create(
        user=other_user,
        title="Another user's deleted task",
        deleted_at=timezone.now(),
    )

    response = authenticated_client.get(TASK_HISTORY_URL)

    assert response.status_code == 200
    assert response.data["total"] == 1
    assert response.data["results"][0]["id"] == deleted_task.pk
    assert response.data["results"][0]["deleted_at"] is not None


@pytest.mark.django_db
def test_deleted_task_history_requires_authentication(client):
    response = client.get(TASK_HISTORY_URL)

    assert response.status_code == 401


@pytest.mark.django_db
def test_deleted_task_can_be_restored_by_its_owner(
    authenticated_client, user, other_user
):
    deleted_task = Task.objects.create(
        user=user,
        title="Restore me",
        deleted_at=timezone.now(),
    )
    foreign_task = Task.objects.create(
        user=other_user,
        title="Not yours",
        deleted_at=timezone.now(),
    )

    response = authenticated_client.post(
        TASK_DETAIL_URL.format(deleted_task.pk) + "restore/"
    )

    assert response.status_code == 200
    assert response.data["id"] == deleted_task.pk
    deleted_task.refresh_from_db()
    assert deleted_task.deleted_at is None
    assert (
        authenticated_client.post(
            TASK_DETAIL_URL.format(foreign_task.pk) + "restore/"
        ).status_code
        == 404
    )


@pytest.mark.django_db
@pytest.mark.parametrize("operation", ["complete", "delete"])
def test_bulk_operations_are_atomic_for_unknown_or_foreign_task(
    authenticated_client, user, other_user, operation
):
    own_task = Task.objects.create(user=user, title="Owned task")
    foreign_task = Task.objects.create(user=other_user, title="Foreign task")
    url = BULK_COMPLETE_URL if operation == "complete" else BULK_DELETE_URL
    method = "patch" if operation == "complete" else "delete"

    response = getattr(authenticated_client, method)(
        url,
        {"ids": [own_task.pk, foreign_task.pk]},
        format="json",
    )

    assert response.status_code == 400
    own_task.refresh_from_db()
    assert own_task.is_completed is False
    assert own_task.deleted_at is None


@pytest.mark.django_db
@pytest.mark.parametrize("operation", ["complete", "delete"])
def test_bulk_operations_reject_empty_and_duplicate_ids(
    authenticated_client, operation
):
    url = BULK_COMPLETE_URL if operation == "complete" else BULK_DELETE_URL
    method = "patch" if operation == "complete" else "delete"

    empty_response = getattr(authenticated_client, method)(
        url, {"ids": []}, format="json"
    )
    duplicate_response = getattr(authenticated_client, method)(
        url, {"ids": [1, 1]}, format="json"
    )

    assert empty_response.status_code == 400
    assert duplicate_response.status_code == 400


@pytest.mark.django_db
def test_task_statistics_count_active_tasks_and_overdue_items(
    authenticated_client, user
):
    Task.objects.create(user=user, title="Pending")
    Task.objects.create(user=user, title="Completed", is_completed=True)
    Task.objects.create(
        user=user,
        title="Overdue",
        due_date=timezone.now() - timedelta(days=1),
    )
    Task.objects.create(
        user=user,
        title="Deleted",
        deleted_at=timezone.now(),
    )

    response = authenticated_client.get(STATS_URL)

    assert response.status_code == 200
    assert response.data == {
        "total": 3,
        "completed": 1,
        "pending": 2,
        "overdue": 1,
    }

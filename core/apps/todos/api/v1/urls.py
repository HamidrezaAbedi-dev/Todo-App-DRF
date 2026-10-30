from django.urls import path
from . import views

app_name = "api-v1-todo"

urlpatterns = [
    path(
        "tasks-list/",
        views.TasksListCreateAPIView.as_view(),
        name="task-list-create",
    ),
    path(
        "task/<int:pk>/",
        views.TaskRetrieveUpdateDestroyAPIView.as_view(),
        name="task-detail",
    ),
    path(
        "task/history/",
        views.DeletedTasksListAPIView.as_view(),
        name="task-history",
    ),
    path(
        "task/<int:pk>/restore/",
        views.RestoreDeletedTaskAPIView.as_view(),
        name="task-restore",
    ),
    path(
        "task/bulk-complete/",
        views.BulkCompleteTasksAPIView.as_view(),
        name="task-bulk-complete",
    ),
    path(
        "task/bulk-delete/",
        views.BulkDeleteTasksAPIView.as_view(),
        name="task-bulk-delete",
    ),
    path(
        "task/stats/",
        views.TaskStatisticsAPIView.as_view(),
        name="task-statistics",
    ),
]
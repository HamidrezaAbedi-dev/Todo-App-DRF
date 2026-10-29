from django.db.models import Count, Q
from django.utils import timezone
from django.db import transaction
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.filters import SearchFilter
from rest_framework.generics import (
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
    GenericAPIView,
)
from rest_framework.permissions import IsAuthenticated

from apps.todos.models import Task
from apps.todos.api.utils.paginations import DefaultPagination
from apps.todos.api.utils.filters import (
    TaskFilter, StrictDjangoFilterBackend, StrictOrderingFilter,
)
from .serializers import (
    TasksListCreateSerializer, TaskDetailSerializer, BulkTaskSerializer
)


class TasksListCreateAPIView(ListCreateAPIView):
    """
    List the authenticated user's tasks and create new tasks.
    """
    serializer_class = TasksListCreateSerializer
    pagination_class = DefaultPagination
    permission_classes = [IsAuthenticated]
    filter_backends = [SearchFilter, StrictDjangoFilterBackend, StrictOrderingFilter,]
    search_fields = ["title", "description"]
    filterset_class = TaskFilter
    ordering_fields= ["created_date", "updated_date", "due_date", "priority", "title"]

    def get_queryset(self):
        # Return only tasks owned by the authenticated user.
        return Task.objects.filter(user=self.request.user, deleted_at__isnull=True)

    def perform_create(self, serializer):
        # Assign the authenticated user as the task owner.
        serializer.save(user=self.request.user)


class TaskRetrieveUpdateDestroyAPIView(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or soft-delete an active task owned by the user.
    """
    serializer_class = TaskDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):

        # Return active tasks owned by the authenticated user.
        return Task.objects.filter(
            user=self.request.user,
            deleted_at__isnull=True,
        )

    def perform_destroy(self, instance):

        # Mark the task as deleted instead of removing it from the database.
        now = timezone.now()
        instance.deleted_at = now
        instance.updated_date = now

        instance.save(
            update_fields=["deleted_at", "updated_date"],
        )


class TaskStatisticsAPIView(GenericAPIView):
    """
    Return statistics for the authenticated user's tasks.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):

        # Calculate and return task statistics.
        stats = Task.objects.filter(
            user=request.user,
            deleted_at__isnull=True,
        ).aggregate(
            total=Count("id"),
            completed=Count(
                "id",
                filter=Q(is_completed=True),
            ),
            pending=Count(
                "id",
                filter=Q(is_completed=False),
            ),
            overdue=Count(
                "id",
                filter=Q(
                    is_completed=False,
                    due_date__lt=timezone.now(),
                ),
            ),
        )

        return Response(stats)


# Bulk Operations

class BulkCompleteTasksAPIView(GenericAPIView):
    """
    Mark multiple tasks as completed for the authenticated user.
    """
    serializer_class = BulkTaskSerializer
    permission_classes = [IsAuthenticated]

    def patch(self, request, *args, **kwargs):
        """
        Validate ownership and complete all requested tasks.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_ids = serializer.validated_data["ids"]

        with transaction.atomic():
            tasks = Task.objects.filter(
                user=request.user,
                id__in=task_ids,
                deleted_at__isnull=True,
            )

            if tasks.count() != len(task_ids):
                raise serializers.ValidationError({
                    "ids": (
                        "One or more tasks were not found "
                        "or do not belong to you."
                    )
                })

            updated_count = tasks.update(
                is_completed=True,
                updated_date=timezone.now(),
            )

        return Response(
            {
                "message": "Tasks completed successfully.",
                "updated_count": updated_count,
            },
            status=status.HTTP_200_OK,
        )


class BulkDeleteTasksAPIView(GenericAPIView):
    """
    Soft-delete multiple active tasks owned by the authenticated user.
    """
    serializer_class = BulkTaskSerializer
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        
        # Soft-delete multiple active tasks owned by the user.
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        task_ids = serializer.validated_data["ids"]
        now = timezone.now()

        with transaction.atomic():
            tasks = Task.objects.filter(
                user=request.user,
                id__in=task_ids,
                deleted_at__isnull=True,
            )

            if tasks.count() != len(task_ids):
                raise serializers.ValidationError({
                    "ids": (
                        "One or more tasks were not found "
                        "or do not belong to you."
                    )
                })

            deleted_count = tasks.update(
                deleted_at=now,
                updated_date=now,
            )

        return Response(
            {
                "message": "Tasks deleted successfully.",
                "deleted_count": deleted_count,
            },
            status=status.HTTP_200_OK,
        )
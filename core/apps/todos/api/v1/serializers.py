
from django.utils import timezone
from rest_framework import serializers
from apps.todos.models import Task


class TasksListCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for listing tasks and creating new tasks.
    """
    user = serializers.ReadOnlyField(source="user.id")

    class Meta:
        model = Task
        fields = [
            "id",
            "user",
            "title",
            "description",
            "is_completed",
            "priority",
            "due_date",
        ]

    def validate_due_date(self, value):

        # Ensure the due date is not in the past.
        if value is not None and value < timezone.now():
            raise serializers.ValidationError(
                "The due date cannot be in the past."
            )

        return value


class TaskDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for retrieving, updating, and deleting task details.
    """
    user = serializers.ReadOnlyField(source="user.id")

    class Meta:
        model = Task
        fields = [
            "id",
            "user",
            "title",
            "description",
            "is_completed",
            "priority",
            "due_date",
            "created_date",
            "updated_date",
        ]
        read_only_fields = [
            "id",
            "user",
            "created_date",
            "updated_date",
        ]

    def validate_due_date(self, value):

        # Ensure the due date is not in the past.
        if value is not None and value < timezone.now():
            raise serializers.ValidationError(
                "The due date cannot be in the past."
            )

        return value


class BulkTaskSerializer(serializers.Serializer):
    """
    Validate task IDs for bulk operations.
    """
    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
        max_length=100,
    )

    def validate_ids(self, value):
        
        # Reject duplicate task IDs.
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Duplicate task IDs are not allowed."
            )

        return value
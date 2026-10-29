from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class PriorityTask(models.TextChoices):
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class Task(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="tasks",
    )
    title = models.CharField(max_length=100)
    description = models.CharField(
        max_length=1000, null=True, blank=True
    )
    is_completed = models.BooleanField(default=False)
    priority = models.CharField(
        max_length=6,
        choices=PriorityTask.choices,
        default=PriorityTask.MEDIUM,
    )
    due_date = models.DateTimeField(
        null=True,
        blank=True,
    )

    created_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True,)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "is_completed"]
            ),
        ]
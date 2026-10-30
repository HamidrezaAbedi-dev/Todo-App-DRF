from django.contrib import admin
from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "title",
        "user",
        "priority",
        "is_completed",
        "due_date",
        "created_date",
    )

    list_display_links = ("id", "title")

    list_filter = (
        "is_completed",
        "priority",
        "created_date",
        "due_date",
    )

    search_fields = (
        "title",
        "description",
        "user__email",
    )

    readonly_fields = (
        "created_date",
        "updated_date",
    )

    ordering = ("-created_date",)

    list_per_page = 25

    date_hierarchy = "created_date"

    autocomplete_fields = ("user",)

    fieldsets = (
        ("Task Information", {
            "fields": (
                "user",
                "title",
                "description",
                "priority",
            )
        }),
        ("Task Status", {
            "fields": (
                "is_completed",
                "due_date",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_date",
                "updated_date",
                "deleted_at",
            )
        }),
    )

    readonly_fields = (
        "created_date",
        "updated_date",
    )
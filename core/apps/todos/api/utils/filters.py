from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from apps.todos.api.utils.exceptions import CustomValidationException
from apps.todos.models import Task
import django_filters


class TaskFilter(django_filters.FilterSet):
    """Filter tasks by status, priority, and due date range."""

    due_date = django_filters.DateTimeFromToRangeFilter(
        field_name="due_date",
    )

    class Meta:
        model = Task
        fields = ["is_completed", "priority"]


class StrictDjangoFilterBackend(DjangoFilterBackend):
    """Reject invalid filter values instead of silently ignoring them."""

    def filter_queryset(self, request, queryset, view):
        filterset = self.get_filterset(request, queryset, view)

        if filterset is None:
            return queryset

        if not filterset.is_valid():
            raise CustomValidationException(
                code="INVALID_FILTER",
                message="Invalid filter value",
                details=filterset.errors,
            )

        return filterset.qs


class StrictOrderingFilter(OrderingFilter):
    """Reject unsupported ordering fields."""

    def get_ordering(self, request, queryset, view):
        ordering = request.query_params.get(self.ordering_param)

        if ordering:
            allowed_fields = set(
                self.get_valid_fields(queryset, view, {"request": request})
            )
            allowed_field_names = {field[0] for field in allowed_fields}

            requested_fields = [field.strip() for field in ordering.split(",")]

            for field in requested_fields:
                field_name = field.lstrip("-")

                if not field_name or field_name not in allowed_field_names:
                    raise CustomValidationException(
                        code="INVALID_SORT_FIELD",
                        message="Invalid sort field",
                    )

        return super().get_ordering(request, queryset, view)

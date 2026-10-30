from django.urls import path, include
from . import views

app_name = "todos"

urlpatterns = [
    # api based todos
    path("api/v1/", include("apps.todos.api.v1.urls")),
    # Template based todos
    path("", views.TodoTemplateView.as_view(), name="todo"),
]

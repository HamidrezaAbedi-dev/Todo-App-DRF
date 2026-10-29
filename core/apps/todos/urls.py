from django.urls import path, include

app_name = "todos"

urlpatterns = [
    # api based todos
    path("api/v1/", include("apps.todos.api.v1.urls"))
]
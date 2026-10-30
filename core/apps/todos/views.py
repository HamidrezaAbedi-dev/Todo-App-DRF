from django.views.generic import TemplateView


class TodoTemplateView(TemplateView):
    template_name = "todos/index.html"

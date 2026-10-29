
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class DefaultPagination(PageNumberPagination):
    """
    Customize pagination response format.
    """
    page_size = 10
    page_query_param = "page"
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):

        # Return paginated results with metadata and navigation links.
        return Response({
            "results": data,
            "page": self.page.number,
            "page_size": self.page.paginator.per_page,
            "total": self.page.paginator.count,
            "pages": self.page.paginator.num_pages,
            "links": {
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
        })

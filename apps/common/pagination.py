"""
Custom pagination classes for Cynosure API.
"""
from rest_framework.pagination import PageNumberPagination, CursorPagination
from rest_framework.response import Response


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination for most API endpoints.
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class LargeResultsSetPagination(PageNumberPagination):
    """
    Pagination for endpoints that may return large result sets.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class SmallResultsSetPagination(PageNumberPagination):
    """
    Pagination for endpoints with smaller result sets.
    """
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 50


class CauseListPagination(PageNumberPagination):
    """
    Custom pagination for cause lists.
    """
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'date_range': self.get_date_range(data),
            'results': data
        })
    
    def get_date_range(self, data):
        """Get the date range of the paginated results."""
        if not data:
            return None
        
        dates = [item.get('date') for item in data if item.get('date')]
        if dates:
            return {
                'start': min(dates),
                'end': max(dates)
            }
        return None


class NotificationCursorPagination(CursorPagination):
    """
    Cursor-based pagination for notifications (efficient for real-time feeds).
    """
    page_size = 20
    ordering = '-created_at'
    cursor_query_param = 'cursor'
    
    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class SearchResultsPagination(PageNumberPagination):
    """
    Pagination for search results.
    """
    page_size = 25
    page_size_query_param = 'page_size'
    max_page_size = 100
    
    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'query': self.request.query_params.get('q', ''),
            'results': data
        })

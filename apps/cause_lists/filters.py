"""
Filters for cause lists endpoints.
"""
import django_filters
from .models import CauseList


class CauseListFilter(django_filters.FilterSet):
    """Filter for CauseList model."""
    
    court = django_filters.UUIDFilter(field_name='court__id')
    judge = django_filters.UUIDFilter(field_name='judge__id')
    panel = django_filters.UUIDFilter(field_name='panel__id')
    date = django_filters.DateFilter(field_name='date')
    date_from = django_filters.DateFilter(field_name='date', lookup_expr='gte')
    date_to = django_filters.DateFilter(field_name='date', lookup_expr='lte')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    court_type = django_filters.CharFilter(field_name='court__court_type', lookup_expr='iexact')
    state = django_filters.CharFilter(field_name='court__state', lookup_expr='iexact')
    
    class Meta:
        model = CauseList
        fields = ['court', 'judge', 'panel', 'date', 'status', 'court_type', 'state']

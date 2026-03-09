"""
Filters for cases endpoints.
"""
import django_filters
from .models import Case


class CaseFilter(django_filters.FilterSet):
    """Filter for Case model."""
    
    court = django_filters.UUIDFilter(field_name='court__id')
    judge = django_filters.UUIDFilter(field_name='judge__id')
    case_type = django_filters.CharFilter(field_name='case_type', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    court_type = django_filters.CharFilter(field_name='court__court_type', lookup_expr='iexact')
    state = django_filters.CharFilter(field_name='court__state', lookup_expr='iexact')
    filing_date_from = django_filters.DateFilter(field_name='filing_date', lookup_expr='gte')
    filing_date_to = django_filters.DateFilter(field_name='filing_date', lookup_expr='lte')
    next_hearing_from = django_filters.DateFilter(field_name='next_hearing_date', lookup_expr='gte')
    next_hearing_to = django_filters.DateFilter(field_name='next_hearing_date', lookup_expr='lte')
    
    class Meta:
        model = Case
        fields = ['court', 'judge', 'case_type', 'status']

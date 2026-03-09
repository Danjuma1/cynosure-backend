"""
Filters for judges endpoints.
"""
import django_filters
from .models import Judge


class JudgeFilter(django_filters.FilterSet):
    """Filter for Judge model."""
    
    court = django_filters.UUIDFilter(field_name='court__id')
    division = django_filters.UUIDFilter(field_name='division__id')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    court_type = django_filters.CharFilter(field_name='court__court_type', lookup_expr='iexact')
    state = django_filters.CharFilter(field_name='court__state', lookup_expr='iexact')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    is_chief_judge = django_filters.BooleanFilter(field_name='is_chief_judge')
    
    class Meta:
        model = Judge
        fields = ['court', 'division', 'status', 'court_type', 'state', 'is_active', 'is_chief_judge']

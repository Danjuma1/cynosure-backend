"""
Filters for courts endpoints.
"""
import django_filters
from .models import Court, Division


class CourtFilter(django_filters.FilterSet):
    """Filter for Court model."""
    
    state = django_filters.CharFilter(field_name='state', lookup_expr='iexact')
    court_type = django_filters.CharFilter(field_name='court_type', lookup_expr='iexact')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    city = django_filters.CharFilter(field_name='city', lookup_expr='icontains')
    name = django_filters.CharFilter(field_name='name', lookup_expr='icontains')
    
    class Meta:
        model = Court
        fields = ['state', 'court_type', 'is_active', 'city', 'name']


class DivisionFilter(django_filters.FilterSet):
    """Filter for Division model."""
    
    court = django_filters.UUIDFilter(field_name='court__id')
    court_type = django_filters.CharFilter(field_name='court__court_type', lookup_expr='iexact')
    state = django_filters.CharFilter(field_name='court__state', lookup_expr='iexact')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    
    class Meta:
        model = Division
        fields = ['court', 'court_type', 'state', 'is_active']

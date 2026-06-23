import django_filters
from .models import BriefRequest


class BriefRequestFilter(django_filters.FilterSet):
    hearing_date = django_filters.DateFilter(field_name='hearing_date')
    hearing_date_from = django_filters.DateFilter(field_name='hearing_date', lookup_expr='gte')
    hearing_date_to = django_filters.DateFilter(field_name='hearing_date', lookup_expr='lte')
    court = django_filters.UUIDFilter(field_name='court__id')
    judge = django_filters.UUIDFilter(field_name='judge__id')
    brief_type = django_filters.CharFilter(field_name='brief_type')
    status = django_filters.CharFilter(field_name='status')
    requester = django_filters.UUIDFilter(field_name='requester__id')

    class Meta:
        model = BriefRequest
        fields = ['hearing_date', 'court', 'judge', 'brief_type', 'status', 'requester']

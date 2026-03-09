"""
Firms app - Law firm management.
"""
import uuid
from django.db import models
from rest_framework import viewsets, serializers
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from apps.common.models import BaseModel, TimeStampedModel
from apps.common.pagination import StandardResultsSetPagination
from apps.common.permissions import IsFirmMemberOrAdmin


# ============== MODELS ==============

class LawFirm(BaseModel):
    """Law firm profile."""
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    registration_number = models.CharField(max_length=100, blank=True)
    
    # Contact
    email = models.EmailField(blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True)
    
    # Address
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=50, blank=True)
    
    # Profile
    logo = models.ImageField(upload_to='firms/logos/', null=True, blank=True)
    description = models.TextField(blank=True)
    year_established = models.PositiveIntegerField(null=True, blank=True)
    specializations = models.JSONField(default=list, blank=True)
    
    # Admin
    admin = models.ForeignKey(
        'authentication.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='administered_firms'
    )
    
    # Status
    is_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class FirmMembership(TimeStampedModel):
    """Membership of users in law firms."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    firm = models.ForeignKey(LawFirm, on_delete=models.CASCADE, related_name='memberships')
    user = models.OneToOneField('authentication.User', on_delete=models.CASCADE, related_name='firm_membership')
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('partner', 'Partner'),
        ('associate', 'Associate'),
        ('paralegal', 'Paralegal'),
        ('staff', 'Staff'),
    ]
    
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='associate')
    title = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    joined_at = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = ['firm', 'user']
    
    def __str__(self):
        return f"{self.user.full_name} - {self.firm.name}"


# ============== SERIALIZERS ==============

class LawFirmListSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LawFirm
        fields = ['id', 'name', 'slug', 'city', 'state', 'logo', 'is_verified', 'member_count']
    
    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class LawFirmDetailSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    
    class Meta:
        model = LawFirm
        fields = [
            'id', 'name', 'slug', 'registration_number',
            'email', 'phone_number', 'website',
            'address', 'city', 'state',
            'logo', 'description', 'year_established', 'specializations',
            'is_verified', 'is_active', 'member_count',
            'created_at', 'updated_at',
        ]
    
    def get_member_count(self, obj):
        return obj.memberships.filter(is_active=True).count()


class FirmMembershipSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = FirmMembership
        fields = ['id', 'user', 'user_name', 'user_email', 'role', 'role_display', 'title', 'is_active', 'joined_at']


# ============== VIEWS ==============

class LawFirmViewSet(viewsets.ModelViewSet):
    """ViewSet for law firms."""
    queryset = LawFirm.objects.filter(is_deleted=False, is_active=True)
    pagination_class = StandardResultsSetPagination
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['city', 'state', 'is_verified']
    lookup_field = 'slug'
    
    def get_serializer_class(self):
        if self.action == 'list':
            return LawFirmListSerializer
        return LawFirmDetailSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return []
        return [IsFirmMemberOrAdmin()]


class FirmMembershipViewSet(viewsets.ModelViewSet):
    """ViewSet for firm memberships."""
    serializer_class = FirmMembershipSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'firm_membership') and user.firm_membership:
            return FirmMembership.objects.filter(firm=user.firm_membership.firm)
        return FirmMembership.objects.none()

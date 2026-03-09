"""
Custom permission classes for role-based access control.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsLawyer(BasePermission):
    """
    Permission for lawyer users.
    """
    message = "You must be a registered lawyer to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type == 'lawyer'
        )


class IsLawFirmAdmin(BasePermission):
    """
    Permission for law firm administrators.
    """
    message = "You must be a law firm administrator to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type == 'firm_admin'
        )


class IsRegistryStaff(BasePermission):
    """
    Permission for court registry staff.
    """
    message = "You must be registry staff to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type == 'registry_staff'
        )


class IsSuperAdmin(BasePermission):
    """
    Permission for super administrators.
    """
    message = "You must be a super administrator to access this resource."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.user_type == 'super_admin' or request.user.is_superuser)
        )


class IsRegistryOrAdmin(BasePermission):
    """
    Permission for registry staff or administrators.
    """
    message = "You must be registry staff or an administrator."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            request.user.user_type in ['registry_staff', 'super_admin'] or
            request.user.is_superuser
        )


class IsOwnerOrAdmin(BasePermission):
    """
    Object-level permission to only allow owners or admins to edit.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any authenticated user
        if request.method in SAFE_METHODS:
            return True
        
        # Admins can edit anything
        if request.user.user_type == 'super_admin' or request.user.is_superuser:
            return True
        
        # Check if user owns the object
        if hasattr(obj, 'user'):
            return obj.user == request.user
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        if hasattr(obj, 'created_by'):
            return obj.created_by == request.user
        
        return False


class IsFirmMemberOrAdmin(BasePermission):
    """
    Permission for law firm members or administrators.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Super admins always have access
        if request.user.user_type == 'super_admin' or request.user.is_superuser:
            return True
        
        # Check if user is a firm member
        return hasattr(request.user, 'firm_membership') and request.user.firm_membership is not None


class CanManageCourt(BasePermission):
    """
    Permission to manage court data.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return request.user.is_authenticated
        
        return (
            request.user.is_authenticated and 
            (request.user.user_type in ['registry_staff', 'super_admin'] or
             request.user.is_superuser)
        )


class CanUploadCauseList(BasePermission):
    """
    Permission to upload cause lists.
    """
    message = "Only registry staff or administrators can upload cause lists."
    
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and 
            (request.user.user_type in ['registry_staff', 'super_admin'] or
             request.user.is_superuser)
        )


class CanManageFilings(BasePermission):
    """
    Permission to manage e-filings.
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Registry staff and admins can manage all filings
        if request.user.user_type in ['registry_staff', 'super_admin']:
            return True
        
        # Lawyers can only create and view their own filings
        if request.method in ['GET', 'POST']:
            return request.user.user_type in ['lawyer', 'firm_admin']
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admins and registry can access all
        if request.user.user_type in ['registry_staff', 'super_admin']:
            return True
        
        # Lawyers can only access their own filings
        return obj.filed_by == request.user


class ReadOnly(BasePermission):
    """
    Read-only permission.
    """
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS


class IsAuthenticatedOrReadOnly(BasePermission):
    """
    Allow authenticated users full access, others read-only.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated

"""
Tests for courts app.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestCourtList:
    """Tests for court listing."""
    
    def test_list_courts_public(self, api_client, court):
        """Test listing courts without authentication."""
        url = reverse('court-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1
    
    def test_list_courts_filter_by_state(self, api_client, court):
        """Test filtering courts by state."""
        url = reverse('court-list')
        response = api_client.get(url, {'state': 'lagos'})
        
        assert response.status_code == status.HTTP_200_OK
        for item in response.data['results']:
            assert item['state'] == 'lagos'
    
    def test_list_courts_filter_by_type(self, api_client, court):
        """Test filtering courts by type."""
        url = reverse('court-list')
        response = api_client.get(url, {'court_type': 'federal_high'})
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCourtDetail:
    """Tests for court detail."""
    
    def test_get_court_detail(self, api_client, court):
        """Test getting court details."""
        url = reverse('court-detail', kwargs={'pk': court.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['name'] == court.name
    
    def test_get_nonexistent_court(self, api_client):
        """Test getting non-existent court returns 404."""
        import uuid
        url = reverse('court-detail', kwargs={'pk': uuid.uuid4()})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.django_db
class TestCourtFollow:
    """Tests for following courts."""
    
    def test_follow_court_authenticated(self, authenticated_client, court):
        """Test following a court when authenticated."""
        url = reverse('court-follow', kwargs={'pk': court.id})
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_200_OK
        court.refresh_from_db()
        assert court.follower_count == 1
    
    def test_follow_court_unauthenticated(self, api_client, court):
        """Test following a court without auth fails."""
        url = reverse('court-follow', kwargs={'pk': court.id})
        response = api_client.post(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_follow_court_twice(self, authenticated_client, court):
        """Test following a court twice returns error."""
        url = reverse('court-follow', kwargs={'pk': court.id})
        authenticated_client.post(url)
        response = authenticated_client.post(url)
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_unfollow_court(self, authenticated_client, court):
        """Test unfollowing a court."""
        follow_url = reverse('court-follow', kwargs={'pk': court.id})
        unfollow_url = reverse('court-unfollow', kwargs={'pk': court.id})
        
        authenticated_client.post(follow_url)
        response = authenticated_client.post(unfollow_url)
        
        assert response.status_code == status.HTTP_200_OK
        court.refresh_from_db()
        assert court.follower_count == 0


@pytest.mark.django_db
class TestCourtCreate:
    """Tests for court creation (admin only)."""
    
    def test_create_court_as_admin(self, admin_client):
        """Test creating a court as admin."""
        url = reverse('court-list')
        data = {
            'name': 'Test Court',
            'code': 'TC-001',
            'court_type': 'state_high',
            'state': 'lagos',
            'city': 'Lagos',
        }
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
    
    def test_create_court_as_regular_user(self, authenticated_client):
        """Test creating a court as regular user fails."""
        url = reverse('court-list')
        data = {
            'name': 'Test Court',
            'code': 'TC-001',
            'court_type': 'state_high',
            'state': 'lagos',
        }
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN

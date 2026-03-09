"""
Tests for authentication app.
"""
import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestUserRegistration:
    """Tests for user registration."""
    
    def test_register_user_success(self, api_client, user_data):
        """Test successful user registration."""
        url = reverse('signup')
        response = api_client.post(url, user_data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert 'access' in response.data['data']
        assert 'refresh' in response.data['data']
        assert response.data['data']['user']['email'] == user_data['email']
    
    def test_register_user_duplicate_email(self, api_client, user_data, user):
        """Test registration with existing email fails."""
        user_data['email'] = user.email
        url = reverse('signup')
        response = api_client.post(url, user_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_user_weak_password(self, api_client, user_data):
        """Test registration with weak password fails."""
        user_data['password'] = '123'
        user_data['password_confirm'] = '123'
        url = reverse('signup')
        response = api_client.post(url, user_data, format='json')
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestUserLogin:
    """Tests for user login."""
    
    def test_login_success(self, api_client, user):
        """Test successful login."""
        url = reverse('login')
        data = {
            'email': user.email,
            'password': 'TestPass123!',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data['data']
        assert 'refresh' in response.data['data']
    
    def test_login_invalid_credentials(self, api_client, user):
        """Test login with wrong password fails."""
        url = reverse('login')
        data = {
            'email': user.email,
            'password': 'wrongpassword',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_login_nonexistent_user(self, api_client):
        """Test login with non-existent email fails."""
        url = reverse('login')
        data = {
            'email': 'nonexistent@example.com',
            'password': 'password123',
        }
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestUserProfile:
    """Tests for user profile."""
    
    def test_get_profile_authenticated(self, authenticated_client, user):
        """Test getting profile when authenticated."""
        url = reverse('profile')
        response = authenticated_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['email'] == user.email
    
    def test_get_profile_unauthenticated(self, api_client):
        """Test getting profile when not authenticated fails."""
        url = reverse('profile')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_update_profile(self, authenticated_client, user):
        """Test updating profile."""
        url = reverse('profile')
        data = {
            'first_name': 'Updated',
            'bio': 'My new bio',
        }
        response = authenticated_client.put(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.first_name == 'Updated'


@pytest.mark.django_db
class TestTokenRefresh:
    """Tests for JWT token refresh."""
    
    def test_refresh_token_success(self, api_client, user):
        """Test successful token refresh."""
        from rest_framework_simplejwt.tokens import RefreshToken
        
        refresh = RefreshToken.for_user(user)
        url = reverse('token_refresh')
        data = {'refresh': str(refresh)}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        assert 'access' in response.data
    
    def test_refresh_token_invalid(self, api_client):
        """Test refresh with invalid token fails."""
        url = reverse('token_refresh')
        data = {'refresh': 'invalid-token'}
        response = api_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

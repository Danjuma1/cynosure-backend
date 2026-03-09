"""
Tests for cause lists app.
"""
import pytest
from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestCauseListList:
    """Tests for cause list listing."""
    
    def test_list_cause_lists_public(self, api_client, cause_list):
        """Test listing cause lists without authentication."""
        url = reverse('causelist-list')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_cause_lists_filter_by_court(self, api_client, cause_list):
        """Test filtering cause lists by court."""
        url = reverse('causelist-list')
        response = api_client.get(url, {'court': str(cause_list.court_id)})
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_list_cause_lists_filter_by_date(self, api_client, cause_list):
        """Test filtering cause lists by date."""
        url = reverse('causelist-list')
        response = api_client.get(url, {'date': str(cause_list.date)})
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCauseListDaily:
    """Tests for daily cause list summary."""
    
    def test_get_daily_summary(self, api_client, cause_list):
        """Test getting daily summary."""
        url = reverse('causelist-daily')
        response = api_client.get(url, {'date': str(date.today())})
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_daily_summary_default_date(self, api_client, cause_list):
        """Test getting daily summary without date parameter uses today."""
        url = reverse('causelist-daily')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCauseListByJudge:
    """Tests for cause lists by judge."""
    
    def test_get_by_judge(self, api_client, cause_list):
        """Test getting cause lists for a judge."""
        url = reverse('causelist-by-judge')
        response = api_client.get(url, {'judge_id': str(cause_list.judge_id)})
        
        assert response.status_code == status.HTTP_200_OK
    
    def test_get_by_judge_with_date_range(self, api_client, cause_list):
        """Test getting cause lists for a judge with date range."""
        url = reverse('causelist-by-judge')
        start_date = date.today()
        end_date = start_date + timedelta(days=14)
        response = api_client.get(url, {
            'judge_id': str(cause_list.judge_id),
            'start_date': str(start_date),
            'end_date': str(end_date),
        })
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCauseListFuture:
    """Tests for future cause lists."""
    
    def test_get_future_cause_lists(self, api_client, create_cause_list, court, judge):
        """Test getting future cause lists."""
        # Create a future cause list
        future_date = date.today() + timedelta(days=7)
        create_cause_list(court=court, judge=judge, list_date=future_date)
        
        url = reverse('causelist-future')
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestCauseListDetail:
    """Tests for cause list detail."""
    
    def test_get_cause_list_detail(self, api_client, cause_list):
        """Test getting cause list details."""
        url = reverse('causelist-detail', kwargs={'pk': cause_list.id})
        response = api_client.get(url)
        
        assert response.status_code == status.HTTP_200_OK
        assert str(response.data['data']['id']) == str(cause_list.id)


@pytest.mark.django_db
class TestCauseListStatusUpdate:
    """Tests for cause list status updates."""
    
    def test_update_status_as_registry(self, admin_client, cause_list):
        """Test updating cause list status as registry staff."""
        url = reverse('causelist-update-status', kwargs={'pk': cause_list.id})
        data = {
            'status': 'sitting',
            'status_note': 'Court is now in session',
        }
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_200_OK
        cause_list.refresh_from_db()
        assert cause_list.status == 'sitting'
    
    def test_update_status_as_regular_user(self, authenticated_client, cause_list):
        """Test updating cause list status as regular user fails."""
        url = reverse('causelist-update-status', kwargs={'pk': cause_list.id})
        data = {'status': 'sitting'}
        response = authenticated_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestCauseListEntry:
    """Tests for cause list entries."""
    
    def test_add_entry_to_cause_list(self, admin_client, cause_list):
        """Test adding an entry to a cause list."""
        url = reverse('causelistentry-list')
        data = {
            'cause_list': str(cause_list.id),
            'case_number': 'FHC/L/CS/456/2024',
            'parties': 'ABC Ltd v. XYZ Corp',
            'applicant': 'ABC Ltd',
            'respondent': 'XYZ Corp',
            'matter_type': 'Motion',
            'order_number': 1,
        }
        response = admin_client.post(url, data, format='json')
        
        assert response.status_code == status.HTTP_201_CREATED
        cause_list.refresh_from_db()
        assert cause_list.total_cases == 1

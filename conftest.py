"""
Pytest fixtures for Cynosure tests.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.fixture
def api_client():
    """Return an unauthenticated API client."""
    return APIClient()


@pytest.fixture
def user_data():
    """Return sample user data for registration."""
    return {
        'email': 'testuser@example.com',
        'password': 'TestPass123!',
        'first_name': 'Test',
        'last_name': 'User',
        'phone_number': '+2348012345678',
    }


@pytest.fixture
def create_user(db):
    """Factory fixture to create users."""
    def _create_user(
        email='test@example.com',
        password='TestPass123!',
        user_type='lawyer',
        **kwargs
    ):
        user = User.objects.create_user(
            email=email,
            password=password,
            user_type=user_type,
            **kwargs
        )
        return user
    return _create_user


@pytest.fixture
def user(create_user):
    """Return a standard test user."""
    return create_user(
        email='user@example.com',
        first_name='Test',
        last_name='User',
    )


@pytest.fixture
def admin_user(create_user):
    """Return a super admin user."""
    return create_user(
        email='admin@example.com',
        first_name='Admin',
        last_name='User',
        user_type='super_admin',
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def registry_user(create_user):
    """Return a registry staff user."""
    return create_user(
        email='registry@example.com',
        first_name='Registry',
        last_name='Staff',
        user_type='registry_staff',
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """Return an API client authenticated as a regular user."""
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """Return an API client authenticated as an admin."""
    refresh = RefreshToken.for_user(admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def create_court(db):
    """Factory fixture to create courts."""
    from apps.courts.models import Court
    
    def _create_court(
        name='Federal High Court, Lagos',
        code='FHC-LAG',
        court_type='federal_high',
        state='lagos',
        **kwargs
    ):
        court = Court.objects.create(
            name=name,
            code=code,
            court_type=court_type,
            state=state,
            **kwargs
        )
        return court
    return _create_court


@pytest.fixture
def court(create_court):
    """Return a sample court."""
    return create_court()


@pytest.fixture
def create_judge(db, court):
    """Factory fixture to create judges."""
    from apps.judges.models import Judge
    
    def _create_judge(
        first_name='John',
        last_name='Doe',
        title='HON_JUSTICE',
        court=court,
        **kwargs
    ):
        judge = Judge.objects.create(
            first_name=first_name,
            last_name=last_name,
            title=title,
            court=court,
            **kwargs
        )
        return judge
    return _create_judge


@pytest.fixture
def judge(create_judge):
    """Return a sample judge."""
    return create_judge()


@pytest.fixture
def create_case(db, court):
    """Factory fixture to create cases."""
    from apps.cases.models import Case
    
    def _create_case(
        case_number='FHC/L/CS/123/2024',
        parties='John Doe v. Jane Doe',
        court=court,
        case_type='civil',
        **kwargs
    ):
        case = Case.objects.create(
            case_number=case_number,
            parties=parties,
            court=court,
            case_type=case_type,
            **kwargs
        )
        return case
    return _create_case


@pytest.fixture
def case(create_case):
    """Return a sample case."""
    return create_case()


@pytest.fixture
def create_cause_list(db, court, judge):
    """Factory fixture to create cause lists."""
    from apps.cause_lists.models import CauseList
    from datetime import date
    
    def _create_cause_list(
        court=court,
        judge=judge,
        list_date=None,
        status='published',
        **kwargs
    ):
        cause_list = CauseList.objects.create(
            court=court,
            judge=judge,
            date=list_date or date.today(),
            status=status,
            **kwargs
        )
        return cause_list
    return _create_cause_list


@pytest.fixture
def cause_list(create_cause_list):
    """Return a sample cause list."""
    return create_cause_list()

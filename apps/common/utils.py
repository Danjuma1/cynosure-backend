"""
Common utility functions for Cynosure.
"""
import hashlib
import os
import random
import re
import string
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags


def generate_otp(length: int = 6) -> str:
    """Generate a random OTP code."""
    return ''.join(random.choices(string.digits, k=length))


def generate_unique_id(prefix: str = '') -> str:
    """Generate a unique identifier with optional prefix."""
    unique = uuid.uuid4().hex[:12]
    return f"{prefix}{unique}" if prefix else unique


def generate_case_number(court_code: str, year: int = None) -> str:
    """Generate a case number in Nigerian format."""
    if year is None:
        year = timezone.now().year
    
    # Get next sequence number from cache/db
    cache_key = f'case_seq_{court_code}_{year}'
    seq = cache.get(cache_key, 0) + 1
    cache.set(cache_key, seq, timeout=None)
    
    return f"{court_code}/{year}/{seq:05d}"


def normalize_case_number(case_number: str) -> str:
    """Normalize case number format for consistent searching."""
    # Remove extra spaces
    normalized = ' '.join(case_number.split())
    # Standardize separators
    normalized = re.sub(r'[\s/\\-]+', '/', normalized)
    return normalized.upper()


def normalize_party_name(name: str) -> str:
    """Normalize party names for consistent formatting."""
    if not name:
        return ''
    
    # Remove extra spaces
    name = ' '.join(name.split())
    # Title case but preserve legal abbreviations
    words = name.split()
    preserved = ['V.', 'VS', 'VS.', 'AND', '&', 'PLC', 'LTD', 'NIG', 'FRN', 'FCT']
    
    result = []
    for word in words:
        upper_word = word.upper()
        if upper_word in preserved:
            result.append(upper_word)
        else:
            result.append(word.title())
    
    return ' '.join(result)


def clean_html(html_content: str) -> str:
    """Strip HTML tags and clean text."""
    if not html_content:
        return ''
    
    # Remove HTML tags
    text = strip_tags(html_content)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text.strip()


def hash_file_content(file_content: bytes) -> str:
    """Generate SHA256 hash of file content."""
    return hashlib.sha256(file_content).hexdigest()


def get_file_extension(filename: str) -> str:
    """Get file extension in lowercase."""
    _, ext = os.path.splitext(filename)
    return ext.lower()


def validate_file_extension(filename: str) -> bool:
    """Check if file extension is allowed."""
    ext = get_file_extension(filename)
    return ext in settings.CYNOSURE_SETTINGS['ALLOWED_UPLOAD_EXTENSIONS']


def validate_file_size(file_size: int) -> bool:
    """Check if file size is within limits."""
    return file_size <= settings.CYNOSURE_SETTINGS['FILE_UPLOAD_MAX_SIZE']


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def send_notification_email(
    to_email: str,
    subject: str,
    template_name: str,
    context: Dict[str, Any],
    from_email: str = None
) -> bool:
    """Send a templated email notification."""
    try:
        from_email = from_email or settings.DEFAULT_FROM_EMAIL
        
        # Render HTML email
        html_message = render_to_string(f'emails/{template_name}.html', context)
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def get_nigerian_states() -> List[Dict[str, str]]:
    """Get list of Nigerian states."""
    return [
        {'code': 'AB', 'name': 'Abia'},
        {'code': 'AD', 'name': 'Adamawa'},
        {'code': 'AK', 'name': 'Akwa Ibom'},
        {'code': 'AN', 'name': 'Anambra'},
        {'code': 'BA', 'name': 'Bauchi'},
        {'code': 'BY', 'name': 'Bayelsa'},
        {'code': 'BE', 'name': 'Benue'},
        {'code': 'BO', 'name': 'Borno'},
        {'code': 'CR', 'name': 'Cross River'},
        {'code': 'DE', 'name': 'Delta'},
        {'code': 'EB', 'name': 'Ebonyi'},
        {'code': 'ED', 'name': 'Edo'},
        {'code': 'EK', 'name': 'Ekiti'},
        {'code': 'EN', 'name': 'Enugu'},
        {'code': 'FC', 'name': 'FCT Abuja'},
        {'code': 'GO', 'name': 'Gombe'},
        {'code': 'IM', 'name': 'Imo'},
        {'code': 'JI', 'name': 'Jigawa'},
        {'code': 'KD', 'name': 'Kaduna'},
        {'code': 'KN', 'name': 'Kano'},
        {'code': 'KT', 'name': 'Katsina'},
        {'code': 'KE', 'name': 'Kebbi'},
        {'code': 'KO', 'name': 'Kogi'},
        {'code': 'KW', 'name': 'Kwara'},
        {'code': 'LA', 'name': 'Lagos'},
        {'code': 'NA', 'name': 'Nasarawa'},
        {'code': 'NI', 'name': 'Niger'},
        {'code': 'OG', 'name': 'Ogun'},
        {'code': 'ON', 'name': 'Ondo'},
        {'code': 'OS', 'name': 'Osun'},
        {'code': 'OY', 'name': 'Oyo'},
        {'code': 'PL', 'name': 'Plateau'},
        {'code': 'RI', 'name': 'Rivers'},
        {'code': 'SO', 'name': 'Sokoto'},
        {'code': 'TA', 'name': 'Taraba'},
        {'code': 'YO', 'name': 'Yobe'},
        {'code': 'ZA', 'name': 'Zamfara'},
    ]


def get_court_types() -> List[Dict[str, str]]:
    """Get list of Nigerian court types."""
    return [
        {'code': 'SC', 'name': 'Supreme Court'},
        {'code': 'CA', 'name': 'Court of Appeal'},
        {'code': 'FHC', 'name': 'Federal High Court'},
        {'code': 'NIC', 'name': 'National Industrial Court'},
        {'code': 'SHC', 'name': 'State High Court'},
        {'code': 'FCT', 'name': 'FCT High Court'},
        {'code': 'SAC', 'name': 'Sharia Court of Appeal'},
        {'code': 'CCA', 'name': 'Customary Court of Appeal'},
        {'code': 'MC', 'name': 'Magistrate Court'},
        {'code': 'AC', 'name': 'Area Court'},
        {'code': 'CC', 'name': 'Customary Court'},
    ]


def parse_date_string(date_str: str) -> Optional[datetime]:
    """Parse various date string formats."""
    formats = [
        '%Y-%m-%d',
        '%d-%m-%Y',
        '%d/%m/%Y',
        '%Y/%m/%d',
        '%B %d, %Y',
        '%d %B %Y',
        '%d %b %Y',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            continue
    
    return None


def get_business_days(start_date: datetime, num_days: int) -> List[datetime]:
    """Get list of business days from start date."""
    business_days = []
    current = start_date
    
    while len(business_days) < num_days:
        if current.weekday() < 5:  # Monday = 0, Friday = 4
            business_days.append(current)
        current += timedelta(days=1)
    
    return business_days


def cache_key(*args) -> str:
    """Generate a cache key from arguments."""
    return ':'.join(str(arg) for arg in args)


def cache_result(key: str, timeout: int = 300):
    """Decorator to cache function results."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache_k = cache_key(key, *args, *kwargs.values())
            result = cache.get(cache_k)
            
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_k, result, timeout)
            
            return result
        return wrapper
    return decorator


def invalidate_cache_pattern(pattern: str):
    """Invalidate all cache keys matching pattern."""
    # This is a simplified version - in production,
    # use Redis SCAN + DEL for pattern matching
    pass


class CacheInvalidator:
    """Helper class for cache invalidation."""
    
    @staticmethod
    def invalidate_court(court_id: str):
        """Invalidate all caches related to a court."""
        patterns = [
            f'court:{court_id}',
            f'court_list',
            f'cause_list:court:{court_id}',
        ]
        for pattern in patterns:
            cache.delete_pattern(f'*{pattern}*')
    
    @staticmethod
    def invalidate_judge(judge_id: str):
        """Invalidate all caches related to a judge."""
        patterns = [
            f'judge:{judge_id}',
            f'cause_list:judge:{judge_id}',
        ]
        for pattern in patterns:
            cache.delete_pattern(f'*{pattern}*')
    
    @staticmethod
    def invalidate_cause_list(date: str = None, court_id: str = None):
        """Invalidate cause list caches."""
        patterns = ['cause_list']
        if date:
            patterns.append(f'cause_list:date:{date}')
        if court_id:
            patterns.append(f'cause_list:court:{court_id}')
        
        for pattern in patterns:
            cache.delete_pattern(f'*{pattern}*')

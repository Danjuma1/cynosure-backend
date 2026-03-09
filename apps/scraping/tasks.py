"""
Celery tasks for scraping cause lists.
"""
import logging
import hashlib
import tempfile
from datetime import date
from celery import shared_task
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name='apps.scraping.tasks.scrape_all_courts')
def scrape_all_courts():
    """Scrape cause lists from all configured courts."""
    from .models import ScraperConfig
    
    configs = ScraperConfig.objects.filter(is_active=True)
    results = []
    
    for config in configs:
        result = scrape_court.delay(str(config.id))
        results.append({'config_id': str(config.id), 'task_id': str(result.id)})
    
    logger.info(f"Started {len(results)} scraping tasks")
    return {'status': 'started', 'tasks': results}


@shared_task(name='apps.scraping.tasks.scrape_court', bind=True, max_retries=3)
def scrape_court(self, config_id: str):
    """Scrape cause lists for a specific court."""
    from .models import ScraperConfig, ScraperRun
    
    try:
        config = ScraperConfig.objects.get(id=config_id)
        
        # Create run record
        run = ScraperRun.objects.create(
            config=config,
            status='running',
            started_at=timezone.now()
        )
        
        try:
            # Determine scraper type
            if config.scraper_type == 'pdf':
                result = scrape_pdf_source(config, run)
            elif config.scraper_type == 'html':
                result = scrape_html_source(config, run)
            elif config.scraper_type == 'api':
                result = scrape_api_source(config, run)
            else:
                raise ValueError(f"Unknown scraper type: {config.scraper_type}")
            
            # Update run
            run.status = 'completed'
            run.completed_at = timezone.now()
            run.items_found = result.get('found', 0)
            run.items_created = result.get('created', 0)
            run.items_updated = result.get('updated', 0)
            run.save()
            
            # Update config stats
            config.last_run = timezone.now()
            config.last_success = timezone.now()
            config.total_runs += 1
            config.successful_runs += 1
            config.save()
            
            logger.info(f"Scraping completed for {config.name}")
            return {'status': 'success', 'run_id': str(run.id), **result}
            
        except Exception as e:
            run.status = 'failed'
            run.completed_at = timezone.now()
            run.error_message = str(e)
            run.save()
            
            config.last_run = timezone.now()
            config.total_runs += 1
            config.failed_runs += 1
            config.save()
            
            logger.error(f"Scraping failed for {config.name}: {e}")
            raise
            
    except Exception as e:
        logger.error(f"Scraping task failed: {e}")
        # Retry with exponential backoff
        retry_delay = settings.CYNOSURE_SETTINGS['SCRAPER_RETRY_DELAY'] * (2 ** self.request.retries)
        raise self.retry(exc=e, countdown=retry_delay)


def scrape_pdf_source(config, run):
    """Scrape PDF cause lists from source."""
    # Placeholder for PDF scraping logic
    # This would use libraries like PyPDF2, pdfplumber, or camelot
    logger.info(f"PDF scraping for {config.court.name}")
    return {'found': 0, 'created': 0, 'updated': 0}


def scrape_html_source(config, run):
    """Scrape HTML cause lists from website."""
    # Placeholder for HTML scraping logic
    # This would use requests + BeautifulSoup or Scrapy
    logger.info(f"HTML scraping for {config.court.name}")
    return {'found': 0, 'created': 0, 'updated': 0}


def scrape_api_source(config, run):
    """Fetch cause lists from API."""
    # Placeholder for API integration
    logger.info(f"API scraping for {config.court.name}")
    return {'found': 0, 'created': 0, 'updated': 0}


@shared_task(name='apps.scraping.tasks.parse_cause_list_pdf')
def parse_cause_list_pdf(cause_list_id: str):
    """Parse uploaded PDF cause list."""
    from apps.cause_lists.models import CauseList, CauseListEntry
    from .models import ParsedDocument
    from .parsers import PDFParser
    
    try:
        cause_list = CauseList.objects.get(id=cause_list_id)
        
        if not cause_list.pdf_file:
            logger.warning(f"No PDF file for cause list {cause_list_id}")
            return {'status': 'error', 'message': 'No PDF file'}
        
        # Calculate file hash
        file_content = cause_list.pdf_file.read()
        file_hash = hashlib.sha256(file_content).hexdigest()
        cause_list.pdf_file.seek(0)
        
        # Check for duplicate
        if ParsedDocument.objects.filter(file_hash=file_hash, status='imported').exists():
            logger.info(f"PDF already processed: {file_hash}")
            return {'status': 'duplicate', 'hash': file_hash}
        
        # Parse PDF
        parser = PDFParser()
        parsed_data = parser.parse(cause_list.pdf_file)
        
        # Create parsed document record
        parsed_doc = ParsedDocument.objects.create(
            source_file=cause_list.pdf_file,
            file_hash=file_hash,
            court=cause_list.court,
            date=cause_list.date,
            parsed_data=parsed_data,
            status='parsed'
        )
        
        # Create cause list entries from parsed data
        entries_created = 0
        for idx, entry_data in enumerate(parsed_data.get('entries', [])):
            CauseListEntry.objects.create(
                cause_list=cause_list,
                case_number=entry_data.get('case_number', ''),
                parties=entry_data.get('parties', ''),
                applicant=entry_data.get('applicant', ''),
                respondent=entry_data.get('respondent', ''),
                matter_type=entry_data.get('matter_type', ''),
                order_number=idx + 1,
                scheduled_time=entry_data.get('time'),
                courtroom=entry_data.get('courtroom', ''),
            )
            entries_created += 1
        
        # Update cause list
        cause_list.total_cases = entries_created
        cause_list.status = 'published'
        cause_list.save()
        
        # Mark parsed doc as imported
        parsed_doc.status = 'imported'
        parsed_doc.save()
        
        logger.info(f"Parsed {entries_created} entries from PDF for cause list {cause_list_id}")
        return {'status': 'success', 'entries': entries_created}
        
    except Exception as e:
        logger.error(f"Failed to parse PDF for cause list {cause_list_id}: {e}")
        return {'status': 'error', 'message': str(e)}


@shared_task(name='apps.scraping.tasks.retry_failed_scrapes')
def retry_failed_scrapes():
    """Retry failed scraping runs."""
    from .models import ScraperRun
    from datetime import timedelta
    
    cutoff = timezone.now() - timedelta(hours=6)
    
    failed_runs = ScraperRun.objects.filter(
        status='failed',
        created_at__gte=cutoff
    ).select_related('config')
    
    retried = 0
    for run in failed_runs:
        if run.config.is_active:
            scrape_court.delay(str(run.config.id))
            retried += 1
    
    logger.info(f"Retried {retried} failed scraping tasks")
    return {'status': 'success', 'retried': retried}


@shared_task(name='apps.scraping.tasks.cleanup_temp_files')
def cleanup_temp_files():
    """Clean up temporary files from scraping."""
    from .models import ParsedDocument
    from datetime import timedelta
    import os
    
    cutoff = timezone.now() - timedelta(days=7)
    
    # Delete old parsed documents
    old_docs = ParsedDocument.objects.filter(
        created_at__lt=cutoff,
        status__in=['imported', 'rejected']
    )
    
    deleted = 0
    for doc in old_docs:
        if doc.source_file:
            try:
                os.remove(doc.source_file.path)
            except OSError:
                pass
        doc.delete()
        deleted += 1
    
    logger.info(f"Cleaned up {deleted} old parsed documents")
    return {'status': 'success', 'deleted': deleted}

"""
PDF and document parsers for cause lists.
"""
import re
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Parser for PDF cause lists.
    Uses various patterns to extract case information.
    """
    
    # Common patterns for Nigerian cause lists
    CASE_NUMBER_PATTERNS = [
        r'([A-Z]+/\d+[A-Z]*/\d{4})',  # FHC/L/CS/123/2024
        r'(SUIT NO[.:\s]*[A-Z0-9/]+)',  # SUIT NO. ABC/123/2024
        r'(CA/[A-Z]+/\d+/\d{4})',  # CA/L/123/2024
        r'(SC[.:\s]*\d+/\d{4})',  # SC.123/2024
    ]
    
    PARTY_SEPARATOR_PATTERNS = [
        r'\s+[Vv][Ss]?[.]?\s+',  # v, vs, V, VS, v., vs.
        r'\s+AND\s+',
        r'\s+&\s+',
    ]
    
    def __init__(self, template_config: Dict = None):
        self.template_config = template_config or {}
    
    def parse(self, pdf_file) -> Dict:
        """
        Parse a PDF file and extract cause list data.
        """
        try:
            # Try pdfplumber first
            try:
                import pdfplumber
                return self._parse_with_pdfplumber(pdf_file)
            except ImportError:
                pass
            
            # Fallback to PyPDF2
            try:
                import PyPDF2
                return self._parse_with_pypdf2(pdf_file)
            except ImportError:
                pass
            
            logger.error("No PDF parsing library available")
            return {'entries': [], 'errors': ['No PDF parser available']}
            
        except Exception as e:
            logger.error(f"PDF parsing failed: {e}")
            return {'entries': [], 'errors': [str(e)]}
    
    def _parse_with_pdfplumber(self, pdf_file) -> Dict:
        """Parse using pdfplumber."""
        import pdfplumber
        
        entries = []
        errors = []
        
        with pdfplumber.open(pdf_file) as pdf:
            full_text = ''
            for page in pdf.pages:
                full_text += page.extract_text() or ''
        
        # Extract entries from text
        entries = self._extract_entries_from_text(full_text)
        
        return {
            'entries': entries,
            'errors': errors,
            'raw_text': full_text[:5000],  # First 5000 chars for debugging
        }
    
    def _parse_with_pypdf2(self, pdf_file) -> Dict:
        """Parse using PyPDF2."""
        import PyPDF2
        
        entries = []
        errors = []
        
        reader = PyPDF2.PdfReader(pdf_file)
        full_text = ''
        for page in reader.pages:
            full_text += page.extract_text() or ''
        
        entries = self._extract_entries_from_text(full_text)
        
        return {
            'entries': entries,
            'errors': errors,
            'raw_text': full_text[:5000],
        }
    
    def _extract_entries_from_text(self, text: str) -> List[Dict]:
        """Extract case entries from text."""
        entries = []
        
        # Find all case numbers
        case_numbers = []
        for pattern in self.CASE_NUMBER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            case_numbers.extend(matches)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_case_numbers = []
        for cn in case_numbers:
            if cn not in seen:
                seen.add(cn)
                unique_case_numbers.append(cn)
        
        # For each case number, try to extract surrounding context
        for case_num in unique_case_numbers:
            entry = self._extract_entry_context(text, case_num)
            if entry:
                entries.append(entry)
        
        return entries
    
    def _extract_entry_context(self, text: str, case_number: str) -> Optional[Dict]:
        """Extract context around a case number."""
        try:
            # Find position of case number
            pos = text.find(case_number)
            if pos == -1:
                return None
            
            # Get surrounding text (500 chars before and after)
            start = max(0, pos - 200)
            end = min(len(text), pos + len(case_number) + 500)
            context = text[start:end]
            
            # Try to extract parties
            parties = self._extract_parties(context)
            
            # Try to extract time
            time = self._extract_time(context)
            
            return {
                'case_number': case_number.strip(),
                'parties': parties,
                'applicant': self._extract_applicant(parties),
                'respondent': self._extract_respondent(parties),
                'time': time,
                'matter_type': self._extract_matter_type(context),
                'courtroom': self._extract_courtroom(context),
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract context for {case_number}: {e}")
            return None
    
    def _extract_parties(self, context: str) -> str:
        """Extract party names from context."""
        # Look for common party separators
        for pattern in self.PARTY_SEPARATOR_PATTERNS:
            match = re.search(r'([A-Z][A-Za-z\s.,&]+)' + pattern + r'([A-Z][A-Za-z\s.,&]+)', context)
            if match:
                return f"{match.group(1).strip()} v. {match.group(2).strip()}"
        return ''
    
    def _extract_applicant(self, parties: str) -> str:
        """Extract applicant from parties string."""
        if ' v. ' in parties:
            return parties.split(' v. ')[0].strip()
        return ''
    
    def _extract_respondent(self, parties: str) -> str:
        """Extract respondent from parties string."""
        if ' v. ' in parties:
            parts = parties.split(' v. ')
            if len(parts) > 1:
                return parts[1].strip()
        return ''
    
    def _extract_time(self, context: str) -> Optional[str]:
        """Extract time from context."""
        # Common time patterns
        patterns = [
            r'(\d{1,2}[:.]\d{2}\s*(?:am|pm|AM|PM))',
            r'(\d{1,2}[:.]\d{2})',
            r'(\d{1,2}\s*(?:am|pm|AM|PM))',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context)
            if match:
                return match.group(1)
        return None
    
    def _extract_matter_type(self, context: str) -> str:
        """Extract matter type from context."""
        matter_types = [
            'Motion', 'Hearing', 'Ruling', 'Judgment', 'Mention',
            'Trial', 'Appeal', 'Application', 'Petition',
        ]
        
        context_lower = context.lower()
        for mt in matter_types:
            if mt.lower() in context_lower:
                return mt
        return ''
    
    def _extract_courtroom(self, context: str) -> str:
        """Extract courtroom from context."""
        patterns = [
            r'Court(?:room)?\s*(\d+[A-Za-z]?)',
            r'Court\s*([A-Z])',
            r'Room\s*(\d+[A-Za-z]?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return f"Court {match.group(1)}"
        return ''


class HTMLParser:
    """Parser for HTML cause lists."""
    
    def parse(self, html_content: str) -> Dict:
        """Parse HTML content."""
        from bs4 import BeautifulSoup
        
        soup = BeautifulSoup(html_content, 'html.parser')
        entries = []
        
        # Look for table-based cause lists
        tables = soup.find_all('table')
        for table in tables:
            entries.extend(self._parse_table(table))
        
        return {'entries': entries, 'errors': []}
    
    def _parse_table(self, table) -> List[Dict]:
        """Parse a table for cause list entries."""
        entries = []
        rows = table.find_all('tr')
        
        for row in rows[1:]:  # Skip header
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 2:
                entry = {
                    'case_number': cells[0].get_text(strip=True) if len(cells) > 0 else '',
                    'parties': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                    'time': cells[2].get_text(strip=True) if len(cells) > 2 else '',
                }
                if entry['case_number']:
                    entries.append(entry)
        
        return entries

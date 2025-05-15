import requests
import time
from bs4 import BeautifulSoup
from config import MAX_TEXT_LENGTH

def scrape_website(url, timeout=10, max_retries=2):
    """Scrape website with retry logic and timeout"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive'
    }
    
    for attempt in range(max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if attempt < max_retries:
                # Wait before retrying (exponential backoff)
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
                continue
            return None

def extract_main_content(html_content):
    """Extract and clean main content from HTML, limiting length for efficiency"""
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove unnecessary elements
        for element in soup(["script", "style", "nav", "footer","aside", "iframe"]):
            element.decompose()
        
        # Get text content
        text = soup.get_text(separator=" ", strip=True)
        
        # Limit text length to reduce token usage
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
        
        return text
    except Exception as e:
        print(f"Error extracting content: {e}")
        # Fallback to a simpler extraction if BeautifulSoup fails
        if html_content:
            # Simple text extraction
            text = ' '.join(html_content.split())
            if len(text) > MAX_TEXT_LENGTH:
                return text[:MAX_TEXT_LENGTH]
            return text
        return ""
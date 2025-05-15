import os
import time
from config import CACHE_DIR, CACHE_EXPIRY_DAYS

def check_dependencies():
    """Check if all required libraries are installed"""
    required_libs = [
        "requests", "bs4", "ollama", "tqdm", "concurrent.futures"
    ]
    missing_libs = []
    
    for lib in required_libs:
        try:
            __import__(lib)
        except ImportError:
            missing_libs.append(lib)
    
    if missing_libs:
        print(f"Missing dependencies: {', '.join(missing_libs)}")
        print("Please install them using: pip install " + " ".join(missing_libs))
        return False
    return True

def validate_url(url):
    """Validate and normalize URL"""
    url = url.strip()
    if not url:
        return None
    
    # Basic URL validation
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    # Check for basic URL structure
    if '.' not in url.split('//')[1]:
        return None
    
    return url

def sanitize_filename(filename):
    """Sanitize filename to prevent directory traversal attacks"""
    # Remove path separators and other problematic characters
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '.', '..']
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Ensure the filename isn't empty after sanitization
    if not filename.strip('_'):
        filename = 'unnamed_file'
    
    return filename

def get_filename_from_url(url):
    """Generate a valid filename from a URL"""
    clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    
    if clean_url.endswith('/'):
        clean_url = clean_url[:-1]
    
    # Use sanitize function for safer filename generation    
    clean_url = sanitize_filename(clean_url)
        
    if len(clean_url) > 100:
        clean_url = clean_url[:100]
        
    return f"{clean_url}.txt"

def is_cache_expired(file_path):
    """Check if a cache file is expired based on its modification time"""
    if not os.path.exists(file_path):
        return True
    
    # Get file modification time
    mod_time = os.path.getmtime(file_path)
    current_time = time.time()
    
    # Check if file is older than expiry time
    if (current_time - mod_time) > (CACHE_EXPIRY_DAYS * 24 * 60 * 60):
        return True
    
    return False

def read_urls_from_file(filename):
    """Read URLs from a file with fallback encoding"""
    for encoding in ['utf-8', 'latin1', 'windows-1252']:
        try:
            with open(filename, 'r', encoding=encoding) as f:
                urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                # Filter out invalid URLs
                valid_urls = [url for url in urls if validate_url(url)]
                if len(valid_urls) < len(urls):
                    print(f"Warning: {len(urls) - len(valid_urls)} invalid URLs were skipped.")
                return valid_urls
        except UnicodeDecodeError:
            print(f"Encoding {encoding} failed, trying next...")
        except Exception as e:
            print(f"Error reading file with encoding {encoding}: {e}")
            break
    print("Failed to read file with known encodings.")
    return []
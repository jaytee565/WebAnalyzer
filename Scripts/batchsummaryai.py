import requests
from bs4 import BeautifulSoup
import ollama
import time
import os
import io
import concurrent.futures
import csv
from tqdm import tqdm

# Configuration variables
CATEGORIES = {
    "Technology": """
1. Target audience for the technology  
2. Key technologies or products featured  
3. Technical specifications or features highlighted  
4. Any release dates or version information  
5. Contact information  
""",
    "News": """
1. Publication dates of the articles  
2. Main headlines and topics covered (Include important personnel or location)  
3. Key facts from the articles  
4. Sources cited or referenced  
""",
    "Sports": """
1. Main sports or athletic activities featured  
2. Key teams, athletes, or events mentioned  
3. Recent results or upcoming events  
4. Fan or community engagement information  
5. Contact or venue information  
""",
    "E-commerce": """
1. Main product categories offered  
2. Any special deals or promotions  
3. Shipping or delivery information  
4. Return policy highlights  
5. Customer service contact details  
""",
    "Finance": """
1. Financial services or products offered  
2. Key market data or financial metrics mentioned  
3. Any investment advice or financial insights  
4. Regulatory information or compliance details  
5. Key Personnel/ Companies/ Countries involved
""",
    "Education": """
1. Educational programs or courses offered  
2. Faculty or instructor information  
3. Admission requirements or processes  
4. Academic resources available  
5. Contact information for the institution  
""",
    "Healthcare": """
1. Healthcare provider information  
2. Medical services or treatments offered
3. Patient resources or health tips  
4. Insurance or payment information  
5. Contact details for appointments  
""",
    "Travel": """
1. Destinations or locations featured  
2. Travel packages or services offered  
3. Pricing or booking information  
4. Travel tips or recommendations  
5. Contact information for bookings or inquiries  
""",
    "Food": """
1. Types of cuisine or food products featured  
2. Menu highlights or special dishes  
3. Pricing or ordering information  
4. Location and hours of operation  
5. Contact information for reservations  
""",
    "Entertainment": """
1. Types of entertainment offered  
2. Featured artists, performers, or content  
3. Event schedules or release dates  
4. Venue information or platform details  
5. Contact information for tickets or support  
""",
    "Default": """
1. A short analysis of the content displayed in bullet points (Do not be vague)  
2. Any important statistics or data points found within the content (e.g., visitor numbers, growth figures, or specific metrics mentioned)  
3. Display the Contact information  
"""
}

# Hard-coded base directory for saving files (preserved as requested)
BASE_SAVE_DIR = r"C:\Users\DESG ITAdmin\Extrext\Website Analysis"

# Configuration for performance
MAX_TEXT_LENGTH = 10000  # Limit text length to reduce token usage
MAX_WORKERS = 4  # Number of concurrent processes/threads
CACHE_DIR = os.path.join(BASE_SAVE_DIR, "_cache")  # Cache directory for category classifications
USE_STREAMING = False  # Set to False for faster non-streaming responses
MODEL_NAME = "llama3.2:1b"  # Model to use for inference
CACHE_EXPIRY_DAYS = 7  # Number of days before cache entries expire

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

def create_folders():
    """Create all necessary folders"""
    # Create the base directory if it doesn't exist
    if not os.path.exists(BASE_SAVE_DIR):
        os.makedirs(BASE_SAVE_DIR)
    
    # Create the cache directory
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
    
    # Create a folder for each category
    for category in CATEGORIES.keys():
        category_path = os.path.join(BASE_SAVE_DIR, category)
        if not os.path.exists(category_path):
            os.makedirs(category_path)

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
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
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

def check_category_cache(url):
    """Check if we already have a category classification for this URL in cache"""
    cache_file = os.path.join(CACHE_DIR, get_filename_from_url(url).replace('.txt', '_category.txt'))
    
    # Check if cache file exists and is not expired
    if os.path.exists(cache_file) and not is_cache_expired(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None
    return None

def save_category_cache(url, category):
    """Save category classification to cache"""
    cache_file = os.path.join(CACHE_DIR, get_filename_from_url(url).replace('.txt', '_category.txt'))
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(category)
    except Exception as e:
        print(f"Error saving to cache: {e}")
        pass

def detect_category(website_text, url):
    """Detect website category with caching"""
    # Check cache first
    cached_category = check_category_cache(url)
    if cached_category and cached_category in CATEGORIES:
        return cached_category
    
    # Use more content for better classification
    # Using 2000 characters instead of 1000 for better accuracy
    sample_text = website_text[:2000] if len(website_text) > 2000 else website_text
    
    categories = ", ".join(CATEGORIES.keys())
    message = f"""
As a classifier, identify the category of this website content.
Choose ONE from: {categories}
If no clear match, respond with: Default

Content:
{sample_text}

Response must be ONLY ONE WORD from the categories list.
"""
    try:
        messages = [
            {'role': 'system', 'content': "You are a website category classifier that responds with only one category name."},
            {'role': 'user', 'content': message}
        ]
        
        response = ollama.chat(
            model=MODEL_NAME,
            messages=messages
        )
        
        reply = response['message']['content'].strip()
        
        # Extract category name
        for category in CATEGORIES.keys():
            if category.lower() in reply.lower():
                # Cache the result
                save_category_cache(url, category)
                return category
        
        # Default fallback
        save_category_cache(url, 'Default')
        return 'Default'
    except Exception as e:
        print(f"Error detecting category: {e}")
        return 'Default'

def analyze_with_ollama(website_text, category, url):
    """Analyze website content using Ollama"""
    analysis_points = CATEGORIES.get(category, CATEGORIES['Default'])
    
    # Optimize by reducing prompt size but keeping structure
    prompt = f"""
Analyze this {category} category website based on:
{analysis_points}

Only use information from the provided text. Be concise and specific.
Website content:
{website_text}
"""
    try:
        messages = [
            {'role': 'system', 'content': "You are a website analyst focused on extracting key information efficiently."},
            {'role': 'user', 'content': prompt}
        ]
        
        # Capture the analysis
        analysis_buffer = io.StringIO()
        analysis_buffer.write(f"=========== Website Analysis: {url} ===========\n\n")
        analysis_buffer.write(f"Category: {category}\n\n")
        
        # Use streaming based on global setting
        if USE_STREAMING:
            # Streaming mode (slower but shows progress)
            stream = ollama.chat(
                model=MODEL_NAME,
                messages=messages,
                stream=True
            )
            
            for chunk in stream:
                if 'message' in chunk:
                    content = chunk['message']['content']
                    print(content, end='', flush=True)
                    analysis_buffer.write(content)
        else:
            # Non-streaming mode (faster)
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages
            )
            content = response['message']['content']
            analysis_buffer.write(content)
        
        # Add footer with timestamp
        analysis_buffer.write(f"\n\n=========== Analysis completed at {time.strftime('%Y-%m-%d %H:%M:%S')} ===========\n")
        analysis_buffer.write(f"Analyzed URL: {url}")
        
        return analysis_buffer.getvalue()
    except Exception as e:
        error_msg = f"\nError during analysis: {str(e)}"
        return error_msg

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

def save_analysis_to_file(analysis_text, category, url):
    """Save analysis to the appropriate category folder"""
    filename = get_filename_from_url(url)
    file_path = os.path.join(BASE_SAVE_DIR, category, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(analysis_text)
        return True, file_path
    except Exception as e:
        return False, str(e)

def process_url(url):
    """Process a single URL completely with optimized workflow"""
    # Validate URL
    validated_url = validate_url(url)
    if not validated_url:
        return url, False, "Invalid URL format"
    
    try:
        # Scrape with optimized settings
        html_content = scrape_website(validated_url)
        if not html_content:
            return validated_url, False, "Failed to scrape website"
        
        # Extract with length limits
        website_text = extract_main_content(html_content)
        if not website_text:
            return validated_url, False, "Failed to extract content"
        
        # Classify content
        category = detect_category(website_text, validated_url)
        print(f"URL: {validated_url} - Category: {category}")
        
        # Analyze content
        analysis_text = analyze_with_ollama(website_text, category, validated_url)
        
        # Save results
        success, result = save_analysis_to_file(analysis_text, category, validated_url)
        
        if success:
            return validated_url, True, result
        else:
            return validated_url, False, f"Failed to save: {result}"
    except Exception as e:
        return validated_url, False, f"Error: {str(e)}"

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


def batch_process_urls(urls):
    """Process multiple URLs with multithreading"""
    # Ensure folders exist
    create_folders()
    
    results = []
    processed_count = 0
    
    print(f"Starting batch processing of {len(urls)} URLs...")
    start_time = time.time()
    
    # Process URLs concurrently with a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(process_url, url): url for url in urls}
        
        # Use tqdm for progress tracking
        with tqdm(total=len(urls), desc="Processing websites") as pbar:
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        if result[1]:  # Success
                            processed_count += 1
                            tqdm.write(f"✅ {result[0]}")
                        else:
                            tqdm.write(f"❌ {result[0]}: {result[2]}")
                except Exception as exc:
                    tqdm.write(f"❌ {url}: {exc}")
                finally:
                    pbar.update(1)
    
    # Save results summary
    summary_file = os.path.join(BASE_SAVE_DIR, "batch_results.csv")
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Success', 'Result'])
        for result in results:
            writer.writerow(result)
    
    elapsed = time.time() - start_time
    print(f"\nProcessed {processed_count}/{len(urls)} URLs in {elapsed:.2f} seconds")
    print(f"Results saved to: {summary_file}")
    
    return results

def clean_cache():
    """Clean expired cache files"""
    if not os.path.exists(CACHE_DIR):
        return
    
    print("Cleaning expired cache files...")
    count = 0
    for filename in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, filename)
        if is_cache_expired(file_path):
            try:
                os.remove(file_path)
                count += 1
            except Exception as e:
                print(f"Error removing cache file {filename}: {e}")
    
    print(f"Removed {count} expired cache files.")

def main():
    # Check dependencies before starting
    if not check_dependencies():
        return
    
    print("Website Analyzer")
    print("===============")
    print("1. Analyze single URL")
    print("2. Batch process URLs from a file")
    print("3. Clean expired cache")
    
    choice = input("Select an option (1/2/3): ")
    
    # Define function scope variables
    global USE_STREAMING
    
    if choice == "1":
        # Single URL mode
        url = input("Enter the URL to analyze: ").strip()
        validated_url = validate_url(url)
        if not validated_url:
            print("Invalid URL format.")
            return
        
        start_time = time.time()
        create_folders()
        
        # Set streaming mode for single URL analysis
        USE_STREAMING = True
        
        html_content = scrape_website(validated_url)
        if not html_content:
            print("Failed to scrape the website.")
            return
        
        website_text = extract_main_content(html_content)
        if not website_text:
            print("Failed to extract content.")
            return
        
        try:
            # Detect category
            category = detect_category(website_text, validated_url)
            print(f"\n✔ Detected Category: {category}")
            
            # Analyze website
            analysis_text = analyze_with_ollama(website_text, category, validated_url)
            
            # Save analysis
            success, file_path = save_analysis_to_file(analysis_text, category, validated_url)
            if success:
                print(f"\nAnalysis saved to: {file_path}")
            
            print(f"\nExecution Time: {time.time() - start_time:.2f} seconds")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
    
    elif choice == "2":
        # Batch processing mode
        file_path = input("Enter the path to the file containing URLs: ")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        urls = read_urls_from_file(file_path)
        if not urls:
            print("No valid URLs found in the file.")
            return
        
        # Disable streaming for batch mode
        USE_STREAMING = False
        batch_process_urls(urls)
    
    elif choice == "3":
        # Clean cache mode
        clean_cache()
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
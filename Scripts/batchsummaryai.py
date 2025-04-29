import requests
from bs4 import BeautifulSoup
import ollama
import time
import os
import io
import concurrent.futures
import csv
from tqdm import tqdm
import random

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

# Hard-coded base directory for saving files
BASE_SAVE_DIR = r"C:\Users\DESG ITAdmin\Extrext\Website Analysis"

# Configuration for performance
MAX_TEXT_LENGTH = 10000  # Limit text length to reduce token usage
MAX_WORKERS = 4  # Number of concurrent processes/threads
CACHE_DIR = os.path.join(BASE_SAVE_DIR, "_cache")  # Cache directory for category classifications
USE_STREAMING = False  # Set to False for faster non-streaming responses
MODEL_NAME = "llama3.2"  # Model to use for inference

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
    except Exception:
        # Fallback to a simpler extraction if BeautifulSoup fails
        if html_content:
            # Simple text extraction
            text = ' '.join(html_content.split())
            if len(text) > MAX_TEXT_LENGTH:
                return text[:MAX_TEXT_LENGTH]
            return text
        return ""

def check_category_cache(url):
    """Check if we already have a category classification for this URL in cache"""
    cache_file = os.path.join(CACHE_DIR, get_filename_from_url(url).replace('.txt', '_category.txt'))
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except:
            pass
    return None

def save_category_cache(url, category):
    """Save category classification to cache"""
    cache_file = os.path.join(CACHE_DIR, get_filename_from_url(url).replace('.txt', '_category.txt'))
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(category)
    except:
        pass

def detect_category(website_text, url):
    """Detect website category with caching"""
    # Check cache first
    cached_category = check_category_cache(url)
    if cached_category and cached_category in CATEGORIES:
        return cached_category
    
    # Optimize prompt by using less text
    # Use only first 3000 characters for category detection to save tokens
    sample_text = website_text[:3000] if len(website_text) > 3000 else website_text
    
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

def get_filename_from_url(url):
    """Generate a valid filename from a URL"""
    clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
    
    if clean_url.endswith('/'):
        clean_url = clean_url[:-1]
        
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        clean_url = clean_url.replace(char, '_')
        
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
    url = url.strip()
    if not url:
        return None, False, "Empty URL"
    
    # Normalize URL
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    try:
        # Scrape with optimized settings
        html_content = scrape_website(url)
        if not html_content:
            return url, False, "Failed to scrape website"
        
        # Extract with length limits
        website_text = extract_main_content(html_content)
        if not website_text:
            return url, False, "Failed to extract content"
        
        # Classify content
        category = detect_category(website_text, url)
        print(f"URL: {url} - Category: {category}")
        
        # Analyze content
        analysis_text = analyze_with_ollama(website_text, category, url)
        
        # Save results
        success, result = save_analysis_to_file(analysis_text, category, url)
        
        if success:
            return url, True, result
        else:
            return url, False, f"Failed to save: {result}"
    except Exception as e:
        return url, False, f"Error: {str(e)}"

def read_urls_from_file(filename):
    """Read URLs from a file"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except Exception as e:
        print(f"Error reading file: {e}")
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

def main():
    print("Website Analyzer")
    print("===============")
    print("1. Analyze single URL")
    print("2. Batch process URLs from a file")
    choice = input("Select an option (1/2): ")
    
    if choice == "1":
        # Single URL mode
        url = input("Enter the URL to analyze: ").strip()
        if not url:
            print("No URL provided.")
            return
        
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        
        start_time = time.time()
        create_folders()
        
        html_content = scrape_website(url)
        if not html_content:
            print("Failed to scrape the website.")
            return
        
        website_text = extract_main_content(html_content)
        if not website_text:
            print("Failed to extract content.")
            return
        
        try:
            # Detect category
            category = detect_category(website_text, url)
            print(f"\n✔ Detected Category: {category}")
            
            # Analyze website
            global USE_STREAMING
            USE_STREAMING = True  # Use streaming for single URL for better UX
            analysis_text = analyze_with_ollama(website_text, category, url)
            
            # Save analysis
            success, file_path = save_analysis_to_file(analysis_text, category, url)
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
        
        global USE_STREAMING
        USE_STREAMING = False  # Disable streaming for batch mode
        batch_process_urls(urls)
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
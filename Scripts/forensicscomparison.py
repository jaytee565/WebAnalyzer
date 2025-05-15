import requests
from bs4 import BeautifulSoup
import ollama
import time
import os
import io
import concurrent.futures
import csv
import json
from tqdm import tqdm
from urllib.parse import urlparse

# Configuration variables
BASE_SAVE_DIR = r"C:\Users\DESG ITAdmin\Extrext\Digital Forensics Analysis"
MAX_TEXT_LENGTH = 15000  # Increased limit for better analysis
MAX_WORKERS = 4  # Number of concurrent processes/threads
CACHE_DIR = os.path.join(BASE_SAVE_DIR, "_cache")  # Cache directory
USE_STREAMING = False  # Set to False for faster non-streaming responses
MODEL_NAME = "llama3.2:1b"  # Model to use for inference
CACHE_EXPIRY_DAYS = 7  # Number of days before cache entries expire

# Digital forensics analysis prompts
SINGLE_ANALYSIS_PROMPT = """
Analyze this digital forensics product/service website and extract the following information:

1. Product/Service name and manufacturer/provider
2. Key features and capabilities of the product/service
3. Supported device types or data sources (mobile, computer, cloud, etc.)
4. Technical specifications (if available)
5. Target markets or use cases (law enforcement, corporate, etc.)
6. Any unique selling points or differentiators
7. Pricing information (if available)
8. Contact or support information

Only use information from the provided text. Be specific and provide actual details, not generic statements.
"""

COMPARISON_PROMPT = """
Compare the following digital forensics products/services based on their websites:

{website_data}

Create a detailed comparison that includes:
1. Common features shared across products
2. Key differences between products
3. Unique capabilities of each product
4. Target markets and use cases
5. Pricing differences (if available)
6. Technical capability differences

Format your response as both a structured comparison AND generate a CSV format at the end that shows the key differences in a table format.
The CSV should have rows for different feature categories and columns for each product.
"""

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
    
    # Create folders for single analyses and comparisons
    single_analysis_dir = os.path.join(BASE_SAVE_DIR, "Single_Analyses")
    comparison_dir = os.path.join(BASE_SAVE_DIR, "Comparisons")
    
    if not os.path.exists(single_analysis_dir):
        os.makedirs(single_analysis_dir)
    
    if not os.path.exists(comparison_dir):
        os.makedirs(comparison_dir)
        
    return single_analysis_dir, comparison_dir

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

def scrape_website(url, timeout=15, max_retries=3):
    """Scrape website with retry logic and timeout"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0'
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
                print(f"Retry {attempt+1}/{max_retries} after {sleep_time}s for {url}")
                time.sleep(sleep_time)
                continue
            print(f"Failed to scrape {url}: {e}")
            return None

def extract_main_content(html_content):
    """Extract and clean main content from HTML, limiting length for efficiency"""
    if not html_content:
        return ""
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract title for better context
        title = ""
        title_tag = soup.find('title')
        if title_tag:
            title = f"TITLE: {title_tag.get_text()}\n\n"
        
        # Remove unnecessary elements
        for element in soup(["script", "style", "iframe"]):
            element.decompose()
        
        # Try to focus on main content areas
        main_content = ""
        
        # Look for product sections, main content, etc.
        product_sections = soup.find_all(['div', 'section', 'article'], 
                                        class_=lambda c: c and any(term in str(c).lower() 
                                                               for term in ['product', 'feature', 'solution', 
                                                                           'service', 'forensic', 'main', 
                                                                           'content', 'description']))
        
        for section in product_sections:
            section_text = section.get_text(separator=" ", strip=True)
            if len(section_text) > 100:  # Only add substantial sections
                main_content += section_text + "\n\n"
        
        # If we couldn't find specific product sections, get all body text
        if not main_content:
            body = soup.find('body')
            if body:
                main_content = body.get_text(separator=" ", strip=True)
        
        # Combine title and main content
        text = title + main_content
        
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

def check_analysis_cache(url):
    """Check if we already have an analysis for this URL in cache"""
    cache_file = os.path.join(CACHE_DIR, get_filename_from_url(url).replace('.txt', '_analysis.txt'))
    
    # Check if cache file exists and is not expired
    if os.path.exists(cache_file) and not is_cache_expired(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading cache: {e}")
            return None
    return None

def save_analysis_cache(url, analysis_text):
    """Save analysis to cache"""
    cache_file = os.path.join(CACHE_DIR, get_filename_from_url(url).replace('.txt', '_analysis.txt'))
    try:
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(analysis_text)
    except Exception as e:
        print(f"Error saving to cache: {e}")
        pass

def analyze_with_ollama(website_text, url, is_comparison=False, websites_data=None):
    """Analyze website content using Ollama"""
    # Check cache for single analysis
    if not is_comparison:
        cached_analysis = check_analysis_cache(url)
        if cached_analysis:
            print(f"Using cached analysis for {url}")
            return cached_analysis
    
    try:
        if is_comparison:
            # Prepare comparison prompt
            prompt = COMPARISON_PROMPT.format(website_data=websites_data)
            system_message = "You are a digital forensics expert comparing different products and solutions."
        else:
            # Prepare single analysis prompt
            prompt = SINGLE_ANALYSIS_PROMPT + f"\n\nWebsite content:\n{website_text}"
            system_message = "You are a digital forensics expert analyzing products and services."
        
        messages = [
            {'role': 'system', 'content': system_message},
            {'role': 'user', 'content': prompt}
        ]
        
        # Capture the analysis
        analysis_buffer = io.StringIO()
        
        if not is_comparison:
            analysis_buffer.write(f"=========== Digital Forensics Product Analysis: {url} ===========\n\n")
        else:
            analysis_buffer.write(f"=========== Digital Forensics Products Comparison ===========\n\n")
        
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
        
        if not is_comparison:
            analysis_buffer.write(f"Analyzed URL: {url}")
            # Cache the single analysis result
            save_analysis_cache(url, analysis_buffer.getvalue())
        
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
    # Parse the URL to get the domain
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    
    # Remove www. if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    # Add part of the path if it exists (for better identification)
    path = parsed_url.path
    if path and path != '/':
        # Take only the first part of the path
        path_parts = path.strip('/').split('/')
        if path_parts[0]:
            domain = f"{domain}_{path_parts[0]}"
    
    # Sanitize the domain for a valid filename
    clean_name = sanitize_filename(domain)
    
    if len(clean_name) > 100:
        clean_name = clean_name[:100]
        
    return f"{clean_name}.txt"

def save_analysis_to_file(analysis_text, url, save_dir):
    """Save analysis to the specified directory"""
    filename = get_filename_from_url(url)
    file_path = os.path.join(save_dir, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(analysis_text)
        return True, file_path
    except Exception as e:
        return False, str(e)

def extract_csv_from_text(text):
    """Extract CSV content from the text response"""
    # Look for CSV format indicators
    csv_indicators = ["csv", "CSV", "table format", "comparison table"]
    
    # If no indicators, return empty
    if not any(indicator in text for indicator in csv_indicators):
        return None
    
    # Try to find CSV format content
    lines = text.split('\n')
    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)
    
    # Look for table-like content (lines with multiple commas)
    csv_lines = []
    in_csv_section = False
    
    for line in lines:
        # Check if we're in a csv section
        if any(f"```{ind}" in line.lower() for ind in ["csv", ""]) and not in_csv_section:
            in_csv_section = True
            continue
        elif "```" in line and in_csv_section:
            in_csv_section = False
            continue
        
        # Collect lines that look like CSV format
        if in_csv_section or line.count(',') >= 2:
            # Clean the line
            clean_line = line.strip()
            if clean_line and not clean_line.startswith('|') and ',' in clean_line:
                csv_lines.append(clean_line)
    
    # If no CSV found, try to create one from the comparison
    if not csv_lines:
        # This is a fallback that tries to construct a simple CSV
        product_names = []
        features = {}
        
        # Look for product names and features
        product_section = False
        current_feature = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Look for product names
            if "Product:" in line or "Product Name:" in line:
                parts = line.split(":", 1)
                if len(parts) > 1:
                    product_name = parts[1].strip()
                    if product_name and product_name not in product_names:
                        product_names.append(product_name)
            
            # Look for feature sections
            if current_feature is None:
                for feature in ["Features", "Capabilities", "Supported Devices", "Target Market", "Pricing"]:
                    if feature in line and ":" in line:
                        current_feature = feature
                        features[current_feature] = {}
                        break
            elif line.startswith("- ") or line.startswith("* "):
                # This is a feature item
                if ":" in line:
                    product, value = line[2:].split(":", 1)
                    product = product.strip()
                    if product in product_names:
                        features[current_feature][product] = value.strip()
            else:
                # Check if we've moved to a new section
                current_feature = None
        
        # Create CSV from extracted data
        if product_names and features:
            # Write header
            header = ["Feature"] + product_names
            csv_writer.writerow(header)
            
            # Write feature rows
            for feature, products in features.items():
                row = [feature]
                for product in product_names:
                    row.append(products.get(product, ""))
                csv_writer.writerow(row)
            
            csv_lines = csv_buffer.getvalue().split('\n')
    
    # Create CSV content
    if csv_lines:
        return '\n'.join(csv_lines)
    
    return None

def save_comparison_csv(comparison_text, comparison_dir):
    """Extract and save CSV from comparison analysis"""
    csv_content = extract_csv_from_text(comparison_text)
    
    if not csv_content:
        # If we couldn't extract CSV, generate a simple one with a message
        csv_content = "Note,Details\nNo CSV format detected,Please check the text analysis for detailed comparison."
    
    # Generate timestamp for unique filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    csv_file_path = os.path.join(comparison_dir, f"comparison_{timestamp}.csv")
    
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as f:
            f.write(csv_content)
        return True, csv_file_path
    except Exception as e:
        return False, str(e)

def process_url(url, single_analysis_dir):
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
        
        # Analyze content
        analysis_text = analyze_with_ollama(website_text, validated_url)
        
        # Save results
        success, result = save_analysis_to_file(analysis_text, validated_url, single_analysis_dir)
        
        if success:
            # Return URL and extracted content for potential comparison use
            return validated_url, True, {"path": result, "content": analysis_text, "text": website_text}
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

def batch_process_urls(urls, single_analysis_dir, comparison_dir):
    """Process multiple URLs with multithreading and create comparison"""
    results = []
    processed_count = 0
    successful_analyses = []
    
    print(f"Starting batch processing of {len(urls)} URLs...")
    start_time = time.time()
    
    # Process URLs concurrently with a thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(process_url, url, single_analysis_dir): url for url in urls}
        
        # Use tqdm for progress tracking
        with tqdm(total=len(urls), desc="Processing websites") as pbar:
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    result = future.result()
                    if result:
                        url, success, data = result
                        results.append(result)
                        if success:
                            processed_count += 1
                            successful_analyses.append(data)
                            tqdm.write(f"✅ {url}")
                        else:
                            tqdm.write(f"❌ {url}: {data}")
                except Exception as exc:
                    tqdm.write(f"❌ {url}: {exc}")
                finally:
                    pbar.update(1)
    
    # Create comparison if we have multiple successful analyses
    if len(successful_analyses) >= 2:
        print("\nCreating comparison analysis...")
        
        # Prepare website data for comparison
        websites_data = ""
        for i, data in enumerate(successful_analyses):
            # Extract domain name for easier reference
            domain = urlparse(urls[i]).netloc
            if domain.startswith('www.'):
                domain = domain[4:]
                
            websites_data += f"Website {i+1} ({domain}):\n{data['content']}\n\n"
        
        # Generate comparison analysis
        comparison_text = analyze_with_ollama(None, None, is_comparison=True, websites_data=websites_data)
        
        # Save comparison text file
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        comparison_file = os.path.join(comparison_dir, f"comparison_{timestamp}.txt")
        with open(comparison_file, 'w', encoding='utf-8') as f:
            f.write(comparison_text)
        
        # Extract and save CSV separately
        csv_success, csv_path = save_comparison_csv(comparison_text, comparison_dir)
        
        if csv_success:
            print(f"Comparison CSV saved to: {csv_path}")
        else:
            print(f"Failed to save comparison CSV: {csv_path}")
            
        print(f"Comparison analysis saved to: {comparison_file}")
    
    elapsed = time.time() - start_time
    print(f"\nProcessed {processed_count}/{len(urls)} URLs in {elapsed:.2f} seconds")
    
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
    
    print("Digital Forensics Website Analyzer")
    print("==================================")
    print("1. Analyze single digital forensics product/service")
    print("2. Compare multiple digital forensics products/services from a file")
    print("3. Clean expired cache")
    
    choice = input("Select an option (1/2/3): ")
    
    # Create necessary folders
    single_analysis_dir, comparison_dir = create_folders()
    
    # Define function scope variables
    global USE_STREAMING
    
    if choice == "1":
        # Single URL mode
        url = input("Enter the URL of the digital forensics product/service to analyze: ").strip()
        validated_url = validate_url(url)
        if not validated_url:
            print("Invalid URL format.")
            return
        
        start_time = time.time()
        
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
            # Analyze website
            print("\nAnalyzing digital forensics product/service...")
            analysis_text = analyze_with_ollama(website_text, validated_url)
            
            # Save analysis
            success, file_path = save_analysis_to_file(analysis_text, validated_url, single_analysis_dir)
            if success:
                print(f"\nAnalysis saved to: {file_path}")
            
            print(f"\nExecution Time: {time.time() - start_time:.2f} seconds")
        except KeyboardInterrupt:
            print("\nOperation cancelled.")
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
    
    elif choice == "2":
        # Batch processing mode for comparison
        file_path = input("Enter the path to the file containing URLs of digital forensics products/services: ")
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            return
        
        urls = read_urls_from_file(file_path)
        if not urls:
            print("No valid URLs found in the file.")
            return
        
        if len(urls) < 2:
            print("At least 2 URLs are needed for comparison. Please add more URLs to your file.")
            return
        
        # Disable streaming for batch mode
        USE_STREAMING = False
        batch_process_urls(urls, single_analysis_dir, comparison_dir)
    
    elif choice == "3":
        # Clean cache mode
        clean_cache()
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
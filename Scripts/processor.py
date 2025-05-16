import time
import concurrent.futures
from tqdm import tqdm
from config import USE_STREAMING
from scraper import scrape_website, extract_main_content
from analyzer import detect_category, analyze_with_ollama, text_to_csv
from file_handler import save_analysis_to_file, save_batch_results, create_folders
from utils import validate_url

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

def batch_process_urls(urls):
    """Process multiple URLs with multithreading"""
    from config import MAX_WORKERS
    
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
    summary_file = save_batch_results(results)
    
    elapsed = time.time() - start_time
    print(f"\nProcessed {processed_count}/{len(urls)} URLs in {elapsed:.2f} seconds")
    print(f"Results saved to: {summary_file}")
    
    return results

def process_single_url(url):
    """Process a single URL with streaming output"""
    start_time = time.time()
    create_folders()
    
    try:
        # Validate URL
        validated_url = validate_url(url)
        if not validated_url:
            print("Invalid URL format.")
            return False
        
        # Scrape website
        print("Scraping website...")
        html_content = scrape_website(validated_url)
        if not html_content:
            print("Failed to scrape the website.")
            return False
        
        # Extract content
        print("Extracting main content...")
        website_text = extract_main_content(html_content)
        if not website_text:
            print("Failed to extract content.")
            return False
        
        # Detect category
        print("Detecting category...")
        category = detect_category(website_text, validated_url)
        print(f"\n✔ Detected Category: {category}")
        
        # Analyze website
        print(f"Analyzing website as {category}...")
        analysis_text = analyze_with_ollama(website_text, category, validated_url)
        
        # Save analysis
        print("Saving analysis...")
        success, file_path = save_analysis_to_file(analysis_text, category, validated_url)
        if success:
            print(f"\nAnalysis saved to: {file_path}")
        
        print(f"\nExecution Time: {time.time() - start_time:.2f} seconds")
        return success
        
    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        return False
    except Exception as e:
        print(f"\nAn error occurred: {str(e)}")
        return False
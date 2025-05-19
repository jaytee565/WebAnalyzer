import os
from config import BASE_SAVE_DIR, CACHE_DIR
from utils import is_cache_expired
from export_csv import process_txt_folder_to_csv

def create_folders():
    """Create base and cache directories"""
    from config import CATEGORIES

    if not os.path.exists(BASE_SAVE_DIR):
        os.makedirs(BASE_SAVE_DIR)

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # Create category folders
    for category in CATEGORIES.keys():
        category_dir = os.path.join(BASE_SAVE_DIR, category)
        if not os.path.exists(category_dir):
            os.makedirs(category_dir)

def save_analysis_to_file(analysis_text, category, url):
    """Save analysis to a file in the category folder"""
    # Create category folder if it doesn't exist
    category_dir = os.path.join(BASE_SAVE_DIR, category)
    if not os.path.exists(category_dir):
        os.makedirs(category_dir)
    
    # Create a filename from the URL (sanitized)
    import re
    from urllib.parse import urlparse
    
    # Extract domain and path for filename
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    path = parsed_url.path
    
    # Clean up the filename
    filename = f"{domain}{path}".replace('/', '_').replace(':', '_')
    filename = re.sub(r'[^\w\-_.]', '_', filename)
    filename = filename[:100]  # Limit filename length
    
    # Ensure unique filename by adding timestamp if needed
    import time
    if not filename:
        filename = f"analysis_{int(time.time())}"
    
    file_path_txt = os.path.join(category_dir, f"{filename}.txt")
    file_path_csv = os.path.join(category_dir, f"{filename}.csv")
    
    try:
        with open(file_path_txt, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n\n")
            f.write(f"ANALYSIS:\n{analysis_text}")

        process_txt_folder_to_csv(file_path_txt, file_path_csv)
        return True, file_path_txt
    except Exception as e:
        return False, str(e)

def save_batch_results(results):
    """Save overall batch summary to a TXT file"""
    summary_file = os.path.join(BASE_SAVE_DIR, "batch_results.txt")
    with open(summary_file, 'w', encoding='utf-8') as f:
        f.write("URL\tSuccess\tResult\n")
        for result in results:
            # Join the result list with tabs
            f.write(f"{result[0]}\t{result[1]}\t{result[2]}\n")
    return summary_file

def clean_cache():
    """Clean expired cache files"""
    if not os.path.exists(CACHE_DIR):
        return
    
    print("Cleaning expired cache files...")
    count = 0
    for filename in os.listdir(CACHE_DIR):
        file_path_txt = os.path.join(CACHE_DIR, filename)
        if is_cache_expired(file_path_txt):
            try:
                os.remove(file_path_txt)
                count += 1
            except Exception as e:
                print(f"Error removing cache file {filename}: {e}")
    
    print(f"Removed {count} expired cache files.")
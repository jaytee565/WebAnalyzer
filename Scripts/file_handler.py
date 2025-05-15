import os
import csv
from config import BASE_SAVE_DIR, CACHE_DIR
from utils import is_cache_expired

def create_folders():
    """Create base and cache directories"""
    from config import CATEGORIES

    if not os.path.exists(BASE_SAVE_DIR):
        os.makedirs(BASE_SAVE_DIR)

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # No need to create category folders, just ensure base exists
    # Optionally, create empty CSVs with headers
    for category in CATEGORIES.keys():
        category_csv = os.path.join(BASE_SAVE_DIR, f"{category}.csv")
        if not os.path.exists(category_csv):
            with open(category_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['URL', 'Success', 'Analysis'])  # Headers

import csv
import os
import io

def save_analysis_to_file(analysis_text, category, url):
    """Append parsed CSV analysis to the category CSV file"""
    csv_path = os.path.join(BASE_SAVE_DIR, f"{category}.csv")

    try:
        # Parse analysis_text into actual CSV rows
        csv_reader = csv.reader(io.StringIO(analysis_text), delimiter = ";")
        rows = list(csv_reader)

        # Append rows to the CSV file
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for row in rows:
                writer.writerow(row)
        return True, csv_path

    except Exception as e:
        return False, str(e)

def save_batch_results(results):
    """Save overall batch summary to a CSV"""
    summary_file = os.path.join(BASE_SAVE_DIR, "batch_results.csv")
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['URL', 'Success', 'Result'])
        for result in results:
            writer.writerow(result)
    return summary_file

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
import os
import csv
import io
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
    for k,v in CATEGORIES.items():
        category_csv = os.path.join(BASE_SAVE_DIR, f"{k}.csv")
        if not os.path.exists(category_csv):
            with open(category_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([f"Category:{k}"])
                writer.writerow([])
                # Create header with question texts without the numbering
                headers = []
                for item in v:
                    if ". " in item:  # Split by first period and space
                        headers.append(item.split(". ", 1)[1])
                    else:
                        headers.append(item)  # Fallback if no numbered format
                writer.writerow(headers)  # Headers

def save_analysis_to_file(analysis_text, category, url):
    """Append parsed CSV analysis to the category CSV file"""
    csv_path = os.path.join(BASE_SAVE_DIR, f"{category}.csv")

    try:
        # Extract just the answer part before any footer
        answers_part = analysis_text.split("\n\n===========")[0].strip()
        
        # Check if we have our special delimiter "|||" which means we used JSON parsing
        if "|||" in answers_part:
            # Split by our special delimiter
            row_data = answers_part.split("|||")
        else:
            # Legacy CSV parsing as fallback
            try:
                # Clean up quotes if needed
                answers_part = answers_part.replace('""', '"')
                
                # Try to parse as CSV
                csv_reader = csv.reader([answers_part])
                row_data = next(csv_reader, None)
                
                # If parsing failed or row is empty, try simple splitting
                if not row_data:
                    row_data = [item.strip('"') for item in answers_part.split(',')]
            except:
                # Last resort fallback - just use the whole text as a single column
                row_data = [answers_part]
        
        # Prepend the URL as first column for tracking
        row_data = [url] + row_data
        
        # Append to the CSV file
        with open(csv_path, 'a', newline='', encoding='utf-8') as f:
            # Use a dialect that properly handles quoting
            writer = csv.writer(f, quoting=csv.QUOTE_ALL)
            writer.writerow(row_data)
        
        return True, csv_path

    except Exception as e:
        print(f"Error saving analysis: {e}")
        # Fallback method - just add raw text
        try:
            with open(csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f, quoting=csv.QUOTE_ALL)
                writer.writerow([url, analysis_text.replace('\n', ' ')])
            return True, csv_path
        except Exception as e2:
            return False, f"Failed to save analysis: {str(e2)}"

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
#!/usr/bin/env python3
"""
Website Analyzer
---------------
This script analyzes websites and categorizes them based on their content.
"""

from utils import check_dependencies, read_urls_from_file
from processor import process_single_url, batch_process_urls
from file_handler import clean_cache, create_folders
from export_csv import create_csv_files
import os

def export_all_txt_to_csv():
    """Export all existing TXT analysis files to their category CSVs"""
    from export_csv import extract_analysis_text, append_to_category_csv
    from config import BASE_SAVE_DIR, CATEGORIES
    
    # Ensure CSVs are created
    create_csv_files()
    
    total_processed = 0
    total_failed = 0
    
    # Process each category folder
    for category in CATEGORIES.keys():
        category_dir = os.path.join(BASE_SAVE_DIR, category)
        if not os.path.exists(category_dir):
            continue
        
        print(f"\nProcessing {category} folder...")
        processed = 0
        failed = 0
        
        # Process each TXT file in the category folder
        for filename in os.listdir(category_dir):
            if filename.endswith(".txt"):
                txt_path = os.path.join(category_dir, filename)
                try:
                    # Read the file
                    with open(txt_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Extract URL and analysis text
                    url = ""
                    if "URL:" in content:
                        url_line = content.split("URL:")[1].split("\n")[0].strip()
                        url = url_line
                    
                    analysis_text = extract_analysis_text(content)
                    
                    # Append to CSV
                    if append_to_category_csv(url, analysis_text, category):
                        processed += 1
                        print(f"✅ Processed: {filename}")
                    else:
                        failed += 1
                        print(f"❌ Failed to process: {filename}")
                except Exception as e:
                    failed += 1
                    print(f"❌ Error processing {filename}: {e}")
        
        print(f"Category {category}: Processed {processed}, Failed {failed}")
        total_processed += processed
        total_failed += failed
    
    print(f"\nTotal: Processed {total_processed}, Failed {total_failed}")
    return total_processed, total_failed

def main():
    # Check dependencies before starting
    if not check_dependencies():
        return
    
    print("Website Analyzer")
    print("===============")
    print("1. Analyze single URL")
    print("2. Batch process URLs from a file")
    print("3. Clean expired cache")
    print("4. Export all TXT files to CSV")
    
    choice = input("Select an option (1/2/3/4): ")
    
    if choice == "1":
        # Single URL mode
        url = input("Enter the URL to analyze: ").strip()
        process_single_url(url)
    
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
        
        batch_process_urls(urls)
    
    elif choice == "3":
        # Clean cache mode
        clean_cache()
    
    elif choice == "4":
        # Export all TXT files to CSV
        export_all_txt_to_csv()
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
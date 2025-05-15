#!/usr/bin/env python3
"""
Website Analyzer
---------------
This script analyzes websites and categorizes them based on their content.
"""

from utils import check_dependencies, read_urls_from_file
from processor import process_single_url, batch_process_urls
from file_handler import clean_cache, create_folders
import os

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
    
    else:
        print("Invalid choice.")

if __name__ == "__main__":
    main()
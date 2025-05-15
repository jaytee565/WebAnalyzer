import os
import io
import time
import ollama
from config import CATEGORIES, MODEL_NAME, CACHE_DIR
from utils import get_filename_from_url, is_cache_expired

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
    
    # classify using url
    sample_text = website_text[0:3000] if len(website_text)<3000 else website_text
    categories = ", ".join(CATEGORIES.keys())
    message = f"""
As a classifier, identify the category of this website from its text.
Choose ONE from: {categories}
If no clear match, respond with: Default

Website text:
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

Only use information from the provided text. Be concise and specific. Do not add extra questions or words for e.g. "here is the analysis", just reply the questions.Do not go to the next line unneccessarily. Put the same information in the same row. 
Structure your output as follows and fill it in with the content of the website:
"Header1"; "Header 2"; "Header 3"; and as follows
"Answer1"; "Answer2"; "Answer3" and as follows

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
        

        response = ollama.chat(
                model=MODEL_NAME,
                messages=messages
            )
        content = response['message']['content']
        analysis_buffer.write(content)
        print(content)
        
        # Add footer with timestamp
        analysis_buffer.write(f"\n\n=========== Analysis completed at {time.strftime('%Y-%m-%d %H:%M:%S')} ===========\n")
        analysis_buffer.write(f"Analyzed URL: {url}")
        
        return analysis_buffer.getvalue()
    except Exception as e:
        error_msg = f"\nError during analysis: {str(e)}"
        return error_msg
    
import csv
import io
from collections import OrderedDict

def text_to_csv(text, existing_csv=None, delimiter=':'):
    """
    Convert unstructured text data into CSV format.
    If an existing CSV is provided, it adds the new product as an additional column.
    
    Args:
        text (str): Text data with field names followed by values
        existing_csv (str, optional): Existing CSV content to append to
        delimiter (str, optional): Delimiter for CSV (default is comma)
        
    Returns:
        str: CSV formatted data
    """
    # Parse the input text into field-value pairs
    fields = OrderedDict()
    current_field = None
    current_value = []
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Check if this line starts a new field (contains a colon)
        if ':' in line and not line.startswith('*') and not line.startswith('•'):
            # If we have a previous field, add it to our dictionary
            if current_field is not None:
                value_text = ' '.join(current_value)
                fields[current_field] = value_text
                
            # Start a new field
            parts = line.split(':', 1)
            current_field = parts[0].strip()
            current_value = [parts[1].strip()] if len(parts) > 1 and parts[1].strip() else []
        else:
            # Continue with the current field
            if line.startswith('*') or line.startswith('•'):
                # Handle bullet points - replace with a clean bullet
                line = line.replace('*', '•').strip()
            current_value.append(line)
    
    # Add the last field if it exists
    if current_field is not None and (current_value or current_field):
        value_text = ' '.join(current_value)
        fields[current_field] = value_text
    
    # Get the product name as identifier
    product_name = fields.get('Product name', 'Unknown Product')
    
    # If there's an existing CSV, merge with it
    if existing_csv:
        # Parse existing CSV
        existing_data = {}
        existing_fieldnames = []
        existing_products = []
        
        csv_reader = csv.reader(io.StringIO(existing_csv), delimiter=delimiter)
        rows = list(csv_reader)
        
        if rows:
            # First row contains field names
            existing_fieldnames = rows[0][1:]  # Skip the first cell which is "Field"
            
            # Build dictionary with existing data
            for row in rows[1:]:
                if row:  # Skip empty rows
                    field_name = row[0]
                    existing_data[field_name] = row[1:]
                    
            # Get existing product names
            header_row = rows[0]
            existing_products = header_row[1:]
    else:
        # Start a new CSV
        existing_data = {}
        existing_fieldnames = []
        existing_products = []
    
    # Create output CSV
    output = io.StringIO()
    csv_writer = csv.writer(output, delimiter=delimiter)
    
    # Write header row with all product names
    all_products = existing_products + [product_name]
    csv_writer.writerow(['Field'] + all_products)
    
    # Combine all unique field names
    all_fields = list(fields.keys())
    for field in existing_data:
        if field not in all_fields:
            all_fields.append(field)
    
    # Write data rows
    for field in all_fields:
        row = [field]
        
        # Add values from existing products
        for _ in existing_products:
            product_values = existing_data.get(field, [])
            if product_values and len(product_values) > 0:
                row.append(product_values.pop(0))
            else:
                row.append('')
        
        # Add value for the new product
        row.append(fields.get(field, ''))
        
        csv_writer.writerow(row)
    
    return output.getvalue()
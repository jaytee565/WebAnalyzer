import os
import io
import time
import ollama
import json
import ast
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
    
    # Create explicit question list for more reliable parsing
    questions = [q.split(". ", 1)[1] if ". " in q else q for q in analysis_points]
    
    # Optimize by reducing prompt size but keeping structure
    prompt = f"""
Analyze this {category} category website based on the questions:
{analysis_points}

Only use information from the provided text. Be concise and specific. 
Structure your output EXACTLY as a comma-separated list of answers, ONE answer per question, in the order given.
If there is no relevant content for a question, put a '-' as the answer.
DO NOT include the questions themselves in your response.
DO NOT include line breaks in your response.
DO NOT include extra text or explanations.

Example format of your response:
"Answer1","Answer2","Answer3"

Website content:
{website_text}  # Limiting content size for token efficiency
"""
    try:
        messages = [
            {'role': 'system', 'content': "You are a website analyst focused on extracting key information efficiently."},
            {'role': 'user', 'content': prompt}
        ]
        
        # Capture the analysis
        analysis_buffer = io.StringIO()

        response = ollama.chat(
                model=MODEL_NAME,
                messages=messages
            )
        content = response['message']['content'].strip()
        print(content)
        
        # More robust output processing - handle the response as CSV directly
        # This avoids issues with dictionary parsing
        processed_content = content
        
        # Remove any explanatory text if the model still includes it
        if not processed_content.startswith('"') and '"' in processed_content:
            processed_content = processed_content[processed_content.find('"'):]
        
        # Pass through the content directly to the buffer - we'll parse as CSV later
        analysis_buffer.write(processed_content)
        
        # Add footer with timestamp
        analysis_buffer.write(f"\n\n=========== Analysis completed at {time.strftime('%Y-%m-%d %H:%M:%S')} ===========\n")
        analysis_buffer.write(f"Analyzed URL: {url}")

        return analysis_buffer.getvalue()
       
    except Exception as e:
        error_msg = f"\nError during analysis: {str(e)}"
        print(f"Analysis error: {e}")
        return error_msg
    
def text_to_csv(text, existing_csv=None, delimiter=','):
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
    # This is a simplified version that just returns the input
    # since we're now handling CSV directly in analyze_with_ollama
    return text
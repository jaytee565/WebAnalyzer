import os
import io
import time
import ollama
from config import CATEGORIES, MODEL_NAME, USE_STREAMING, CACHE_DIR
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
    You are a professional website content analyst. Your task is to extract specific answers from a {category} website.

    Below are the exact analysis questions you must answer:
    {analysis_points}

    Rules:
    - Only use information from the provided text.
    - DO NOT invent answers or speculate.
    - DO NOT reword or summarize the questions.
    - DO NOT answer any questions not listed.
    - Format your output exactly like the structure shown below.
    - If there is no relevant information in the content for a question, write: "- No information found."
    - Do not output the <think>

    Output format (mandatory):
    1. [Exact Question 1]:
    - Answer 1
    - Answer 2

    2. [Exact Question 2]:
    - Answer 1

    ...continue this format for all questions.

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
        analysis_buffer.write(f"Category: {category}\n\n")
        
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
                    print(content)
        else:
            # Non-streaming mode (faster)
            response = ollama.chat(
                model=MODEL_NAME,
                messages=messages
            )
            content = response['message']['content']
            analysis_buffer.write(content)
    
        
        return analysis_buffer.getvalue()
    except Exception as e:
        error_msg = f"\nError during analysis: {str(e)}"
        return error_msg
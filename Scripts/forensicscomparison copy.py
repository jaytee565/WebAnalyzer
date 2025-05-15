import requests
from bs4 import BeautifulSoup
import subprocess
from tabulate import tabulate
import re
import time
import validators  # You may need to install this: pip install validators

def validate_url(url):
    """Validate if the input is a properly formatted URL"""
    return validators.url(url)

def fetch_website_text(url):
    """Fetch and extract text from a website with improved error handling and parsing"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Try to determine encoding
        if response.encoding == 'ISO-8859-1':
            # Sites often default to ISO-8859-1 when they're actually UTF-8
            response.encoding = 'utf-8'
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style', 'footer', 'nav', 'header']):
            script_or_style.decompose()
            
        # Extract meaningful content (focusing on product description areas)
        main_content = soup.find('main') or soup.find('div', {'id': re.compile('(content|product|description)', re.I)})
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
        else:
            text = soup.get_text(separator=' ', strip=True)
            
        # Normalize text and remove problematic characters
        text = ' '.join(text.split())  # Normalize whitespace
        return text
    
    except requests.exceptions.RequestException as e:
        print(f"Request error fetching {url}: {e}")
        return ""
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

def call_ollama(prompt, model="llama3.2:1b"):
    """Call Ollama with better error handling and timeout management"""
    try:
        # Handle encoding issues by ensuring we use UTF-8
        process = subprocess.Popen(
            ["ollama", "run", model],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False  # Changed to binary mode
        )
        
        # Encode prompt as UTF-8 bytes
        prompt_bytes = prompt.encode('utf-8', errors='ignore')
        
        # Communicate in binary mode
        stdout_bytes, stderr_bytes = process.communicate(input=prompt_bytes, timeout=60)
        
        # Decode responses with error handling
        stdout = stdout_bytes.decode('utf-8', errors='replace') if stdout_bytes else ""
        stderr = stderr_bytes.decode('utf-8', errors='replace') if stderr_bytes else ""
        
        if stderr and not stdout:
            print("Ollama error:", stderr)
            return ""
        return stdout
    
    except subprocess.TimeoutExpired:
        print("Error: Ollama process timed out after 60 seconds")
        process.kill()
        return ""
    except Exception as e:
        print("Error calling Ollama:", e)
        return ""

def extract_markdown_table(text):
    """Extract markdown table with improved regex pattern matching"""
    # Look for sequences of lines containing pipe characters
    table_pattern = r'(\|[^\n]+\|\n)+'
    matches = re.findall(table_pattern, text)
    
    if matches:
        # Join all table parts and clean up
        return ''.join(matches).strip()
    
    # Fallback method using line by line approach
    table_lines = []
    capture = False
    row_count = 0
    
    for line in text.splitlines():
        if "|" in line:
            if not capture:
                capture = True
            table_lines.append(line)
            row_count += 1
        elif capture:
            # Only end table capture if we've had at least 3 rows (header, separator, data)
            # and we hit an empty line
            if row_count >= 3 and not line.strip():
                break
    
    return "\n".join(table_lines) if table_lines else ""

def parse_markdown_table(md_table):
    """Parse markdown table with validation and error handling"""
    try:
        lines = [line.strip() for line in md_table.splitlines() if line.strip()]
        
        if len(lines) < 3:  # Need header, separator, and at least one data row
            return None, None
            
        # Extract headers, handling edge cases
        header_parts = [h.strip() for h in lines[0].split("|")]
        headers = [h for h in header_parts if h]  # Filter out empty strings
        
        rows = []
        for line in lines[2:]:  # Skip header and separator lines
            if "|" in line:
                parts = [c.strip() for c in line.split("|")]
                cols = [c for c in parts if c != ""]  # Filter out empty strings
                
                # Handle potential mismatch in column count
                if len(cols) <= len(headers):
                    # Pad with empty strings if needed
                    while len(cols) < len(headers):
                        cols.append("N/A")
                    rows.append(cols)
        
        if not rows:
            return None, None
            
        return headers, rows
        
    except Exception as e:
        print(f"Error parsing markdown table: {e}")
        return None, None

def main():
    print("🔗 Enter up to 3 product URLs to compare.")
    urls = []
    
    for i in range(3):
        while True:
            url = input(f"Enter URL for product {i+1} (leave blank to skip): ").strip()
            if not url:
                break
                
            if validate_url(url):
                urls.append(url)
                break
            else:
                print("❌ Invalid URL format. Please enter a valid URL (e.g., https://example.com/product)")
    
    if len(urls) < 2:
        print("❌ Please enter at least two URLs for comparison.")
        return

    contents = []
    for i, url in enumerate(urls):
        print(f"Fetching content for Product {i+1}...")
        text = fetch_website_text(url)
        
        if not text:
            print(f"⚠️ Failed to extract content from {url}")
            continue
            
        # Clean text of potential problematic characters
        text = text.encode('utf-8', errors='ignore').decode('utf-8')
        
        print(f"✅ Successfully extracted {len(text)} characters")
        
        # Get a simple product name from URL for better identification
        product_name = url.split('/')[-1]
        if not product_name:
            product_name = url.split('/')[-2] if len(url.split('/')) > 2 else f"Product {i+1}"
            
        contents.append((f"Product {i+1} ({product_name})", text[:8000]))  # Reduced size limit
        
        # Add a small delay between requests
        if i < len(urls) - 1:
            time.sleep(1)

    if len(contents) < 2:
        print("❌ Could not extract enough content for comparison.")
        return

    # Build improved comparison prompt with shortened text to avoid encoding issues
    prompt = """You are a product analyst. Compare the following products based on their specifications and features.
Focus on: Target Devices, Copy Modes, Transfer Speed, Supported Formats, Sanitization Options, and Additional Features.
Return ONLY a markdown table with these columns:

| Feature | Product 1 | Product 2 | Product 3 (if applicable) |
|---------|-----------|-----------|---------------------------|
| ... | ... | ... | ... |
"""

    for label, text in contents:
        # Further limit text size to avoid potential encoding issues
        prompt += f"\n--- {label} ---\n{text[:5000]}\n"

    # Run the LLM
    print("\nCalling Ollama to generate comparison...")
    raw_response = call_ollama(prompt)
    
    if not raw_response:
        print("❌ Failed to get a response from Ollama")
        return

    # Extract and display
    markdown_table = extract_markdown_table(raw_response)
    if markdown_table:
        headers, rows = parse_markdown_table(markdown_table)
        if headers and rows:
            print("\n=== 📊 Product Comparison Table ===\n")
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        else:
            print("⚠️ Could not parse the markdown table properly.")
            print("Raw table output:")
            print(markdown_table)
    else:
        print("⚠️ No markdown table found in the model output.")
        print("First 200 characters of response:")
        print(raw_response[:200] + "...")

if __name__ == "__main__":
    main()
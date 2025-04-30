# Can work
import requests
from bs4 import BeautifulSoup
import ollama
import time
import os

# Categories for analysis
CATEGORIES = {
    "Technology": """
1. Target audience for the technology  
2. Key technologies or products featured  
3. Technical specifications or features highlighted  
4. Any release dates or version information  
5. Contact information  
""",
    "News": """
1. Publication dates of the articles  
2. Main headlines and topics covered (Include important personnel or location)  
3. Key facts from the articles  
4. Sources cited or referenced  
""",
    "Sports": """
1. Main sports or athletic activities featured  
2. Key teams, athletes, or events mentioned  
3. Recent results or upcoming events  
4. Fan or community engagement information  
5. Contact or venue information  
""",
    "E-commerce": """
1. Main product categories offered  
2. Any special deals or promotions  
3. Shipping or delivery information  
4. Return policy highlights  
5. Customer service contact details  
""",
    "Finance": """
1. Financial services or products offered  
2. Key market data or financial metrics mentioned  
3. Any investment advice or financial insights  
4. Regulatory information or compliance details  
5. Contact information for financial services  
""",
    "Education": """
1. Educational programs or courses offered  
2. Faculty or instructor information  
3. Admission requirements or processes  
4. Academic resources available  
5. Contact information for the institution  
""",
    "Healthcare": """
1. Healthcare provider information  
2. Medical services or treatments offered
3. Patient resources or health tips  
4. Insurance or payment information  
5. Contact details for appointments  
""",
    "Travel": """
1. Destinations or locations featured  
2. Travel packages or services offered  
3. Pricing or booking information  
4. Travel tips or recommendations  
5. Contact information for bookings or inquiries  
""",
    "Food": """
1. Types of cuisine or food products featured  
2. Menu highlights or special dishes  
3. Pricing or ordering information  
4. Location and hours of operation  
5. Contact information for reservations  
""",
    "Entertainment": """
1. Types of entertainment offered  
2. Featured artists, performers, or content  
3. Event schedules or release dates  
4. Venue information or platform details  
5. Contact information for tickets or support  
""",
    "Default": """
1. A short analysis of the content displayed in bullet points (Do not be vague)  
2. Any important statistics or data points found within the content (e.g., visitor numbers, growth figures, or specific metrics mentioned)  
3. Display the Contact information  
"""
}

# Scrape website content
def scrape_website(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        print("Downloading website content...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        print("✓ Download complete")
        return response.text
    except requests.RequestException as e:
        print(f"Error scraping website: {e}")
        return None

# Extract the main content of the website
def extract_main_content(html_content):
    if not html_content:
        return ""
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unnecessary elements
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "iframe"]):
        element.decompose()
    
    # Get text content
    text = soup.get_text(separator=" ", strip=True)
    
    return text

# Detect the category of the website
def detect_category(website_text):
    categories = ", ".join(CATEGORIES.keys())
    message = f"""
You are a classifier. Your job is to identify the category of a website based on its content.

Choose ONE from the following list of categories:
{categories}

Here is the website content:
{website_text}  

Respond with ONLY ONE word that exactly matches one of the categories above.
If no match, return: Default
"""
    try:
        # Create a fresh conversation for category detection
        messages = [
            {'role': 'system', 'content': "You are a website category classifier that responds with only one category name."},
            {'role': 'user', 'content': message}
        ]
        
        response = ollama.chat(
            model='llama3.2:1b',
            messages=messages
        )
        
        reply = response['message']['content'].strip()
        
        # Extract just the category name if there's extra text
        for category in CATEGORIES.keys():
            if category.lower() in reply.lower():
                print(f"✔ Detected Category: {category}")
                return category
        
        return 'Default'
    except Exception as e:
        print(f"Error detecting category: {e}")
        return 'Default'

# Analyze website content using Ollama
def analyze_with_ollama(website_text, category):
    analysis_points = CATEGORIES.get(category, CATEGORIES['Default'])
    prompt = f"""
Please analyze this website based on the following points for a {category} category:
{analysis_points}

Only use content from the text below. Do not add new content. Follow the bullet points.
Website content:
{website_text}
"""
    try:
        print("\n=========== Website Analysis ===========\n")
        
        # Create fresh conversation for analysis
        messages = [
            {'role': 'system', 'content': "You are a helpful assistant tasked with analyzing and summarizing website content."},
            {'role': 'user', 'content': prompt}
        ]
        
        stream = ollama.chat(
            model='llama3.2:1b',
            messages=messages,
            stream=True
        )
        
        for chunk in stream:
            if 'message' in chunk:
                print(chunk['message']['content'], end='', flush=True)
    except Exception as e:
        print(f"\nError during analysis: {str(e)}")

# Main function
def main():
    url = input("Enter the URL of the website you want to analyze: ").strip()
    start_time = time.time()

    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    html_content = scrape_website(url)
    if not html_content:
        print("Failed to scrape the website.")
        return

    website_text = extract_main_content(html_content)
    if not website_text:
        print("Failed to extract content.")
        return

    try:
        # Detect the category of the website
        category = detect_category(website_text)
        
        # Analyze the website based on the detected category
        analyze_with_ollama(website_text, category)
        
        print("\n\n=========== WEBSITE ANALYSIS COMPLETE ===========")
        print(f"Execution Time: {time.time() - start_time:.2f} seconds")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user.")
    except Exception as e:
        print(f"\n\nAn unexpected error occurred: {str(e)}")

if __name__ == "__main__":
    main()

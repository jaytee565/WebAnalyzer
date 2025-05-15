import os

# Configuration variables
CATEGORIES = {
    "Technology": """
1. Product name
2. Target audience for the technology  
3. Key technologies 
4. Technical specifications or features highlighted  
5. Any release dates or version information  
6. Contact information  
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
5. Key Personnel/ Companies/ Countries involved
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

# Hard-coded base directory for saving files (preserved as requested)
BASE_SAVE_DIR = r"C:\Users\DESG ITAdmin\Extrext\Website Analysis"

# Configuration for performance
MAX_TEXT_LENGTH = 10000  # Limit text length to reduce token usage
MAX_WORKERS = 4  # Number of concurrent processes/threads
CACHE_DIR = os.path.join(BASE_SAVE_DIR, "_cache")  # Cache directory for category classifications
USE_STREAMING = False  # Set to False for faster non-streaming responses
MODEL_NAME = "llama3.2:1b"  # Model to use for inference
CACHE_EXPIRY_DAYS = 7  # Number of days before cache entries expire
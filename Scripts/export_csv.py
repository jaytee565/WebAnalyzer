import os
import re
import csv
from config import BASE_SAVE_DIR, CATEGORIES

def create_csv_files():
    """Create base directory and initialize CSVs for each category with headers"""
    if not os.path.exists(BASE_SAVE_DIR):
        os.makedirs(BASE_SAVE_DIR)

    for category, questions in CATEGORIES.items():
        category_csv = os.path.join(BASE_SAVE_DIR, f"{category}.csv")
        if not os.path.exists(category_csv):
            with open(category_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write category name as the first row
                writer.writerow([f"Category: {category}"])
                
                # Extract headers from questions
                headers = ["URL"]  # Add URL as the first column
                for line in questions.strip().split('\n'):
                    line = line.strip()
                    if line and ". " in line:
                        # Extract the question text after the number
                        question = line.split(". ", 1)[1].strip()
                        headers.append(question)
                
                # Write headers row
                writer.writerow(headers)
            print(f"Created CSV file for category: {category}")

def parse_analysis(analysis_text):
    """Parse structured analysis text into a dictionary"""
    results = {}
    current_number = None
    current_question = None
    current_value_lines = []
    
    # Split the text by lines and process each line
    lines = analysis_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Try to match a numbered question pattern (e.g., "1. Product name: iPhone")
        match = re.match(r'^(\d+)\.\s*(.+?):\s*(.*)', line)
        
        if match:
            # If we were processing a previous question, save it
            if current_question:
                results[current_question] = " ".join(current_value_lines).strip()
            
            # Start a new question
            current_number = match.group(1)
            current_question = match.group(2).strip()
            first_value = match.group(3).strip()
            current_value_lines = [first_value] if first_value else []
        else:
            # Continue with the current question's answer
            if current_question:
                current_value_lines.append(line)
    
    # Save the last question
    if current_question:
        results[current_question] = " ".join(current_value_lines).strip()
    
    return results

def extract_analysis_text(content):
    """Extract the ANALYSIS section from text content"""
    if "ANALYSIS:" in content:
        return content.split("ANALYSIS:")[1].strip()
    else:
        return content.strip()

def append_to_category_csv(url, analysis_text, category):
    """Append analysis results to the appropriate category CSV file"""
    # Make sure category CSVs exist
    create_csv_files()
    
    # Get the analysis content
    parsed_analysis = parse_analysis(analysis_text)
    if not parsed_analysis:
        print(f"Warning: Could not parse analysis for {url}")
        return False
        
    # Get the questions for this category
    category_questions = CATEGORIES.get(category, CATEGORIES['Default'])
    headers = []
    for line in category_questions.strip().split('\n'):
        line = line.strip()
        if line and ". " in line:
            question = line.split(". ", 1)[1].strip()
            headers.append(question)
    
    # Prepare the row data
    row_data = [url]  # Start with URL
    
    # Add values for each header/question
    for header in headers:
        value = ""
        # Look for this header in the parsed analysis
        for question, answer in parsed_analysis.items():
            if header.lower() in question.lower() or question.lower() in header.lower():
                value = answer
                break
        row_data.append(value)
        
    # Write to the CSV file
    category_csv = os.path.join(BASE_SAVE_DIR, f"{category}.csv")
    try:
        with open(category_csv, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(row_data)
        print(f"Appended analysis for {url} to {category} CSV")
        return True
    except Exception as e:
        print(f"Error appending to CSV: {e}")
        return False
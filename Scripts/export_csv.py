import os
import re
import csv
from config import BASE_SAVE_DIR

def create_csv():
    """Create base and cache directories"""
    from config import CATEGORIES

    if not os.path.exists(BASE_SAVE_DIR):
        os.makedirs(BASE_SAVE_DIR)


    # Create empty CSVs with headers
    for k,v in CATEGORIES.items():
        category_csv = os.path.join(BASE_SAVE_DIR, f"{k}.csv")
        if not os.path.exists(category_csv):
            with open(category_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(v)  # Headers
                writer.writerow([f"Category:{k}"])
                # Create header with question texts without the numbering
                headers = []
                for item in v:
                    if ". " in item:  # Split by first period and space
                        headers.append(item.split(". ", 1)[1])
                    else:
                        headers.append(item)  # Fallback if no numbered format
                writer.writerow(headers)

def parse_analysis(analysis_text):
    lines = analysis_text.splitlines()
    results = {}
    current_key = None
    current_value_lines = []

    for line in lines:
        match = re.match(r'^(\d+)\. ([^:]+):\s*(.*)', line.strip())
        if match:
            if current_key:
                results[current_key] = " ".join(current_value_lines).strip()
            current_key = match.group(2).strip()
            first_line = match.group(3).strip()
            current_value_lines = [first_line] if first_line else []
        elif current_key:
            current_value_lines.append(line.strip())

    if current_key:
        results[current_key] = " ".join(current_value_lines).strip()

    return results

def extract_analysis_text(txt_file):
    with open(txt_file, 'r', encoding='utf-8') as f:
        content = f.read()

    if "ANALYSIS:" in content:
        return content.split("ANALYSIS:")[1].strip()
    else:
        return content

def process_txt_folder_to_csv(txt_file, output_csv):
    print(f"Processing file: {txt_file}")
    analysis_text = extract_analysis_text(txt_file)
    parsed = parse_analysis(analysis_text)
    print(f"Parsed content: {parsed}")

    headers = list(parsed.keys())
    values = [parsed[key] for key in headers]

    with open(output_csv, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerow(values)

    print(f"\n✅ CSV created from: {txt_file}\n📄 Saved as: {output_csv}")




folder_path = r"C:\Users\DESG ITAdmin\Extrext\Website Analysis\Technology\ureach-inc.com_page_HDD-Duplicator_SAS_MTS-series_1_EF_B8_B07_20SAS_20__20SATA_20HDD_SSD_20Duplicato.txt"
output_csv = r"C:\Users\DESG ITAdmin\Extrext\newvenv\Technology_analysis.csv"
process_txt_folder_to_csv(folder_path, output_csv)
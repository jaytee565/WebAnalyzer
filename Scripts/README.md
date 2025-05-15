# Website Analyzer

A tool to analyze websites and categorize them based on their content.

## Project Structure

- `main.py` - Entry point for the application
- `config.py` - Configuration variables and settings
- `scraper.py` - Website scraping functionality
- `analyzer.py` - Content analysis with Ollama
- `processor.py` - URL processing logic
- `file_handler.py` - File operations and storage
- `utils.py` - Utility functions
- `requirements.txt` - Required dependencies

## Setup

1. Install the required dependencies:

```bash
pip install -r requirements.txt
```

2. Make sure you have Ollama installed and running with the `llama3.2:1b` model:

```bash
ollama pull llama3.2:1b
```

## Usage

Run the main script:

```bash
python main.py
```

### Options

1. **Analyze single URL** - Analyze one website and see the results in real-time
2. **Batch process URLs from a file** - Process multiple URLs from a text file
3. **Clean expired cache** - Remove old cached category classifications

## Features

- Categorizes websites into predefined categories
- Extracts key information based on the category
- Caches results for faster processing
- Supports batch processing with multithreading
- Shows progress with a progress bar
#!/usr/bin/env python3
"""
AI Connection Test Script

Test script to verify AI API connection and configuration.
"""

import sys
import yaml
import json
from pathlib import Path
from typing import Dict

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def print_header(text: str):
    """Print formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.OKCYAN}ℹ {text}{Colors.ENDC}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


def load_config() -> Dict:
    """Load configuration from config.yaml."""
    config_path = Path("config.yaml")
    
    if not config_path.exists():
        print_error("config.yaml not found!")
        print_info("Please copy config.sample.yaml to config.yaml and configure it.")
        print_info("Example: cp config.sample.yaml config.yaml")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print_success("Configuration file loaded successfully")
        return config
    except Exception as e:
        print_error(f"Error loading configuration: {str(e)}")
        sys.exit(1)


def validate_config(config: Dict) -> bool:
    """Validate configuration settings."""
    print_header("Validating Configuration")
    
    ai_config = config.get('ai', {})
    app_config = config.get('app', {})
    
    valid = True
    
    # Check AI provider
    provider = ai_config.get('provider', '')
    print_info(f"AI Provider: {provider}")
    
    if provider not in ['openai', 'azure', 'anthropic', 'openai_compatible']:
        print_warning(f"Unknown provider: {provider}")
        valid = False
    else:
        print_success(f"Valid provider: {provider}")
    
    # Check model
    model = ai_config.get('model', '')
    print_info(f"Model: {model}")
    
    if not model:
        print_warning("No model specified")
        valid = False
    else:
        print_success(f"Model configured: {model}")
    
    # Check API credentials based on provider
    if provider == 'openai':
        api_key = ai_config.get('openai_api_key', '')
        if api_key and api_key != 'sk-YOUR_OPENAI_KEY_HERE':
            print_success("OpenAI API key configured")
        else:
            print_error("OpenAI API key not configured")
            valid = False
    
    elif provider == 'azure':
        api_key = ai_config.get('azure_api_key', '')
        endpoint = ai_config.get('azure_endpoint', '')
        if api_key and api_key != 'YOUR_AZURE_KEY_HERE':
            print_success("Azure API key configured")
        else:
            print_error("Azure API key not configured")
            valid = False
        if endpoint and 'YOUR-RESOURCE-NAME' not in endpoint:
            print_success("Azure endpoint configured")
        else:
            print_error("Azure endpoint not configured")
            valid = False
    
    elif provider == 'anthropic':
        api_key = ai_config.get('anthropic_api_key', '')
        if api_key and api_key != 'sk-ant-YOUR_ANTHROPIC_KEY_HERE':
            print_success("Anthropic API key configured")
        else:
            print_error("Anthropic API key not configured")
            valid = False
    
    elif provider == 'openai_compatible':
        api_key = ai_config.get('compatible_api_key', '')
        base_url = ai_config.get('compatible_base_url', '')
        if api_key and api_key != 'YOUR_API_KEY_HERE':
            print_success("API key configured")
        else:
            print_error("API key not configured")
            valid = False
        if base_url and 'YOUR_PROJECT_ID' not in base_url:
            print_success("Base URL configured")
            print_info(f"Endpoint: {base_url}")
        else:
            print_error("Base URL not configured")
            valid = False
    
    # Check app settings
    print_info("\nApp Configuration:")
    sitemap_url = app_config.get('sitemap_url', '')
    if sitemap_url and sitemap_url != 'https://example.com/sitemap.xml':
        print_success(f"Sitemap URL: {sitemap_url}")
    else:
        print_warning("Sitemap URL not configured (using example)")
    
    return valid


def test_ai_connection(config: Dict) -> bool:
    """Test AI API connection."""
    print_header("Testing AI Connection")
    
    try:
        # Import AI processor
        from src.ai_processor import AIProcessor
        
        print_info("Initializing AI processor...")
        ai_processor = AIProcessor(config)
        print_success("AI processor initialized")
        
        print_info("Sending test request to API...")
        result = ai_processor.test_connection()
        
        if result:
            print_success("Connection test PASSED!")
            return True
        else:
            print_error("Connection test FAILED")
            return False
            
    except ImportError as e:
        print_error(f"Import error: {str(e)}")
        print_info("Make sure to install dependencies: pip install -r requirements.txt")
        return False
    except Exception as e:
        print_error(f"Connection test failed: {str(e)}")
        return False


def test_sample_clustering(config: Dict):
    """Test keyword clustering with sample data."""
    print_header("Testing Keyword Clustering (Optional)")
    
    try:
        from src.ai_processor import AIProcessor
        
        sample_keywords = [
            "best running shoes",
            "running shoes for beginners",
            "how to choose running shoes",
            "trail running shoes",
            "marathon training tips",
            "5k training plan"
        ]
        
        print_info(f"Testing with {len(sample_keywords)} sample keywords...")
        
        ai_processor = AIProcessor(config)
        clusters = ai_processor.cluster_keywords(sample_keywords)
        
        print_success(f"Clustering successful! Created {len(clusters)} clusters")
        
        # Display results
        for i, cluster in enumerate(clusters, 1):
            print(f"\n{Colors.OKCYAN}Cluster {i}:{Colors.ENDC}")
            print(f"  Topic: {cluster.get('main_topic', 'N/A')}")
            print(f"  Keywords: {', '.join(cluster.get('keywords', []))}")
            print(f"  Title: {cluster.get('suggested_title', 'N/A')}")
        
    except Exception as e:
        print_warning(f"Clustering test skipped: {str(e)}")


def main():
    """Main test function."""
    print_header("Seo Toolkit - AI Connection Test")
    
    # Load configuration
    config = load_config()
    
    # Validate configuration
    config_valid = validate_config(config)
    
    if not config_valid:
        print_warning("\nConfiguration has issues. Please review and fix.")
        print_info("Continuing with connection test anyway...\n")
    
    # Test connection
    connection_ok = test_ai_connection(config)
    
    if connection_ok:
        # Test clustering (optional)
        test_sample_clustering(config)
        
        # Final summary
        print_header("Test Summary")
        print_success("All tests passed!")
        print_info("\nYou can now run the main application:")
        print(f"{Colors.BOLD}  python main.py -i your_search_console_data.xlsx{Colors.ENDC}\n")
    else:
        print_header("Test Summary")
        print_error("Connection test failed!")
        print_info("\nPlease check:")
        print("  1. Your API credentials in config.yaml")
        print("  2. Your internet connection")
        print("  3. API endpoint URL is correct")
        print("  4. You have installed all dependencies: pip install -r requirements.txt\n")
        sys.exit(1)


if __name__ == "__main__":
    main()


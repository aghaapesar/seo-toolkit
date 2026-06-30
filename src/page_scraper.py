"""
Page Scraper Module

Scrapes page titles, meta descriptions, and other SEO tags from URLs.
Supports batch processing with progress tracking and resume capability.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
from pathlib import Path
from typing import List, Dict, Optional
import logging
from tqdm import tqdm
import time
from urllib.parse import urlparse, unquote
import urllib.parse

logger = logging.getLogger(__name__)


class PageScraper:
    """
    Scrapes SEO-related data from web pages.
    
    Features:
    - Extract title, meta description, H1, canonical URL
    - Batch processing with progress bars
    - Resume capability (skips already scraped pages)
    - User control over batch size
    - Separate output files per sitemap
    - Test mode support
    """
    
    def __init__(self, output_dir: str = "output"):
        """
        Initialize PageScraper.
        
        Args:
            output_dir: Directory to save output Excel files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # Default request headers to mimic a browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        logger.info(f"PageScraper initialized with output dir: {self.output_dir}")
    
    def _decode_persian_url(self, url: str) -> str:
        """
        Decode Persian URLs properly to display readable Persian text.
        
        Args:
            url: Encoded URL
            
        Returns:
            Decoded URL with readable Persian text
        """
        try:
            # Parse the URL
            parsed = urlparse(url)
            
            # Decode the path component
            decoded_path = unquote(parsed.path, encoding='utf-8')
            
            # Decode query parameters
            if parsed.query:
                decoded_query = unquote(parsed.query, encoding='utf-8')
            else:
                decoded_query = ''
            
            # Reconstruct the URL
            decoded_url = f"{parsed.scheme}://{parsed.netloc}{decoded_path}"
            if decoded_query:
                decoded_url += f"?{decoded_query}"
            
            return decoded_url
            
        except Exception as e:
            logger.warning(f"Error decoding URL {url}: {str(e)}")
            return url  # Return original if decoding fails
    
    def scrape_page(self, url: str, timeout: int = 10) -> Dict:
        """
        Scrape SEO data from a single page.
        
        Args:
            url: URL to scrape
            timeout: Request timeout in seconds
            
        Returns:
            Dictionary with scraped data
        """
        # Decode Persian URLs properly
        decoded_url = self._decode_persian_url(url)
        
        result = {
            'url': decoded_url,  # Store decoded URL
            'original_url': url,  # Keep original for reference
            'status': 'pending',
            'title': '',
            'meta_description': '',
            'h1': '',
            'canonical_url': '',
            'og_title': '',
            'og_description': '',
            'twitter_title': '',
            'twitter_description': '',
            'error': ''
        }
        
        try:
            # Send GET request with decoded URL
            response = requests.get(decoded_url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            
            # Parse HTML
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract title
            title_tag = soup.find('title')
            if title_tag:
                result['title'] = title_tag.get_text().strip()
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                result['meta_description'] = meta_desc['content'].strip()
            
            # Extract H1 (first one if multiple exist)
            h1_tag = soup.find('h1')
            if h1_tag:
                result['h1'] = h1_tag.get_text().strip()
            
            # Extract canonical URL
            canonical = soup.find('link', attrs={'rel': 'canonical'})
            if canonical and canonical.get('href'):
                result['canonical_url'] = canonical['href']
            
            # Extract Open Graph tags
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                result['og_title'] = og_title['content'].strip()
            
            og_desc = soup.find('meta', property='og:description')
            if og_desc and og_desc.get('content'):
                result['og_description'] = og_desc['content'].strip()
            
            # Extract Twitter Card tags
            twitter_title = soup.find('meta', attrs={'name': 'twitter:title'})
            if twitter_title and twitter_title.get('content'):
                result['twitter_title'] = twitter_title['content'].strip()
            
            twitter_desc = soup.find('meta', attrs={'name': 'twitter:description'})
            if twitter_desc and twitter_desc.get('content'):
                result['twitter_description'] = twitter_desc['content'].strip()
            
            result['status'] = 'success'
            logger.debug(f"Successfully scraped: {decoded_url}")
            
        except requests.Timeout:
            result['status'] = 'timeout'
            result['error'] = f'Request timeout after {timeout}s'
            logger.warning(f"Timeout scraping {decoded_url}")
            
        except requests.RequestException as e:
            result['status'] = 'error'
            result['error'] = str(e)[:200]
            logger.warning(f"Error scraping {decoded_url}: {str(e)}")
            
        except Exception as e:
            result['status'] = 'error'
            result['error'] = f'Parsing error: {str(e)}'[:200]
            logger.error(f"Unexpected error scraping {decoded_url}: {str(e)}")
        
        return result
    
    def _get_output_filename(self, sitemap_url: str) -> Path:
        """
        Generate output filename based on sitemap URL.
        
        Args:
            sitemap_url: Sitemap URL
            
        Returns:
            Output file path
        """
        # Extract domain from sitemap URL
        domain = urlparse(sitemap_url).netloc.replace('www.', '')
        
        # Create filename
        filename = f"seo_data_{domain}.xlsx"
        return self.output_dir / filename
    
    def _load_existing_data(self, output_file: Path) -> Optional[pd.DataFrame]:
        """
        Load existing scraped data to enable resume functionality.
        
        Args:
            output_file: Path to existing output file
            
        Returns:
            DataFrame if file exists, None otherwise
        """
        if output_file.exists():
            try:
                df = pd.read_excel(output_file)
                logger.info(f"Loaded {len(df)} existing records from {output_file}")
                return df
            except Exception as e:
                logger.warning(f"Could not load existing file: {str(e)}")
                return None
        return None
    
    def scrape_urls_batch(
        self,
        urls: List[str],
        sitemap_url: str,
        batch_size: Optional[int] = None,
        test_mode: bool = False,
        delay: float = 0.5,
        non_interactive: bool = False,
    ) -> Path:
        """
        Scrape multiple URLs in batches with progress tracking.
        
        Args:
            urls: List of URLs to scrape
            sitemap_url: Source sitemap URL (for output naming)
            batch_size: Pages per batch (prompted if None and interactive)
            test_mode: Limit to 10 pages
            delay: Delay between requests in seconds
            non_interactive: Skip CLI prompts (for web/API usage)
            urls: List of URLs to scrape
            sitemap_url: Original sitemap URL (for filename generation)
            batch_size: Number of pages to scrape per batch (asks user if None)
            test_mode: If True, limit to 10 pages
            delay: Delay between requests in seconds
            
        Returns:
            Path to output Excel file
        """
        # Get output filename
        output_file = self._get_output_filename(sitemap_url)
        
        # Load existing data if any
        existing_df = self._load_existing_data(output_file)
        scraped_urls = set()
        
        if existing_df is not None:
            scraped_urls = set(existing_df['url'].tolist())
            print(f"\n📊 Found existing data: {len(scraped_urls)} URLs already scraped")
        
        # Filter out already scraped URLs
        urls_to_scrape = [url for url in urls if url not in scraped_urls]
        
        if not urls_to_scrape:
            print(f"\n✅ All {len(urls)} URLs already scraped!")
            print(f"   Output file: {output_file}")
            return output_file
        
        print(f"\n📋 URLs to scrape: {len(urls_to_scrape)} (Total: {len(urls)})")
        
        # Apply test mode limit
        if test_mode:
            urls_to_scrape = urls_to_scrape[:10]
            print(f"🧪 TEST MODE: Limited to {len(urls_to_scrape)} pages")
        
        # Ask for batch size if not provided
        if batch_size is None:
            batch_size = len(urls_to_scrape) if non_interactive else self._ask_batch_size(len(urls_to_scrape))
        
        # Scraping loop
        results = []
        total_scraped = 0
        
        while total_scraped < len(urls_to_scrape):
            # Get current batch
            end_idx = min(total_scraped + batch_size, len(urls_to_scrape))
            batch_urls = urls_to_scrape[total_scraped:end_idx]
            
            print(f"\n🔄 Scraping batch: {total_scraped + 1} to {end_idx} of {len(urls_to_scrape)}")
            
            # Scrape with progress bar
            for url in tqdm(batch_urls, desc="Scraping pages"):
                result = self.scrape_page(url)
                results.append(result)
                
                # Delay to be polite to the server
                time.sleep(delay)
            
            total_scraped = end_idx
            
            # Save intermediate results
            self._save_results(results, existing_df, output_file)
            
            print(f"✅ Batch complete. Scraped: {total_scraped}/{len(urls_to_scrape)}")
            
            # Ask if user wants to continue
            if total_scraped < len(urls_to_scrape) and not non_interactive:
                continue_scraping = input(f"\n⏸️  Scraped {total_scraped}/{len(urls_to_scrape)} pages. Continue? (Y/n): ").strip().lower()
                
                if continue_scraping == 'n':
                    print(f"\n⏹️  Scraping paused. {len(urls_to_scrape) - total_scraped} URLs remaining.")
                    print(f"   Run again to resume from where you left off.")
                    break
        
        # Final save
        self._save_results(results, existing_df, output_file)
        
        # Show statistics
        self._show_statistics(results, output_file)
        
        return output_file
    
    def _ask_batch_size(self, total_urls: int) -> int:
        """
        Ask user for batch size.
        
        Args:
            total_urls: Total number of URLs to scrape
            
        Returns:
            Batch size chosen by user
        """
        print("\n" + "-"*60)
        print("How many pages would you like to scrape per batch?")
        print(f"  Recommended: 50-100 for large sites")
        print(f"  Total URLs: {total_urls}")
        print("-"*60)
        
        while True:
            try:
                batch_size = input("Batch size (default 50): ").strip()
                
                if not batch_size:
                    return 50
                
                batch_size = int(batch_size)
                
                if batch_size < 1:
                    print("❌ Batch size must be at least 1")
                    continue
                
                if batch_size > total_urls:
                    print(f"ℹ️  Batch size larger than total URLs. Using {total_urls}")
                    return total_urls
                
                return batch_size
                
            except ValueError:
                print("❌ Please enter a valid number")
    
    def _save_results(
        self,
        new_results: List[Dict],
        existing_df: Optional[pd.DataFrame],
        output_file: Path
    ):
        """
        Save scraping results to Excel file.
        
        Args:
            new_results: Newly scraped results
            existing_df: Existing DataFrame if any
            output_file: Path to output file
        """
        # Convert new results to DataFrame
        new_df = pd.DataFrame(new_results)
        
        # Combine with existing data
        if existing_df is not None:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
        else:
            combined_df = new_df
        
        # Remove duplicates (keep first occurrence)
        combined_df = combined_df.drop_duplicates(subset=['url'], keep='first')
        
        # Save to Excel
        combined_df.to_excel(output_file, index=False, engine='openpyxl')
        
        logger.info(f"Saved {len(combined_df)} records to {output_file}")
    
    def _show_statistics(self, results: List[Dict], output_file: Path):
        """
        Show scraping statistics.
        
        Args:
            results: List of scraping results
            output_file: Path to output file
        """
        if not results:
            return
        
        success_count = sum(1 for r in results if r['status'] == 'success')
        error_count = sum(1 for r in results if r['status'] == 'error')
        timeout_count = sum(1 for r in results if r['status'] == 'timeout')
        
        print("\n" + "="*60)
        print("📊 SCRAPING STATISTICS")
        print("="*60)
        print(f"  ✅ Successful: {success_count}")
        print(f"  ❌ Errors: {error_count}")
        print(f"  ⏱️  Timeouts: {timeout_count}")
        print(f"  📄 Total: {len(results)}")
        print("-"*60)
        print(f"  💾 Output file: {output_file.name}")
        print("="*60)


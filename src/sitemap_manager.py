"""
Sitemap Manager Module

Handles interactive sitemap download, parsing, and management with retry logic.
Supports sitemap indices and selective sitemap downloads.
"""

import requests
from lxml import etree
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging
from tqdm import tqdm
import hashlib
import time

logger = logging.getLogger(__name__)

# Browser-like headers — many sites block default python-requests User-Agent.
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/xml,text/xml,application/xhtml+xml,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,fa;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


class SitemapManager:
    """
    Manages sitemap downloads and parsing with interactive user input.
    
    Features:
    - Interactive sitemap URL input
    - Automatic detection of sitemap indices
    - Selective download of sub-sitemaps
    - Retry logic with 10 attempts
    - Local caching to avoid re-downloads
    - Progress tracking for large sitemaps
    """
    
    def __init__(self, sitemap_dir: str = "sitemaps"):
        """
        Initialize SitemapManager.
        
        Args:
            sitemap_dir: Directory to store downloaded sitemaps
        """
        self.sitemap_dir = Path(sitemap_dir)
        self.sitemap_dir.mkdir(exist_ok=True)
        self.last_download_error: Optional[str] = None
        logger.info(f"Sitemap directory: {self.sitemap_dir}")
    
    def _get_cache_filename(self, url: str) -> Path:
        """
        Generate a cache filename based on URL hash.
        
        Args:
            url: Sitemap URL
            
        Returns:
            Path to cache file
        """
        # Create a hash of the URL for filename
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        
        # Extract domain for readable filename
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.replace('www.', '')
        
        filename = f"{domain}_{url_hash}.xml"
        return self.sitemap_dir / filename
    
    def _download_with_retry(
        self,
        url: str,
        max_retries: int = 10,
        timeout: int = 30,
        silent: bool = False,
    ) -> Optional[bytes]:
        """
        Download sitemap with retry logic.

        Input:
            url: URL to download.
            max_retries: Maximum retry attempts.
            timeout: Per-request timeout in seconds.
            silent: Skip console output (for web/API).

        Output:
            Response body bytes, or None if all attempts failed.
        """
        self.last_download_error = None
        url = url.strip()

        if not silent:
            print(f"\n📥 Downloading sitemap: {url}")

        last_exc: Optional[Exception] = None

        for attempt in range(1, max_retries + 1):
            try:
                if not silent:
                    print(f"   Attempt {attempt}/{max_retries}...", end=" ")

                response = requests.get(
                    url,
                    headers=DEFAULT_REQUEST_HEADERS,
                    timeout=timeout,
                    allow_redirects=True,
                )
                response.raise_for_status()

                if not silent:
                    print("✅ Success!")
                logger.info(f"Downloaded sitemap from {url} (attempt {attempt})")
                return response.content

            except requests.RequestException as exc:
                last_exc = exc
                self.last_download_error = f"{type(exc).__name__}: {exc}"
                if not silent:
                    print(f"❌ Failed: {str(exc)[:80]}")
                logger.warning(
                    f"Download attempt {attempt} failed for {url}: {self.last_download_error}"
                )

                if attempt < max_retries:
                    wait_time = min(2 ** attempt, 30)
                    if not silent:
                        print(f"   Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                elif not silent:
                    print(f"\n❌ All {max_retries} download attempts failed!")

        if last_exc is not None:
            self.last_download_error = f"{type(last_exc).__name__}: {last_exc}"
        return None
    
    def _parse_sitemap_content(self, content: bytes) -> Tuple[List[str], List[str]]:
        """
        Parse sitemap XML content.
        
        Args:
            content: XML content as bytes
            
        Returns:
            Tuple of (urls, sub_sitemaps)
        """
        try:
            root = etree.fromstring(content)
            namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            # Extract URLs (namespace-aware + fallback for variant XML)
            urls = root.xpath('//ns:url/ns:loc/text()', namespaces=namespaces)
            sub_sitemaps = root.xpath('//ns:sitemap/ns:loc/text()', namespaces=namespaces)

            if not urls:
                urls = root.xpath('//*[local-name()="url"]/*[local-name()="loc"]/text()')
            if not sub_sitemaps:
                sub_sitemaps = root.xpath(
                    '//*[local-name()="sitemap"]/*[local-name()="loc"]/text()'
                )

            return urls, sub_sitemaps
            
        except etree.XMLSyntaxError as e:
            logger.error(f"XML parsing error: {str(e)}")
            return [], []
    
    def get_sitemap_url_interactive(self) -> str:
        """
        Prompt user for sitemap URL interactively.
        
        Returns:
            Sitemap URL entered by user
        """
        print("\n" + "="*60)
        print("🗺️  SITEMAP CONFIGURATION")
        print("="*60)
        
        while True:
            url = input("\nEnter your sitemap URL (e.g., https://example.com/sitemap.xml): ").strip()
            
            if not url:
                print("❌ URL cannot be empty. Please try again.")
                continue
            
            if not url.startswith(('http://', 'https://')):
                print("❌ URL must start with http:// or https://")
                continue
            
            return url
    
    def select_sitemaps_interactive(self, sitemap_urls: List[str]) -> List[str]:
        """
        Let user select which sitemaps to download from a list.
        
        Args:
            sitemap_urls: List of sitemap URLs
            
        Returns:
            Selected sitemap URLs
        """
        print("\n" + "="*60)
        print(f"📋 FOUND {len(sitemap_urls)} SUB-SITEMAPS")
        print("="*60)
        
        for idx, url in enumerate(sitemap_urls, 1):
            # Extract readable name from URL
            name = url.split('/')[-1].replace('.xml', '').replace('sitemap', '')
            print(f"  [{idx}] {name or 'main'} - {url}")
        
        print("\n" + "-"*60)
        print("Selection options:")
        print("  - Enter numbers separated by commas (e.g., 1,3,5)")
        print("  - Enter 'all' to download all sitemaps")
        print("  - Enter 'none' to skip")
        print("-"*60)
        
        while True:
            choice = input("\nYour selection: ").strip().lower()
            
            if choice == 'all':
                print(f"✅ Selected all {len(sitemap_urls)} sitemaps")
                return sitemap_urls
            
            if choice == 'none':
                print("⏭️  Skipped sitemap selection")
                return []
            
            # Parse comma-separated numbers
            try:
                indices = [int(x.strip()) for x in choice.split(',')]
                
                # Validate indices
                if all(1 <= idx <= len(sitemap_urls) for idx in indices):
                    selected = [sitemap_urls[idx-1] for idx in indices]
                    print(f"✅ Selected {len(selected)} sitemap(s)")
                    return selected
                else:
                    print(f"❌ Invalid selection. Numbers must be between 1 and {len(sitemap_urls)}")
            
            except ValueError:
                print("❌ Invalid format. Use comma-separated numbers or 'all'/'none'")
    
    def download_and_parse_sitemap(
        self,
        url: Optional[str] = None,
        force_download: bool = False
    ) -> List[str]:
        """
        Download and parse sitemap with caching and interactive features.
        
        Args:
            url: Sitemap URL (prompts user if not provided)
            force_download: Force re-download even if cached
            
        Returns:
            List of URLs extracted from sitemap(s)
        """
        # Get URL from user if not provided
        if not url:
            url = self.get_sitemap_url_interactive()
        
        # Check cache first
        cache_file = self._get_cache_filename(url)
        
        if cache_file.exists() and not force_download:
            print(f"\n✅ Using cached sitemap: {cache_file.name}")
            
            retry = input("   Download again? (y/N): ").strip().lower()
            if retry not in ['y', 'yes']:
                with open(cache_file, 'rb') as f:
                    content = f.read()
                
                urls, sub_sitemaps = self._parse_sitemap_content(content)
                
                if sub_sitemaps:
                    # Handle sitemap index
                    return self._handle_sitemap_index(sub_sitemaps)
                
                print(f"   📊 Loaded {len(urls)} URLs from cache")
                return urls
        
        # Download sitemap
        content = self._download_with_retry(url)
        
        if not content:
            print("\n⚠️  Failed to download sitemap.")
            
            retry = input("Do you want to try again? (y/N): ").strip().lower()
            if retry in ['y', 'yes']:
                return self.download_and_parse_sitemap(url, force_download=True)
            else:
                print("❌ Aborting due to sitemap download failure.")
                return []
        
        # Save to cache
        with open(cache_file, 'wb') as f:
            f.write(content)
        print(f"💾 Cached sitemap: {cache_file.name}")
        
        # Parse content
        urls, sub_sitemaps = self._parse_sitemap_content(content)
        
        # Handle sitemap index
        if sub_sitemaps:
            return self._handle_sitemap_index(sub_sitemaps)
        
        print(f"✅ Extracted {len(urls)} URLs from sitemap")
        logger.info(f"Parsed {len(urls)} URLs from sitemap")
        
        return urls
    
    def _handle_sitemap_index(self, sub_sitemaps: List[str]) -> List[str]:
        """
        Handle sitemap index by letting user select which sitemaps to download.
        
        Args:
            sub_sitemaps: List of sub-sitemap URLs
            
        Returns:
            Combined URLs from selected sitemaps
        """
        print(f"\n🔗 This is a sitemap index containing {len(sub_sitemaps)} sub-sitemaps")
        
        selected_sitemaps = self.select_sitemaps_interactive(sub_sitemaps)
        
        if not selected_sitemaps:
            return []
        
        # Download and parse selected sitemaps
        all_urls = []
        
        print(f"\n📥 Downloading {len(selected_sitemaps)} sitemap(s)...")
        
        for sitemap_url in tqdm(selected_sitemaps, desc="Processing sitemaps"):
            cache_file = self._get_cache_filename(sitemap_url)
            
            # Check cache
            if cache_file.exists():
                with open(cache_file, 'rb') as f:
                    content = f.read()
            else:
                content = self._download_with_retry(sitemap_url, max_retries=3)
                
                if content:
                    with open(cache_file, 'wb') as f:
                        f.write(content)
            
            if content:
                urls, _ = self._parse_sitemap_content(content)
                all_urls.extend(urls)
        
        print(f"\n✅ Total URLs extracted: {len(all_urls)}")
        logger.info(f"Extracted {len(all_urls)} URLs from {len(selected_sitemaps)} sitemaps")
        
        return all_urls


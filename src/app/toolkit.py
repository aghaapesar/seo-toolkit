"""
Seo Toolkit application core.

Coordinates CLI operational modes: content analysis, scraping, generation,
internal linking, synonyms, and URL index diff tracking.
"""

import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from tqdm import tqdm

from src.ai_model_manager import AIModelManager
from src.ai_processor import AIProcessor
from src.analyzer import SearchConsoleAnalyzer
from src.cli.prompts import get_project_name_interactive, print_banner
from src.cli.sections import print_section
from src.clustering import KeywordClusterer
from src.content_generator import ContentGenerator
from src.data_loader import DataLoader
from src.document_exporter import DocumentExporter
from src.excel_writer import ExcelWriter
from src.file_selector import FileSelector
from src.internal_linker import InternalLinker
from src.knowledge_base import KnowledgeBase
from src.page_scraper import PageScraper
from src.services.url_index_tracker import UrlIndexTracker
from src.sitemap_manager import SitemapManager
from src.synonym_finder import SynonymFinder

logger = logging.getLogger(__name__)


class SeoToolkit:
    """
    Main application class for Seo Toolkit workflows.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize Seo Toolkit.
        
        Args:
            config_path: Path to YAML configuration file
        """
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Initialize core components
        self.data_loader = DataLoader(self.config)
        self.analyzer = SearchConsoleAnalyzer(self.config)
        self.ai_processor = AIProcessor(self.config)
        self.clusterer = KeywordClusterer(self.config)
        self.excel_writer = ExcelWriter(self.config)
        
        # Initialize new interactive components
        self.sitemap_manager = SitemapManager()
        self.file_selector = FileSelector()
        self.page_scraper = PageScraper()
        
        # Knowledge base will be initialized per project
        self.knowledge_base = None
        
        logger.info("Seo Toolkit initialized successfully")
    
    def _load_config(self, config_path: str) -> Dict:
        """
        Load and validate configuration from YAML file.
        
        Args:
            config_path: Path to config file
            
        Returns:
            Configuration dictionary
            
        Raises:
            SystemExit: If config file not found or invalid
        """
        try:
            config_file = Path(config_path)
            
            if not config_file.exists():
                logger.error(f"Configuration file not found: {config_path}")
                print(f"\n❌ Config file not found: {config_path}")
                print("   Please copy config.sample.yaml to config.yaml")
                sys.exit(1)
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            logger.info(f"📄 Configuration loaded from {config_path}")
            return config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            print(f"\n❌ Failed to load config: {str(e)}")
            sys.exit(1)
    
    def run_content_optimization(self, test_mode: bool = False):
        """
        Run content optimization workflow using Search Console data.
        
        This mode analyzes existing search performance and generates:
        1. Improvement suggestions for existing content
        2. New content ideas based on keyword clusters
        
        Args:
            test_mode: If True, limit processing to 10 queries for testing
        """
        print_banner()
        print("📊 MODE: Content Optimization & Analysis")
        
        # Get project name for knowledge base
        project_name = get_project_name_interactive()
        
        # Initialize knowledge base for this project
        self.knowledge_base = KnowledgeBase(project_name)
        logger.info(f"🧠 Knowledge Base initialized for project: {project_name}")
        
        print(f"🧠 Knowledge Base: {project_name}")
        
        # Show knowledge base statistics
        kb_stats = self.knowledge_base.get_statistics()
        print(f"   📊 Previous content suggestions: {kb_stats['total_content_suggestions']}")
        print(f"   📊 Previous keyword clusters: {kb_stats['total_keyword_clusters']}")
        
        try:
            # Step 1: Select Excel files
            print_section("Select Input Files", "1/7")
            selected_files = self.file_selector.select_files_interactive()
            
            if not selected_files:
                print("\n❌ No files selected. Exiting...")
                return
            
            # Step 2: Get sitemap configuration
            print_section("Sitemap Configuration", "2/7")
            sitemap_url = self.sitemap_manager.get_sitemap_url_interactive()
            sitemap_urls = self.sitemap_manager.download_and_parse_sitemap(sitemap_url)
            
            if not sitemap_urls:
                print("\n⚠️  No URLs extracted from sitemap. Continuing without URL matching...")
                sitemap_urls = []
            
            # Process each selected file
            for file_idx, excel_file in enumerate(selected_files, 1):
                print_section(f"Processing File: {excel_file.name}", f"{file_idx}/{len(selected_files)}")
                
                # Step 3: Load Search Console data
                print(f"\n[3/7] Loading Search Console data from {excel_file.name}...")
                search_data = self.data_loader.load_search_console_data(str(excel_file))
                
                # Apply test mode limit
                if test_mode:
                    search_data = search_data.head(10)
                    print(f"🧪 TEST MODE: Limited to {len(search_data)} queries")
                
                print(f"✅ Loaded {len(search_data)} queries")
                
                # Step 4: Identify opportunities
                print(f"\n[4/7] Identifying content opportunities...")
                opportunities = self.analyzer.identify_opportunities(search_data)
                opportunities = self.analyzer.calculate_opportunity_score(opportunities)
                opportunities = self.analyzer.filter_high_potential_queries(opportunities, min_impressions=10)
                
                print(f"✅ Found {len(opportunities)} high-potential opportunities")
                
                # Step 5: Match queries to URLs
                print(f"\n[5/7] Matching queries to existing URLs...")
                matched_queries, unmatched_queries = self.analyzer.match_queries_to_urls(
                    opportunities,
                    sitemap_urls
                )
                
                print(f"   📌 Matched to existing pages: {len(matched_queries)}")
                print(f"   ✨ New content opportunities: {len(unmatched_queries)}")
                
                # Step 6: Generate AI-powered improvements
                print(f"\n[6/7] Generating AI-powered suggestions...")
                
                improvements_data = []
                new_content_clusters = []
                
                # Process existing content improvements
                if len(matched_queries) > 0:
                    print(f"\n   🔄 Processing {len(matched_queries.groupby('matched_url'))} existing URLs...")
                    
                    url_groups = matched_queries.groupby('matched_url')
                    
                    for url, group in tqdm(url_groups, desc="   Analyzing pages"):
                        keywords = group['Query'].tolist()
                        avg_position = group['Position'].mean()
                        total_impressions = group['Impressions'].sum()
                        
                        # Get AI suggestions
                        ai_suggestions = self.ai_processor.generate_content_improvements(
                            url=url,
                            keywords=keywords,
                            position=avg_position,
                            impressions=total_impressions
                        )
                        
                        improvements_data.append({
                            'url': url,
                            'main_keyword': keywords[0] if keywords else '',
                            'position': avg_position,
                            'impressions': total_impressions,
                            'ai_suggestions': ai_suggestions
                        })
                    
                    print(f"   ✅ Generated {len(improvements_data)} improvement suggestions")
                    
                    # Save improvements to knowledge base
                    for improvement in improvements_data:
                        self.knowledge_base.add_improvement_suggestion(
                            url=improvement.get('url', ''),
                            keywords=[improvement.get('main_keyword', '')],
                            suggestions=improvement.get('ai_suggestions', {}),
                            current_metrics={
                                'position': improvement.get('position', 0),
                                'impressions': improvement.get('impressions', 0)
                            }
                        )
                        logger.info(f"💾 Saved improvement to KB: {improvement.get('url', 'Unknown')}")
                    
                    print(f"   💾 Saved {len(improvements_data)} improvements to Knowledge Base")
                
                # Process new content suggestions
                if len(unmatched_queries) > 0:
                    # Apply test mode limit for clustering
                    if test_mode:
                        unmatched_queries = unmatched_queries.head(10)
                        print(f"🧪 TEST MODE: Limited clustering to {len(unmatched_queries)} keywords")
                    
                    print(f"\n   🔄 Clustering {len(unmatched_queries)} keywords for new content...")
                    
                    new_content_keywords = unmatched_queries['Query'].tolist()
                    
                    # Cluster with AI
                    ai_clusters = self.ai_processor.cluster_keywords(new_content_keywords)
                    
                    # Merge with metadata
                    new_content_clusters = self.clusterer.merge_clusters_with_metadata(
                        ai_clusters,
                        unmatched_queries
                    )
                    
                    # Validate and filter
                    new_content_clusters = self.clusterer.validate_clusters(new_content_clusters)
                    new_content_clusters = self.clusterer.extract_top_clusters(new_content_clusters, top_n=50)
                    
                    # Check for duplicates using knowledge base
                    filtered_clusters = []
                    for cluster in new_content_clusters:
                        title = cluster.get('article_title', '')
                        keywords = cluster.get('keywords', [])
                        
                        if not self.knowledge_base.is_duplicate_content(title, keywords):
                            filtered_clusters.append(cluster)
                        else:
                            logger.info(f"🚫 Skipped duplicate cluster: {title}")
                    
                    new_content_clusters = filtered_clusters
                    print(f"   🚫 Filtered {len(new_content_clusters)} unique clusters (removed duplicates)")
                    
                    # Check if we have any clusters left after filtering
                    if len(new_content_clusters) == 0:
                        print(f"\n⚠️  All clusters were filtered as duplicates!")
                        print(f"   This might be because:")
                        print(f"   - Similar content was already generated")
                        print(f"   - Duplicate detection is too strict")
                        
                        # Ask user what to do
                        if not test_mode:
                            retry_choice = input(f"\n🔧 What would you like to do?\n"
                                               f"   [1] Lower duplicate detection threshold (allow more similar content)\n"
                                               f"   [2] Generate clusters with different parameters\n"
                                               f"   [3] Skip clustering and continue\n"
                                               f"   Your choice (1-3): ").strip()
                            
                            if retry_choice == "1":
                                print(f"\n🔄 Retrying with lower duplicate threshold...")
                                # Retry with lower threshold on original clusters
                                filtered_clusters = []
                                for cluster in new_content_clusters:
                                    title = cluster.get('article_title', '')
                                    keywords = cluster.get('keywords', [])
                                    
                                    if not self.knowledge_base.is_duplicate_content(title, keywords, threshold=0.85):
                                        filtered_clusters.append(cluster)
                                
                                new_content_clusters = filtered_clusters
                                print(f"   ✅ Retry successful: {len(new_content_clusters)} clusters")
                                
                            elif retry_choice == "2":
                                print(f"\n🔄 Retrying clustering with different AI parameters...")
                                # Retry clustering with different temperature
                                original_temp = self.ai_processor.temperature
                                self.ai_processor.temperature = 0.3  # Slightly more creative
                                
                                try:
                                    ai_clusters_retry = self.ai_processor.cluster_keywords(new_content_keywords)
                                    new_content_clusters_retry = self.clusterer.merge_clusters_with_metadata(
                                        ai_clusters_retry, unmatched_queries
                                    )
                                    new_content_clusters_retry = self.clusterer.validate_clusters(new_content_clusters_retry)
                                    new_content_clusters = new_content_clusters_retry[:50]
                                    print(f"   ✅ Retry successful: {len(new_content_clusters)} clusters")
                                finally:
                                    self.ai_processor.temperature = original_temp
                                    
                            else:
                                print(f"   ⏭️  Skipping clustering...")
                                new_content_clusters = []
                        else:
                            print(f"   ⏭️  Test mode: Skipping clustering...")
                            new_content_clusters = []
                    
                    print(f"   ✅ Created {len(new_content_clusters)} new content suggestions")
                    
                    # Save clusters to knowledge base
                    for cluster in new_content_clusters:
                        self.knowledge_base.add_generated_content(
                            title=cluster.get('article_title', ''),
                            keywords=cluster.get('keywords', []),
                            content_type=cluster.get('content_type', ''),
                            predicted_impressions=cluster.get('recommended_word_count', 1000),
                            cluster_info=cluster
                        )
                        logger.info(f"💾 Saved cluster to KB: {cluster.get('main_topic', 'Unknown')}")
                    
                    print(f"   💾 Saved {len(new_content_clusters)} clusters to Knowledge Base")
                
                # Step 7: Generate Excel reports
                print(f"\n[7/7] Generating Excel reports...")
                
                file_stem = excel_file.stem
                
                if improvements_data:
                    improvements_file = self.excel_writer.write_existing_content_improvements(
                        improvements_data,
                        filename=f"improvements_{file_stem}.xlsx"
                    )
                    print(f"   ✅ Created: {Path(improvements_file).name}")
                
                if new_content_clusters:
                    suggestions_file = self.excel_writer.write_new_content_suggestions(
                        new_content_clusters,
                        filename=f"new_content_{file_stem}.xlsx"
                    )
                    print(f"   ✅ Created: {Path(suggestions_file).name}")
                
                print(f"\n{'='*70}")
                print(f"✅ COMPLETED: {excel_file.name}")
                print(f"{'='*70}")
            
            # Final summary
            print_section("🎉 ALL FILES PROCESSED SUCCESSFULLY!")
            print(f"📁 Output directory: {self.excel_writer.output_dir.absolute()}")
            print(f"📊 Processed {len(selected_files)} file(s)")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Process interrupted by user")
            logger.info("Process interrupted by user")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
            print(f"\n\n❌ Fatal error: {str(e)}")
            sys.exit(1)
    
    def run_seo_data_collection(self, test_mode: bool = False):
        """
        Run SEO data collection mode to scrape page titles and meta tags.
        
        This mode:
        1. Downloads sitemap(s)
        2. Scrapes each URL for SEO data
        3. Saves results to separate Excel files per sitemap
        4. Supports resume functionality
        
        Args:
            test_mode: If True, limit to 10 pages per sitemap
        """
        print_banner()
        print("🔍 MODE: SEO Data Collection (Page Scraping)")
        
        if test_mode:
            print("🧪 TEST MODE ENABLED: Will scrape only 10 pages\n")
        
        try:
            # Step 1: Get sitemap configuration
            print_section("Sitemap Configuration", "1/2")
            sitemap_url = self.sitemap_manager.get_sitemap_url_interactive()
            sitemap_urls = self.sitemap_manager.download_and_parse_sitemap(sitemap_url)
            
            if not sitemap_urls:
                print("\n❌ No URLs found in sitemap. Exiting...")
                return
            
            # Step 2: Scrape pages
            print_section("Scraping SEO Data", "2/2")
            
            output_file = self.page_scraper.scrape_urls_batch(
                urls=sitemap_urls,
                sitemap_url=sitemap_url,
                test_mode=test_mode
            )
            
            # Final summary
            print_section("🎉 SCRAPING COMPLETED!")
            print(f"📁 Output file: {output_file.absolute()}")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Process interrupted by user")
            print("   You can resume by running the program again.")
            logger.info("Scraping interrupted by user")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
            print(f"\n\n❌ Fatal error: {str(e)}")
            sys.exit(1)
    
    def run_content_generation(self):
        """
        Run content generation workflow.
        
        This mode:
        1. Reads headings from Excel output files
        2. Generates AI content for each heading
        3. Adds internal links based on sitemap
        4. Exports to Excel, Word, and HTML
        """
        print_banner()
        print("✍️  MODE: AI Content Generation")
        
        try:
            # Step 1: Initialize AI Model Manager
            print_section("AI Model Configuration", "1/6")
            
            model_manager = AIModelManager(config_path='config.yaml')
            
            # Test connections
            model_manager.test_all_connections()
            
            # Ask if user wants to use default for all operations
            use_default = model_manager.use_default_for_all()
            
            # Step 2: Select input Excel file from output directory
            print_section("Select Input Excel File from Output Folder", "2/6")
            print("📁 Reading files from: output/")
            print("   (These are Excel files generated from content optimization mode)")
            print()
            
            selected_files = self.file_selector.select_files_interactive(custom_dir="output")
            
            if not selected_files:
                print("\n❌ No files selected. Exiting...")
                print("\n💡 Tip: Run content optimization mode first to generate Excel files:")
                print("   python3 main.py --mode content")
                return
            
            excel_file = selected_files[0]  # Process first file
            print(f"\n✅ Selected: {excel_file.name}")
            
            # Step 3: Get project information
            print_section("Project Information", "3/6")
            project_name = get_project_name_interactive()
            
            # Step 4: Select AI model for content generation
            print_section("Select AI Model for Content Generation", "4/6")
            
            if use_default:
                content_model = model_manager.get_default_model()
                print(f"✅ Using default model: {content_model.name}")
            else:
                content_model = model_manager.select_model_interactive(
                    purpose="Content Generation"
                )
            
            if not content_model:
                print("\n❌ No model selected. Exiting...")
                return
            
            # Step 5: Read Excel and generate content row by row
            print_section("Generate Content", "5/6")
            
            content_generator = ContentGenerator(self.config)
            
            # Read Excel with headers
            df = content_generator.read_excel_with_headers(str(excel_file))
            
            print(f"📊 Found {len(df.columns)} columns:")
            
            # Categorize columns
            topic_columns = []
            heading_columns = []
            other_columns = []
            
            for i, col in enumerate(df.columns):
                if i == 0:  # First column is topic
                    topic_columns.append((i+1, col))
                elif "هدینگ H2" in str(col):
                    heading_columns.append((i+1, col))
                else:
                    other_columns.append((i+1, col))
            
            # Display categorized columns
            print(f"\n   📌 Topic Column:")
            for idx, col in topic_columns:
                print(f"      [{idx}] {col}")
            
            if other_columns:
                print(f"\n   📋 Other Columns:")
                for idx, col in other_columns:
                    print(f"      [{idx}] {col}")
            
            print(f"\n   🎯 Heading Columns (H2):")
            for idx, col in heading_columns:
                print(f"      [{idx}] {col}")
            
            print(f"\n📝 Total articles to process: {len(df)}")
            print(f"   📌 Topic from: Column 1")
            print(f"   🎯 Headings from: {len(heading_columns)} H2 columns")
            
            # Confirm
            confirm = input(f"\nStart generating content for {len(df)} article(s)? (Y/n): ").strip().lower()
            if confirm in ['n', 'no']:
                print("❌ Generation cancelled")
                return
            
            # Get content generation instructions
            print(f"\n{'='*70}")
            print(f"📝 Content Generation Instructions")
            print(f"{'='*70}")
            print("You can provide additional instructions for content generation.")
            print("Examples:")
            print("  - 'Include FAQ sections'")
            print("  - 'Add step-by-step guides'")
            print("  - 'Include product comparisons'")
            print("  - 'Add safety warnings'")
            print("  - 'Use more technical language'")
            print("  - 'Focus on beginner-friendly explanations'")
            
            content_instructions = input("\nAdditional content instructions (press Enter to skip): ").strip()
            
            if content_instructions:
                print(f"✅ Content instructions added: {content_instructions[:50]}...")
            else:
                print("✅ Using default content generation prompts")
            
            # Process each row
            generated_articles = []
            
            for idx, row in df.iterrows():
                # Extract topic and headings
                main_topic, headings = content_generator.extract_topic_and_headings(row)
                
                if not main_topic or not headings:
                    print(f"\n⚠️  Row {idx + 1}: No topic or headings found, skipping")
                    continue
                
                # Generate article interactively
                article = content_generator.generate_article_interactive(
                    row_index=idx,
                    main_topic=main_topic,
                    headings=headings,
                    project_name=project_name,
                    ai_model=content_model,
                    total_rows=len(df),
                    content_instructions=content_instructions
                )
                
                if article:
                    generated_articles.append(article)
            
            if not generated_articles:
                print("\n❌ No content generated")
                return
            
            print(f"\n{'='*70}")
            print(f"✅ Generated {len(generated_articles)} article(s)")
            print(f"{'='*70}")
            
            # Step 6: Add internal links and export
            print_section("Internal Linking & Export", "6/6")
            
            # Ask about internal linking
            print(f"\n{'='*70}")
            print(f"🔗 Internal Linking")
            print(f"{'='*70}")
            add_links = input("\nAdd internal links to content? (Y/n): ").strip().lower()
            
            linker = None
            if add_links not in ['n', 'no']:
                # Get sitemap
                sitemap_url = self.sitemap_manager.get_sitemap_url_interactive()
                sitemap_urls = self.sitemap_manager.download_and_parse_sitemap(sitemap_url)
                
                if sitemap_urls:
                    print(f"\n✅ Loaded {len(sitemap_urls)} URLs from sitemap")
                    
                    # Initialize internal linker
                    linker = InternalLinker(sitemap_urls)
                    
                    # Show statistics
                    stats = linker.get_statistics()
                    print(f"\n📊 URL Statistics:")
                    for url_type, count in stats['by_type'].items():
                        print(f"   - {url_type}: {count}")
                    
                    print(f"\n🔄 Adding internal links to articles...")
                    
                    # Add links to each article
                    for article in generated_articles:
                        linked_content = linker.add_internal_links(
                            content_html=article['full_content'],
                            max_links=None,
                            words_per_link=(300, 400)
                        )
                        article['full_content'] = linked_content
                    
                    print(f"✅ Internal links added to {len(generated_articles)} article(s)")
                else:
                    print(f"\n⚠️  No URLs found in sitemap, skipping internal linking")
            
            # Export to Word and HTML
            print(f"\n{'='*70}")
            print(f"📄 Export to Word & HTML")
            print(f"{'='*70}")
            
            export = input("\nExport content to Word and HTML files? (Y/n): ").strip().lower()
            
            word_files = []
            html_files = []
            
            if export not in ['n', 'no']:
                exporter = DocumentExporter(output_dir="output/documents")
                
                print(f"\n🔄 Exporting {len(generated_articles)} article(s)...")
                
                for i, article in enumerate(generated_articles, 1):
                    # Clean topic for filename
                    safe_topic = re.sub(r'[^\w\s-]', '', article['main_topic'])
                    safe_topic = re.sub(r'[-\s]+', '-', safe_topic)[:50]
                    filename = f"content_{project_name}_{i}_{safe_topic}"
                    
                    # Export to Word
                    try:
                        print(f"  📝 Creating Word file for article {i}...")
                        word_file = exporter.export_content_to_word(
                            title=article['seo_title'],
                            meta_description=article['meta_description'],
                            content_html=article['full_content'],
                            output_filename=filename
                        )
                        word_files.append(word_file)
                        print(f"  ✅ Word file created: {Path(word_file).name}")
                    except Exception as e:
                        print(f"  ❌ Word export failed for article {i}: {e}")
                        logger.error(f"Word export failed for article {i}: {e}")
                    
                    # Export to HTML
                    try:
                        html_file = exporter.export_content_to_html(
                            title=article['seo_title'],
                            meta_description=article['meta_description'],
                            content_html=article['full_content'],
                            output_filename=filename
                        )
                        html_files.append(html_file)
                    except Exception as e:
                        logger.error(f"HTML export failed for article {i}: {e}")
                
                print(f"\n✅ Export complete!")
                print(f"   📝 Word files: {len(word_files)}")
                print(f"   🌐 HTML files: {len(html_files)}")
            
            # Calculate total words
            total_words = sum(a['word_count'] for a in generated_articles)
            
            # Final summary
            print_section("🎉 CONTENT GENERATION COMPLETED!")
            print(f"📊 Statistics:")
            print(f"   Total articles: {len(generated_articles)}")
            print(f"   Total words generated: {total_words:,}")
            print(f"\n📁 Output files:")
            print(f"   Word documents: output/documents/")
            print(f"   HTML files: output/documents/")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Process interrupted by user")
            logger.info("Content generation interrupted by user")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Fatal error: {str(e)}", exc_info=True)
            print(f"\n\n❌ Fatal error: {str(e)}")
            sys.exit(1)
    
    def run_internal_linking_only(self):
        """
        Mode 4: Add internal links to existing content files.
        
        This mode reads existing HTML/Word files and adds internal links to them
        using the internal linking system.
        """
        print_banner()
        print("🔗 MODE: Internal Linking Only")
        
        try:
            # Step 1: Select content files
            print_section("Content File Selection", "1/4")
            print(f"\n{'='*70}")
            print(f"📁 Content File Selection")
            print(f"{'='*70}")
            print("Select content files to add internal links to:")
            print("  - HTML files (.html)")
            print("  - Word files (.docx)")
            print("  - Text files (.txt)")
            
            # Get files from documents folder
            documents_dir = Path("output/documents")
            if not documents_dir.exists():
                print(f"❌ Documents directory not found: {documents_dir}")
                return
            
            content_files = []
            for ext in ['*.html', '*.docx', '*.txt']:
                content_files.extend(documents_dir.glob(ext))
            
            if not content_files:
                print(f"❌ No content files found in {documents_dir}")
                print("   Please add HTML, Word, or text files to this directory first.")
                return
            
            print(f"\n📊 Found {len(content_files)} content file(s):")
            for i, file in enumerate(content_files, 1):
                print(f"  [{i}] {file.name} ({file.stat().st_size} bytes)")
            
            # File selection
            while True:
                try:
                    selection = input(f"\nSelect files (1-{len(content_files)}, 'all', or comma-separated): ").strip()
                    
                    if selection.lower() == 'all':
                        selected_files = content_files
                        break
                    else:
                        indices = [int(x.strip()) - 1 for x in selection.split(',')]
                        if all(0 <= i < len(content_files) for i in indices):
                            selected_files = [content_files[i] for i in indices]
                            break
                        else:
                            print("❌ Invalid selection. Please try again.")
                except ValueError:
                    print("❌ Invalid input. Please enter numbers or 'all'.")
            
            print(f"✅ Selected {len(selected_files)} file(s)")
            
            # Step 2: Get sitemap for internal linking
            print_section("Sitemap Configuration", "2/4")
            sitemap_url = self.sitemap_manager.get_sitemap_url_interactive()
            sitemap_urls = self.sitemap_manager.download_and_parse_sitemap(sitemap_url)
            
            if not sitemap_urls:
                print("❌ No URLs found in sitemap")
                return
            
            # Step 3: Setup internal linker
            print_section("Internal Linking Setup", "3/4")
            linker = InternalLinker(sitemap_urls)
            
            print(f"\n✅ Loaded {len(linker.urls)} URLs from sitemap")
            stats = linker.get_statistics()
            print(f"📊 URL Statistics:")
            for url_type, count in stats['by_type'].items():
                print(f"   - {url_type}: {count}")
            
            # Step 4: Process files
            print_section("Adding Internal Links", "4/4")
            
            processed_files = []
            for i, file_path in enumerate(selected_files, 1):
                print(f"\n📝 Processing file {i}/{len(selected_files)}: {file_path.name}")
                
                try:
                    # Read content based on file type
                    if file_path.suffix.lower() == '.html':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    elif file_path.suffix.lower() == '.docx':
                        # For Word files, we'd need to extract text first
                        # For now, skip Word files and focus on HTML
                        print("⚠️  Word file processing not implemented yet. Skipping...")
                        continue
                    elif file_path.suffix.lower() == '.txt':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                    else:
                        print(f"⚠️  Unsupported file type: {file_path.suffix}")
                        continue
                    
                    # Add internal links
                    linked_content = linker.add_internal_links(content)
                    
                    # Save updated content
                    output_file = file_path.parent / f"{file_path.stem}_linked{file_path.suffix}"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(linked_content)
                    
                    processed_files.append(output_file)
                    print(f"✅ Added internal links: {output_file.name}")
                    
                except Exception as e:
                    print(f"❌ Failed to process {file_path.name}: {e}")
                    logger.error(f"Failed to process {file_path.name}: {e}")
                    continue
            
            # Summary
            print(f"\n{'='*70}")
            print(f"🎉 Internal Linking Complete!")
            print(f"{'='*70}")
            print(f"📁 Processed {len(processed_files)} file(s)")
            print(f"📂 Output directory: output/documents/")
            print(f"🔗 Internal links added using {len(linker.urls)} URLs from sitemap")
            
            if processed_files:
                print(f"\n📋 Generated files:")
                for file in processed_files:
                    print(f"   ✅ {file.name}")
            
        except Exception as e:
            logger.error(f"Fatal error in internal linking mode: {e}")
            print(f"\n❌ Fatal error: {e}")
            raise
    
    def run_synonym_finder(self):
        """
        Mode 5: Find semantic equivalents for keywords.
        
        This mode reads keywords from Excel and finds all possible variations including:
        Persian synonyms, Finglish, keyboard typing, misspellings, etc.
        """
        print_banner()
        print("🔍 MODE: Keyword Synonym Finder")
        
        try:
            # Step 1: Initialize AI Model Manager
            print_section("AI Model Configuration", "1/4")
            
            model_manager = AIModelManager(config_path='config.yaml')
            
            # Test connections
            model_manager.test_all_connections()
            
            # Ask if user wants to use default for all operations
            use_default = model_manager.use_default_for_all()
            
            # Step 2: Select input Excel file
            print_section("Select Input Excel File", "2/4")
            print("📁 Reading files from: input/")
            print("   (Excel files with keywords in first column)")
            print()
            
            selected_files = self.file_selector.select_files_interactive(custom_dir="input")
            
            if not selected_files:
                print("\n❌ No files selected. Exiting...")
                return
            
            excel_file = selected_files[0]  # Process first file
            print(f"\n✅ Selected: {excel_file.name}")
            
            # Step 3: Select AI model
            print_section("Select AI Model for Synonym Finding", "3/4")
            
            if use_default:
                synonym_model = model_manager.get_default_model()
                print(f"✅ Using default model: {synonym_model.name}")
            else:
                synonym_model = model_manager.select_model_interactive(
                    purpose="Synonym Finding"
                )
            
            if not synonym_model:
                print("\n❌ No model selected. Exiting...")
                return
            
            # Step 4: Process keywords
            print_section("Finding Semantic Equivalents", "4/4")
            
            synonym_finder = SynonymFinder(self.config)
            
            output_file = synonym_finder.process_excel_file(
                excel_path=str(excel_file),
                ai_model=synonym_model,
                output_dir="output/synonyms"
            )
            
            # Final summary
            print_section("🎉 SYNONYM FINDING COMPLETED!")
            print(f"📁 Output file: {output_file}")
            print(f"\n💡 Tip: Use these synonyms to:")
            print(f"   - Optimize your content for different search variations")
            print(f"   - Cover all possible ways users might search")
            print(f"   - Improve SEO with comprehensive keyword coverage")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Process interrupted by user")
            logger.info("Synonym finding interrupted by user")
            sys.exit(0)
            
        except Exception as e:
            logger.error(f"Fatal error in synonym finding mode: {e}")
            print(f"\n❌ Fatal error: {e}")
            raise

    def run_index_diff(
        self,
        domain: Optional[str] = None,
        import_file: Optional[str] = None,
        mark_submitted: bool = False,
    ) -> None:
        """
        Compare sitemap URLs against previously submitted indexing URLs.

        Input:
            domain: Optional domain/project name (prompted when missing).
            import_file: Optional text file of previously submitted URLs.
            mark_submitted: Mark exported new URLs as submitted after export.

        Output:
            Writes diff text files under output/index_diff/{domain}/.
        """
        print_banner()
        print("MODE: URL Index Diff")

        try:
            if not domain:
                print_section("Domain / Project", "1/4")
                domain = get_project_name_interactive()

            tracker = UrlIndexTracker(domain)

            if import_file:
                added = tracker.import_from_txt(import_file)
                print(f"Imported {added} URL(s) from {import_file}")

            status = tracker.get_status()
            print_section("Current Status", "2/4")
            print(f"Domain: {status['domain']}")
            print(f"Previously submitted: {status['total_submitted']}")
            print(f"Last sitemap fetch: {status['last_sitemap_fetch'] or 'never'}")

            print_section("Sitemap Fetch", "3/4")
            sitemap_url = self.sitemap_manager.get_sitemap_url_interactive()
            current_urls = self.sitemap_manager.download_and_parse_sitemap(sitemap_url)

            if not current_urls:
                print("No URLs found in sitemap. Exiting...")
                return

            new_urls, already_urls = tracker.diff(current_urls)

            print_section("Diff Results", "4/4")
            print(f"Total sitemap URLs: {len(current_urls)}")
            print(f"New URLs: {len(new_urls)}")
            print(f"Already submitted: {len(already_urls)}")

            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_dir = Path("output") / "index_diff" / tracker._sanitize_name(domain)
            new_file = tracker.export_txt(
                new_urls, output_dir / f"new_urls_{stamp}.txt"
            )
            already_file = tracker.export_txt(
                already_urls, output_dir / f"already_submitted_{stamp}.txt"
            )

            print(f"Exported new URLs: {new_file}")
            print(f"Exported already submitted: {already_file}")

            if mark_submitted and new_urls:
                batch_id = tracker.mark_batch_submitted(
                    new_urls, source_file=new_file.name
                )
                print(f"Marked {len(new_urls)} URL(s) as submitted (batch {batch_id})")
            elif new_urls:
                choice = input(
                    "\nMark new URLs as submitted to indexing tool? (y/N): "
                ).strip().lower()
                if choice in ("y", "yes"):
                    batch_id = tracker.mark_batch_submitted(
                        new_urls, source_file=new_file.name
                    )
                    print(
                        f"Marked {len(new_urls)} URL(s) as submitted (batch {batch_id})"
                    )

            print_section("URL Index Diff Completed")
            print("Give new_urls_*.txt to your indexing tool.")

        except KeyboardInterrupt:
            print("\nProcess interrupted by user")
            logger.info("Index diff interrupted by user")
            sys.exit(0)
        except Exception as exc:
            logger.error("Fatal error in index diff mode: %s", exc, exc_info=True)
            print(f"Fatal error: {exc}")
            sys.exit(1)


# Backward-compatible alias for older imports and scripts.
SEOContentOptimizer = SeoToolkit

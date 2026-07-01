# Changelog - Seo Toolkit

All notable changes to this project will be documented in this file.

## v2.9.1 (2025-07-01)

### Fix — task page 500 (Undefined is not JSON serializable)
- Safe i18n merge (EN fallback) for template strings
- `default` filter on task page `tojson` labels

## v2.9.0 (2025-07-01)

### Index Diff — downloadable file list and URL status archive
- Each diff run registers all output files with download links
- `url_status.csv` / `.json` per run — status: indexed, pending_index, excluded
- Export history on Index Diff page and task completion page
- `GET /api/v1/index-diff/files/{domain}` and `/download?path=`

## v2.8.0 (2025-07-01)

### Index Diff — sitemap snapshots, batch marking, sticky project
- Save full sitemap URL list (`sitemap_latest.txt` + dated archives)
- Optional import checkbox: register as indexed or diff-only exclusion
- Mark last diff batch or upload txt after indexing tool submission
- Sticky project via cookie + `?project=` on all nav links
- Sidebar status: sitemap count, submitted, pending batch

## v2.7.1 (2025-07-01)

### Fix — Index Diff `Not Found` on stale server
- Fallback to legacy diff flow when `/api/v1/jobs/index-diff/start` returns 404
- Clear hint to restart `./scripts/run_web.sh` for the progress page

## v2.7.0 (2025-07-01)

### Index Diff — recursive sitemaps, task progress page, background jobs
- **Recursive sub-sitemap expansion** in browser (nested sitemap indexes, relative `<loc>` URLs)
- **Server proxy** `/api/v1/sitemap/proxy` when CORS blocks sub-sitemap downloads
- **Background jobs** API (`POST /api/v1/jobs/index-diff/start`) with polling
- **Progress page** `/tasks/{job_id}` — progress bar, step list, done message

## v2.6.9 (2025-07-01)

### Index Diff — visible progress and browser sitemap index expansion
- Persistent progress panel + sidebar status (no silent “processing” disappear)
- Browser downloads full sitemap index + sub-sitemaps, sends URL list to server
- API accepts `urls_file` txt to skip server-side download

## v2.6.8 (2025-07-01)

### Fix — Index Diff 502 when browser can open sitemap
- Web UI fetches sitemap URL **in the browser** (CORS) and uploads XML to the server
- Avoids Python/server DNS issues when Terminal `curl` works but uvicorn cannot download

## v2.6.7 (2025-07-01)

### Fix — Index Diff `Not Found` (404)
- Stale uvicorn missed `/api/v1/index-diff/diff-form`; restart with `./scripts/run_web.sh`
- Web UI falls back to JSON `/diff` if `/diff-form` returns 404

## v2.6.6 (2025-07-01)

### Fix — sitemap download when curl works but Python fails
- `run_web.sh` unsets IDE-injected HTTP_PROXY before starting uvicorn
- HTTP client forces direct connection (no accidental Cursor proxy)
- macOS curl fallback when `requests` cannot resolve/connect (matches Terminal `curl` behavior)

## v2.6.5 (2025-06-30)

### Fix — blocked sitemap hosts (e.g. sargarmia.com)
- Shared HTTP client: browser headers, `trust_env=False` by default, optional `app.http_proxy` in config.yaml
- HTTPS→HTTP fallback and clearer connection errors
- **Upload sitemap.xml** on Index Diff when download fails (Save As from browser)
- Web uses `POST /api/v1/index-diff/diff-form` (URL and/or file)

## v2.6.4 (2025-06-30)

### Fix — sitemap download failures in web Index Diff
- Browser-like `User-Agent` and headers for sitemap HTTP requests
- Web diff uses non-interactive `fetch_all_sitemap_urls` (no CLI prompts on sitemap index)
- Auto-fetch all sub-sitemaps from sitemap index
- Namespace-agnostic XML parsing fallback
- Detailed 502 error message (SSL, 403, timeout, etc.)

## v2.6.3 (2025-06-30)

### Fix — Index Diff import `[object Object]` error toast
- Parse FastAPI validation errors (`detail` array) into readable messages
- Build multipart FormData explicitly for multiple txt files

## v2.6.2 (2025-06-30)

### Fix — Index Diff page 500 error
- Removed fragile `tojson` in template (caused `Undefined is not JSON serializable` on stale reload)
- Import labels passed via `data-*` attributes with safe defaults

## v2.6.1 (2025-06-30)

### Index Diff — multi-file import (web)
- Upload **multiple `.txt` files at once** on `/tools/index-diff`
- API accepts `urls_files[]` and returns per-file + total counts
- New `UrlIndexTracker.import_from_txt_files()` helper

## v2.6.0 (2025-06-30)

### Multi-project support
- Define multiple projects with isolated data folders under `projects/{slug}/`
- Each project: separate `input/`, `output/`, `knowledge_base/`, `index_history/`, `sitemaps/`
- CLI: `--project my-slug` flag on all modes
- Web: `/projects` page, project switcher in header, per-tool project select
- API: `GET/POST /api/v1/projects`
- Docs: `docs/MULTI_PROJECT.md`, updated `ARCHITECTURE.md` and `API_MODULES.md`

## v2.5.1 (2025-06-30)

### Web UI overhaul
- Full bilingual (EN/FA) dashboard with RTL support and Vazirmatn font
- Dedicated pages for all 6 operational modes
- REST API endpoints for scraping, linking, synonyms, index-diff
- Dark modern design system with responsive layout

## v2.5.0 (2025-06-30)

### Rebrand to Seo Toolkit
- Project renamed from `simple-seo-tool` / SEO Content Analysis & Optimization Tool to **Seo Toolkit**
- New log file: `logs/seo_toolkit.log`
- `SEOContentOptimizer` alias kept; primary class is `SeoToolkit`

### Architecture refactor
- Thin `main.py` CLI entry
- `src/app/toolkit.py` application core
- `src/cli/` prompts, sections, logging setup
- `src/services/url_index_tracker.py` shared service layer
- `docs/` architecture, installation, API modules

### New Mode 6: URL Index Diff
- Compare sitemap URLs against previously submitted indexing URLs
- Per-domain history in `index_history/`
- Export `new_urls_*.txt` and `already_submitted_*.txt`
- CLI flags: `--domain`, `--import`, `--mark-submitted`
- See `docs/INDEX_DIFF.md`

### Web MVP (FastAPI)
- Dashboard at `/`
- Index diff UI at `/index-diff`
- REST API at `/api/v1/index-diff/*` and `/docs`

### Tests
- pytest suite for analyzer, sitemap parser, knowledge base, URL tracker

## v2.4.0 (2024-10-13)

### ✨ New Mode 5: Keyword Synonym Finder 🔍

**Major Feature:**
- Find all semantic equivalents for keywords using AI
- Support for 8 categories of variations:
  1. Persian synonyms (مترادف‌های فارسی)
  2. Finglish standard (گوشی → gooshi, gushi)
  3. English keyboard typing (گوشی → ',ad)
  4. Colloquial abbreviations (اختصارات عامیانه)
  5. Common misspellings (غلط‌های املایی رایج)
  6. English equivalents (معادل انگلیسی)
  7. Abbreviations (مخفف‌ها)
  8. Related terms (واژگان مرتبط)

**How it Works:**
- Read keywords from Excel file (column 1)
- AI generates all possible variations
- Output Excel with 9 columns (original + 8 variation types)
- Comprehensive keyword coverage for SEO

**Use Cases:**
- Optimize content for all search variations
- Cover different ways users might search
- Improve keyword coverage
- Content localization and variations

### 📝 Content Generation Improvements

**Enhanced Prompts:**
- Stronger emphasis on NO conclusion per heading
- Clear instruction that conclusion comes ONLY at end
- Prevent phrases like "در نتیجه", "خلاصه" in section endings
- Added <p> tag instruction for clean HTML
- Improved conclusion prompt for comprehensive summary

**Result:**
- Clean, flowing content without multiple conclusions
- Single comprehensive conclusion at article end
- Better HTML rendering in browser

### 🔗 Internal Linking Improvements

**Duplicate Link Prevention:**
- Added final cleanup pass to remove duplicate URL links
- Keeps only first occurrence of each URL
- Replaces duplicate links with plain anchor text
- Better protection against same URL with different anchor texts

---

## v2.3.3 (2024-10-13)

### Added
- **New Mode 4: Internal Linking Only** 🔗
  - Standalone internal linking for existing content files
  - Supports HTML, Word (.docx), and text files
  - Interactive file selection from output/documents folder
  - Automatic link distribution and relevance checking
  - Preserves original file structure while adding internal links

### Enhanced
- **Content Generation Instructions**
  - Users can now provide additional content generation instructions
  - Instructions are automatically included in AI prompts
  - Supports custom structure requirements (FAQ, step-by-step guides, etc.)

### Fixed
- **Internal Linking Improvements**
  - Fixed KeyError for 'other' URL type in link distribution
  - Enhanced semantic matching for Persian content
  - Improved anchor text selection with 2-3 syllable product name priority
  - Even distribution of links throughout content (not just beginning/end)
  - One link per destination page limit implemented
  - Better relevance scoring with exact matches and keyword bonuses

### Technical
- Added comprehensive content harmony checking
- Enhanced error handling and user feedback
- Improved file export status reporting
- Better debugging and logging for internal linking process

## [2.3.2] - 2024-10-13

### 🔗 Advanced Internal Linking System

#### Smart Product Name Linking
- **2-3 Syllable Priority**: First 2-3 words of product names get highest priority for linking
- **Product Name Recognition**: 50+ Persian product words with syllable-based matching
- **Semantic Anchor Text**: Intelligent selection based on product relevance and context
- **Example**: "بذر پیاز سفید گرانوله" → links "بذر پیاز" (not "سفید")

#### Even Link Distribution
- **Content-Wide Spacing**: Links distributed evenly across entire content, not clustered
- **Two-Pass Algorithm**: First identifies all potential links, then selects for even distribution
- **Target Spacing**: Calculates optimal spacing based on content length and link count
- **Quality Preservation**: Maintains high-quality matches while ensuring even spread

#### Enhanced Word Export
- **Better Error Handling**: Added detailed logging for Word export process
- **Progress Feedback**: Real-time status updates during document creation
- **Exception Recovery**: Graceful handling of export failures with clear error messages

### Technical Improvements
- Enhanced `_find_best_anchor_text()` with product name prioritization
- Added `_find_semantic_anchor_text()` for 2-3 syllable product word matching
- Implemented `_select_links_with_even_distribution()` for optimal link placement
- Improved Persian product word database with syllable classification

---

## [2.3.1] - 2024-10-13

### 🔧 Bug Fixes & Improvements

#### Internal Linking System Enhancement
- **Improved Semantic Matching**: Enhanced algorithm for better content-to-URL relevance
- **Persian Word Relationships**: Added semantic groups for Persian content (گل، بذر، کاشت، آبیاری، خاک، کود، باغچه)
- **Better Phrase Matching**: Exact phrase matches now get 0.8 score (was lower)
- **Partial Word Support**: Added support for partial keyword matches (0.2 score)
- **URL Path Relevance**: URLs with matching terms in path get bonus points
- **Lowered Threshold**: Reduced matching threshold from 0.3 to 0.15 for more links
- **Debug Information**: Added detailed logging for link match scores and URLs

#### Word Export Fix
- **Fixed Missing Dependency**: Installed python-docx package (was causing ModuleNotFoundError)
- **Word Document Creation**: Fixed Word export functionality that was completely broken
- **Document Exporter**: Now fully functional for creating .docx files

#### Version Management
- **Dynamic Version Reading**: main.py now reads version from VERSION file automatically
- **Version File Update**: Updated VERSION file to 2.3.1
- **Banner Update**: Application banner now shows current version dynamically

### Technical Details
- Enhanced `_calculate_match_score()` method with better Persian language support
- Added `_has_semantic_similarity()` method for context-aware linking
- Improved debug logging throughout internal linking process
- Fixed python-docx import error in DocumentExporter

---

## [2.3.0] - 2024-10-12

### 🔧 Updates & Improvements (2024-10-13)

#### Content Generation Workflow Redesign
- **Automatic Topic Reading**: Main topic automatically read from first column (no manual input)
- **Header Detection**: First row treated as column headers
- **Interactive Word Count**: Ask for total article words, then distribute per heading
- **Per-Heading Generation**: Generate content for each heading separately with custom word counts
- **Introduction & Conclusion**: Automatically generated based on article content
- **Complete Articles**: Each row becomes one complete article with intro, body, and conclusion

#### Fixes
- Fixed: Content generation now reads Excel files from `output/` folder instead of `input/`
- Fixed: File selector shows files from output directory for Mode 3
- Improved: Better user guidance when no files are found

#### User Experience
- **Excel Structure**:
  - Row 1: Column headers
  - Column 1: Article topic (automatically used)
  - Columns 2-6: Additional data (predictions, clusters, content type, search intent, word count)
  - Columns 7+: H2 headings (only these used for content generation)
  - Each row = One complete article
- **Smart Column Detection**: Automatically identifies heading columns by "هدینگ H2" pattern
- **Interactive Process**: Confirm each article, set word counts, review progress
- **Smart Prompts**: Separate prompts for headings, introduction, and conclusion

### 🎉 Major Features

#### AI Content Generation System ✨ NEW
- **Content Generator**: Full Persian SEO content generation from Excel headings
- **Multi-Format Export**: Automatic export to Excel, Word (.docx), and HTML formats
- **Smart Content Prompt**: Specialized Persian SEO prompt with E-E-A-T principles
- **Natural Writing**: Random spacing variations for natural appearance
- **Batch Processing**: Process multiple headings in one run with progress tracking

#### Multi-Model AI Support 🤖 NEW
- **Multiple Provider Support**: OpenAI, Claude (Anthropic), Gemini (Google), Grok
- **Model Configuration**: Configure unlimited AI models in `config.yaml`
- **Connection Testing**: Test all configured models before use
- **Default Model**: Set a default model for all operations
- **Per-Operation Selection**: Choose different models for different tasks
- **Environment Variables**: Support for `env:VAR_NAME` to read API keys securely

#### Smart Internal Linking System 🔗 NEW
- **Sitemap Analysis**: Parse and categorize URLs from sitemap
- **URL Categorization**: Automatic detection of categories, products, blogs
- **Semantic Matching**: Links based on content relevance
- **Smart Rules Implementation**:
  - 1 link per 300-400 words
  - No links in headings
  - Priority system: Categories > Products > Blog posts
  - Anchor text optimization (max 5 syllables)
- **Fuzzy Matching**: Intelligent anchor text selection with similarity matching

#### Document Export System 📄 NEW
- **Word Export**: Formatted .docx documents with proper structure
- **HTML Export**: Editor-ready HTML (no wrapper tags)
- **SEO Information**: Separate title and meta description sections
- **Batch Export**: Export all generated content at once
- **Structure Preservation**: Maintains headings, bold text, lists, links

### 🛠️ New Modules

- `src/ai_model_manager.py`: Multi-provider AI model management
- `src/content_generator.py`: AI content generation engine
- `src/internal_linker.py`: Smart internal linking system
- `src/document_exporter.py`: Word and HTML export functionality

### 🔧 Configuration Changes

- Added `ai_models` section in `config.yaml` for multi-model configuration
- Legacy `ai` section maintained for backward compatibility
- Support for environment variable API keys with `env:` prefix

### 📦 Dependencies

- Added `python-docx>=0.8.11` for Word document generation
- Added `google-generativeai>=0.3.0` for Gemini support

### 🎨 User Interface

- New mode selection option: "AI Content Generation"
- Interactive model selection interface
- Progress bars for content generation and export
- Connection status display for all configured models
- Comprehensive statistics after content generation

### 📝 Content Generation Features

- Custom word count per heading
- Persian-aware content structure
- SEO title generation (max 60 chars)
- Meta description generation (max 160 chars)
- HTML content with proper tags (H2, H3, p, strong, ul, li, a)
- JSON response parsing with fallback
- Error handling and retry logic

### 🔗 Internal Linking Features

- URL type detection (category, product, blog, other)
- Semantic relevance scoring
- Anchor text extraction from URLs
- Distribution balancing (equal spread across types)
- Section-based link placement (avoid headers)
- Statistics reporting

### 📊 Export Features

- Excel: Combined output with SEO info and content
- Word: Formatted documents with sections
- HTML: Clean output for CMS/editors
- Batch processing with error handling
- Safe filename generation from titles

### 🐛 Bug Fixes

- Fixed pandas import in main.py for content generation
- Improved error messages for missing dependencies
- Better handling of malformed JSON responses from AI

### 📖 Documentation

- Complete README update with Mode 3 documentation
- Persian documentation for new features
- Configuration examples for all supported providers
- Workflow examples for content generation
- Troubleshooting section updates

### 🚀 Performance

- Parallel processing support for content generation
- Efficient sitemap parsing and caching
- Optimized internal link matching algorithms

---

## [2.2.3] - 2024-10-11

### 🔄 Smart Clustering & Fallback Strategy
- **Intelligent Duplicate Detection**: Improved threshold system (default 0.95, adjustable to 0.85)
- **Fallback Clustering**: Multiple retry strategies when all clusters are filtered as duplicates
- **User-Guided Recovery**: Interactive options to adjust clustering parameters
- **Test Mode Support**: Clustering now works properly in test mode with limited data
- **Threshold Adjustment**: Option to lower duplicate detection threshold on demand

### 🐛 Bug Fixes
- Fixed issue where all clusters were being filtered as duplicates
- Fixed empty output folder when clustering fails
- Improved duplicate detection algorithm to be less aggressive
- Added proper fallback when no unique clusters are found

### 🎯 Clustering Improvements
- Better duplicate detection with weighted similarity scoring
- More lenient threshold for title similarity (0.8 weight vs 0.3 for keywords)
- Interactive retry options for failed clustering attempts
- Support for different AI parameters when retrying

### 📊 User Experience
- Clear error messages when clustering fails
- Interactive recovery options instead of silent failures
- Test mode properly limits clustering data
- Better feedback on clustering success/failure

---

## [2.2.0] - 2024-10-11

### 🎯 Persian Language Optimization (Enhanced)
- **Complete Persian AI Prompts**: All AI prompts rewritten specifically for Persian content
- **Persian Search Intent**: Focus on Iranian user behavior and search patterns  
- **Farsi SEO Best Practices**: Optimized for Google's algorithms for Persian content
- **Localized Output**: All suggestions and recommendations in Persian
- **Persian URL Decoding**: Proper handling of Persian URLs in scraping mode
- **Fully Persian Excel Output**: All column headers and content in Persian

### 🔧 Technical Improvements
- **URL Encoding Fix**: Added `_decode_persian_url()` method to properly display Persian URLs
- **Enhanced AI Prompts**: Improved prompts for better Persian content suggestions
- **Excel Localization**: All Excel column headers now in Persian
- **Better Error Handling**: Improved error messages and logging

### 📊 Output Improvements
- **Persian Column Headers**: Excel files now have Persian column names
- **Enhanced Content Suggestions**: More detailed and actionable suggestions
- **Better Keyword Clustering**: Improved clustering for Persian keywords
- **Comprehensive Analysis**: More detailed analysis for existing content

### 🐛 Bug Fixes
- Fixed Persian URL encoding issues in scraping mode
- Improved AI response parsing for Persian content
- Better handling of Persian characters in Excel output
- Enhanced error messages for Persian users

### 📚 Documentation Updates
- Updated README.md for v2.2
- Enhanced Persian documentation sections
- Added troubleshooting for Persian-specific issues
- Updated examples with Persian content

### 🔄 Migration Notes
- No breaking changes from v2.1
- All existing configurations remain compatible
- Enhanced Persian support is automatic
- Excel output format improved but backward compatible

### 📈 Performance
- Faster Persian URL processing
- Improved AI response times for Persian prompts
- Better memory usage for large Persian datasets
- Enhanced caching for Persian content analysis

### 🎯 Use Cases Enhanced
- **Persian E-commerce**: Better product content optimization
- **Persian Blogs**: Improved article suggestions and structure
- **Persian News Sites**: Enhanced content clustering and suggestions
- **Persian Educational Sites**: Better learning content optimization

### 🔒 Privacy & Security
- No changes to data handling
- All Persian content processed locally
- Enhanced logging for Persian content debugging
- Better error reporting for Persian-specific issues

---

## [2.1.0] - 2025-10-11

### 🎉 Persian Language & Knowledge Base Release

Major update focusing on Persian/Farsi content optimization and intelligent project memory.

---

### ✨ New Features

#### Persian Language Optimization 🇮🇷
- **Persian-Aware AI Prompts**
  - Complete rewrite of AI prompts in Persian
  - Deep understanding of Farsi content nuances
  - Recognition of different Persian spellings and variations
  - Analysis of Iranian user search behavior and intent
  
- **Comprehensive Persian SEO Analysis**
  - LSI keywords specific to Persian language
  - H2/H3 headings optimized for Farsi search patterns
  - Meta descriptions with character limits (60 for title, 160 for description)
  - FAQ suggestions based on Persian "People Also Ask"
  - Internal linking with proper Persian anchor texts
  - Schema markup recommendations for Persian content
  
- **Enhanced Content Suggestions**
  - Content type classification (راهنما/آموزش/مقایسه/لیست/تحلیل)
  - Search intent analysis (informational/commercial/transactional)
  - Recommended word count based on Persian content standards
  - Technical SEO suggestions for Farsi pages
  - User experience improvements for Iranian audience

#### Knowledge Base System 🧠
- **Project Memory** (`src/knowledge_base.py` - 450+ lines)
  - Track content generation history per project
  - Store metadata, clusters, and performance metrics
  - Separate directory for each project in `knowledge_base/`
  - JSON-based storage for easy access and portability
  
- **Duplicate Detection**
  - Automatic detection of similar content titles
  - Hash-based exact duplicate matching
  - Similarity scoring (configurable threshold)
  - Prevention of repetitive content suggestions
  
- **Performance Tracking**
  - Store predicted impressions vs actual results
  - Track improvement suggestions and their outcomes
  - Build training data for CTR prediction models
  - Historical analysis for better future predictions
  
- **Smart Analytics**
  - Content generation statistics
  - Keyword usage tracking
  - Performance metrics export
  - Comprehensive JSON reports

#### Interactive Project Management
- **Project Name Input**
  - Interactive prompt for project identification
  - Name validation and confirmation
  - Used as key for knowledge base organization
  
- **Knowledge Base Integration in Workflow**
  - Automatic loading of project history
  - Real-time duplicate checking during generation
  - Seamless saving of all generated content
  - Progress messages for knowledge base operations

---

### 🔧 Improvements

#### AI Processor
- Completely rewritten prompts for Persian content (`src/ai_processor.py`)
- System prompts now in Farsi with cultural context
- Enhanced JSON structure with more fields:
  - `meta_description`
  - `content_type`
  - `search_intent`
  - `recommended_word_count`
  - `lsi_keywords`
  - `internal_linking`
  - `user_experience`
  - `estimated_impact`

#### Main Application
- Added `get_project_name_interactive()` function
- Knowledge base initialization in SEOContentOptimizer class
- Import of KnowledgeBase module
- Updated banner to show v2.1
- Enhanced workflow messages

#### Documentation
- Brand names replaced with generic examples throughout
- README.md updated with v2.1 features (Persian AI + Knowledge Base)
- QUICKSTART.md enhanced with new workflow steps
- CHANGELOG.md (this file) with detailed v2.1 notes
- All examples now use "example" instead of specific brand names

#### Project Structure
- New `knowledge_base/` directory with .gitkeep
- `knowledge_base/README.md` explaining directory purpose
- Updated `.gitignore` to exclude knowledge base data (except structure)
- Better organization of project artifacts

---

### 📁 New Files

#### Core Modules
- `src/knowledge_base.py` (450+ lines)
  - KnowledgeBase class with full functionality
  - Project-specific data management
  - Duplicate detection algorithms
  - Performance tracking methods
  - Export and reporting functions

#### Documentation
- `knowledge_base/README.md`
  - Explains knowledge base directory structure
  - Usage guidelines
  - Data storage format

#### Configuration
- `.gitkeep` files in new directories
- Updated `.gitignore` patterns

---

### 🌍 Localization

#### Persian Content Focus
- All AI prompts now in Persian
- Understanding of Farsi-specific SEO challenges
- Recognition of Iranian search patterns
- Local content recommendations
- Cultural context in suggestions

#### Bilingual Documentation
- README maintains English + Persian sections
- Both sections updated with v2.1 features
- Examples in both languages
- Clear indicators for Persian-optimized features

---

### 🔄 Migration Notes (v2.0 → v2.1)

#### No Breaking Changes
- All v2.0 features remain intact
- New features are additive
- Existing workflows continue to work
- Knowledge base is optional (auto-created)

#### New Workflow Steps
1. Run application as before
2. **NEW**: Enter project name when prompted
3. Continue with file selection (as before)
4. AI now uses Persian-optimized prompts
5. **NEW**: Knowledge base auto-saves everything
6. Review enhanced output with Persian insights

#### First Run
```bash
python3 main.py --mode content

# You'll see:
📋 PROJECT IDENTIFICATION
Enter a name for this project: example.com
✅ Project name: example.com

# Knowledge base auto-created at:
# knowledge_base/example.com/
```

---

### 📊 Statistics

- **New Lines of Code**: ~500 (knowledge_base.py)
- **Updated Modules**: 3 (ai_processor.py, main.py, .gitignore)
- **Documentation Updates**: 4 files (README, QUICKSTART, CHANGELOG, PROJECT_STRUCTURE)
- **New Directories**: 1 (knowledge_base/)
- **Test Coverage**: Manual testing completed

---

### 🎯 Use Cases Enhanced

#### For Persian Content Creators
- Create SEO-optimized Farsi content
- Get culturally relevant suggestions
- Understand Iranian user intent
- Track all content in one place

#### For SEO Professionals
- Manage multiple projects efficiently
- Avoid duplicate content automatically
- Track performance predictions
- Build knowledge over time

#### For Agencies
- Separate knowledge base per client
- Consistent quality across projects
- Historical data for reporting
- Scalable content strategy

---

### 🔐 Privacy & Data

#### Knowledge Base Storage
- All data stored locally
- JSON format for transparency
- Easy to backup and migrate
- No external data transmission

#### Git Safety
- `knowledge_base/` directory in .gitignore
- Only structure files (.gitkeep, README) tracked
- Sensitive project data never committed

---

## [2.0.0] - 2025-10-11

### 🎉 Major Release - Complete Redesign

This version represents a complete overhaul with focus on user experience, interactivity, and new capabilities.

---

### ✨ New Features

#### Dual Operational Modes
- **Content Optimization Mode**: Existing functionality enhanced with better UX
- **SEO Data Collection Mode**: NEW - Scrape page titles, meta tags, and SEO elements from sitemaps

#### Interactive User Interface
- **File Selection**: Visual, interactive selection from `input/` folder
  - Multi-select support (comma-separated numbers)
  - File metadata display (size, date)
  - "Select all" and "finish" commands
  
- **Mode Selection**: Interactive prompt if mode not specified via CLI
  - Clear descriptions of each mode
  - User-friendly selection interface
  
- **Sitemap Management**: Complete redesign
  - Interactive URL input with validation
  - Automatic caching (no re-downloads)
  - 10-retry logic with exponential backoff
  - User prompts for manual retry after failures
  - Sitemap index detection with selective sub-sitemap downloads

#### Test Mode
- Limit processing to 10 items (queries or pages)
- Available in both operational modes
- Perfect for validation before full runs
- Activated via `--test` flag

#### Resume Capability
- SEO scraping can be paused and resumed
- Existing scraped pages are skipped automatically
- No lost work if interrupted (Ctrl+C, crash, etc.)
- Progress saved after each batch

#### Enhanced Progress Tracking
- Real-time progress bars using `tqdm`
- Detailed status messages with emoji indicators
- Section headers for each processing stage
- Statistics summaries at completion
- Clear error messages with suggested fixes

#### Organized Folder Structure
- `input/` - Place Excel files here
- `sitemaps/` - Cached sitemap downloads
- `output/` - Generated Excel reports
- Automatic directory creation
- Prevents file conflicts

#### Page Scraping (New Module)
- Extract title, meta description, H1, canonical URL
- Open Graph tags (og:title, og:description)
- Twitter Card tags (twitter:title, twitter:description)
- Batch processing with configurable sizes
- User-controlled pause/continue
- Error handling with status tracking
- Separate output files per sitemap/domain

---

### 🔧 Improvements

#### Data Loader
- Better column name detection
  - Supports "Top queries" → "Query" mapping
  - Case-insensitive matching
  - Multiple alternative names for each column
- Improved error messages with available columns listed
- More robust Excel parsing

#### Sitemap Manager (New Module)
- Smart caching with MD5 hash filenames
- Domain-based readable filenames
- Retry logic with exponential backoff
- Sitemap index support
- Progress tracking for multiple sitemaps
- User control at every step

#### File Selector (New Module)
- Automatic detection of `.xlsx` and `.xls` files
- Metadata display (size, modification date)
- Sorted by modification time (newest first)
- Multi-select with validation
- Clear user prompts and error handling

#### AI Processor
- Fixed "json" keyword requirement for OpenAI-compatible APIs
- Better error messages
- More robust JSON parsing with fallbacks

#### Terminal Output
- Colored output with ANSI codes (via test_connection.py pattern)
- Consistent emoji usage for status indicators
- Section dividers for clarity
- Step indicators (e.g., [1/7])
- Real-time progress updates

#### Logging
- More descriptive log messages
- Better error context
- Success confirmations
- File paths in logs for traceability

---

### 🏗️ Architecture Changes

#### New Modules
- `src/sitemap_manager.py` - Interactive sitemap downloading and caching
- `src/file_selector.py` - Interactive Excel file selection
- `src/page_scraper.py` - Web page scraping for SEO data

#### Refactored main.py
- Complete rewrite with modular design
- Two clear operational modes
- Enhanced error handling
- Better separation of concerns
- Comprehensive docstrings and comments

#### Configuration Changes
- Removed `sitemap_url` from required config (now interactive)
- `input_excel_path` optional (interactive file selection)
- Added test mode settings
- Better documentation in sample config

---

### 📚 Documentation

#### New Files
- `FEATURES.md` - Comprehensive feature documentation
- `CHANGELOG.md` - This file
- `README_NEW.md` → `README.md` - Completely rewritten

#### Updated Files
- `QUICKSTART.md` - Fully updated for v2.0
- `EXAMPLES.md` - Updated with new workflows
- `config.sample.yaml` - Better comments and examples

#### README Highlights
- Dual-mode documentation
- Step-by-step workflows
- Troubleshooting section expanded
- Use case examples
- Configuration examples for all providers

---

### 🐛 Bug Fixes

- Fixed column name matching for Google Search Console exports
- Fixed API JSON mode requirements for Liara.ir and compatible APIs
- Improved error handling for missing files
- Better validation for user inputs
- Fixed sitemap download timeout handling

---

### 🔄 Breaking Changes

#### Command Line Interface
**Old (v1.x)**:
```bash
python main.py -i search_console_data.xlsx
```

**New (v2.0)**:
```bash
# Interactive (recommended)
python3 main.py

# Or specify mode
python3 main.py --mode content
python3 main.py --mode scraping

# Test mode
python3 main.py --mode content --test
```

#### File Organization
- Excel files must now be in `input/` folder
- Sitemaps cached in `sitemaps/` folder
- Output remains in `output/` folder

#### Configuration
- `sitemap_url` no longer required (interactive input)
- `input_excel_path` no longer required (interactive selection)

---

### 📦 Dependencies

#### Added
- `beautifulsoup4>=4.12.0` - For HTML parsing in page scraper

#### Updated
- All existing dependencies to latest compatible versions

---

### ⚡ Performance

- Sitemap caching reduces redundant downloads
- Resume capability prevents duplicate work
- Batch processing for memory efficiency
- Rate limiting respects API quotas

---

### 🔐 Security

- API keys never logged in plain text
- Config file in `.gitignore`
- Local processing, minimal external calls
- Backup creation before processing

---

### 🎯 Migration Guide (v1.x → v2.0)

#### Step 1: Update Files
```bash
git pull  # or download new version
pip3 install -r requirements.txt
```

#### Step 2: Move Excel Files
```bash
mkdir -p input
mv your_search_console_data.xlsx input/
```

#### Step 3: Update config.yaml
- Remove or comment out `sitemap_url` (now interactive)
- Remove or comment out `input_excel_path` (now interactive)

#### Step 4: Run New Interface
```bash
python3 main.py
```

Follow interactive prompts!

---

### 📊 Statistics

- **Lines of Code**: ~2,500+ (from ~800)
- **New Modules**: 3 (sitemap_manager, file_selector, page_scraper)
- **Documentation Pages**: 5 (README, QUICKSTART, FEATURES, CHANGELOG, EXAMPLES)
- **Test Coverage**: Manual testing completed for all features

---

### 🙏 Acknowledgments

- Built for SEO professionals and content marketers
- Inspired by feedback from v1.x users
- Designed for ease of use and reliability

---

### 📅 Future Roadmap

#### Planned for v2.1
- [ ] Async page scraping for faster performance
- [ ] Export to CSV in addition to Excel
- [ ] Scheduled runs (cron integration)
- [ ] Email notifications on completion

#### Under Consideration
- [ ] Web UI (Flask/Streamlit)
- [ ] Integration with Google Search Console API (direct)
- [ ] Multi-language support in AI prompts
- [ ] Custom AI prompt templates
- [ ] Historical tracking and comparison

---

### 🐛 Known Issues

None currently. Please report issues via GitHub or email.

---

### 📞 Support

- **Documentation**: See README.md, QUICKSTART.md, FEATURES.md
- **Logs**: Check `logs/seo_toolkit.log` for debugging
- **Test**: Use `--test` flag for validation
- **Connection**: Run `test_connection.py` to verify AI setup

---

## [1.0.0] - 2025-10-11 (Earlier Version)

### Initial Release
- Basic Search Console data analysis
- AI-powered content suggestions
- Keyword clustering
- Excel output generation
- Support for multiple AI providers

---

**For detailed feature documentation, see [FEATURES.md](FEATURES.md)**


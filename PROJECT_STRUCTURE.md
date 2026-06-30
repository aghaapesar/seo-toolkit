# Project Structure - Seo Toolkit v2.5.0

Complete directory structure and file organization guide.

Repository: https://github.com/aghaapesar/seo-toolkit

---

## Directory Tree

```
seo-toolkit/
├── main.py                         # CLI entry point (thin dispatcher)
├── test_connection.py              # AI connection test script
├── config.yaml                     # Your configuration (gitignored)
├── config.sample.yaml              # Sample configuration template
├── requirements.txt                # Python dependencies
├── requirements-dev.txt            # pytest and dev tools
├── VERSION                         # Current release version
│
├── docs/                           # Structured documentation
│   ├── ARCHITECTURE.md             # System design and data flows
│   ├── INSTALLATION.md             # Setup and troubleshooting
│   ├── API_MODULES.md              # Module reference
│   └── INDEX_DIFF.md               # URL index diff guide (EN/FA)
│
├── Documentation (root)
│   ├── README.md                   # Main guide (EN/FA)
│   ├── QUICKSTART.md               # 5-minute quick start
│   ├── FEATURES.md                 # Feature documentation
│   ├── EXAMPLES.md                 # Usage examples
│   ├── CHANGELOG.md                # Version history
│   └── PROJECT_STRUCTURE.md        # This file
│
├── src/
│   ├── app/toolkit.py              # SeoToolkit application core
│   ├── cli/                        # Banner, prompts, logging
│   ├── services/                   # url_index_tracker, shared services
│   ├── modes/                      # Mode dispatch helpers
│   └── *.py                        # Domain modules (AI, sitemap, export, ...)
│
├── web/                            # FastAPI dashboard and API
│   ├── app/main.py
│   ├── app/routers/
│   ├── app/templates/
│   └── requirements-web.txt
│
├── tests/                          # pytest unit tests
│
├── input/                          # Search Console Excel files
├── sitemaps/                       # Cached sitemap XML
├── output/                         # Reports, documents, index diff exports
│   └── index_diff/                 # new_urls / already_submitted txt
├── index_history/                  # Per-domain submitted URL tracking
├── knowledge_base/                 # Per-project content memory
└── logs/seo_toolkit.log            # Application log
```

---

## 📄 Core Files

### Main Application
- **`main.py`** (455 lines)
  - Application entry point
  - Two operational modes (content optimization, SEO scraping)
  - Interactive user interface
  - Progress tracking and error handling
  - CLI argument parsing

### Testing & Configuration
- **`test_connection.py`** (265 lines)
  - AI API connection testing
  - Configuration validation
  - Sample keyword clustering test
  - Color-coded terminal output

- **`config.yaml`** (User's private config)
  - AI provider credentials
  - Application settings
  - **⚠️ Never commit to git!**

- **`config.sample.yaml`** (Template)
  - Sample configuration with comments
  - All available options documented
  - Safe to commit to git

---

## 📚 Documentation Files

### User Guides
- **`README.md`** (568 lines)
  - Comprehensive bilingual guide (English/Persian)
  - Feature overview
  - Installation instructions
  - Usage examples
  - Troubleshooting

- **`QUICKSTART.md`** (471 lines)
  - 5-minute setup guide
  - Step-by-step instructions
  - Common commands
  - Quick troubleshooting

- **`FEATURES.md`** (296 lines)
  - Detailed feature documentation
  - Configuration options
  - Best practices
  - Use cases

### Developer Resources
- **`EXAMPLES.md`** (Original workflows)
  - Real-world usage examples
  - Different scenarios
  - Monthly workflow suggestions

- **`CHANGELOG.md`** (322 lines)
  - Version history
  - Feature additions
  - Bug fixes
  - Migration guides

- **`PROJECT_STRUCTURE.md`** (This file)
  - Directory organization
  - File descriptions
  - Size and line counts

---

## 🔧 Source Modules (`src/`)

### Core Modules (Original)
1. **`data_loader.py`** (230 lines)
   - Load Excel files from Google Search Console
   - Parse XML sitemaps
   - Column name normalization
   - Backup creation

2. **`analyzer.py`** (150 lines)
   - Identify content opportunities
   - Calculate opportunity scores
   - Match queries to URLs
   - Filter high-potential queries

3. **`ai_processor.py`** (325 lines)
   - Multi-provider AI support (OpenAI, Azure, Anthropic, compatible)
   - Keyword clustering
   - Content improvement suggestions
   - Retry logic and rate limiting
   - JSON response parsing

4. **`clustering.py`** (180 lines)
   - Keyword clustering algorithms
   - TF-IDF + DBSCAN (ML fallback)
   - Merge AI results with metrics
   - Cluster validation

5. **`excel_writer.py`** (220 lines)
   - Generate formatted Excel outputs
   - Multiple report types
   - Cell formatting and styling
   - Auto-column width adjustment

### New Modules (v2.0)
6. **`sitemap_manager.py`** (386 lines) ✨
   - Interactive sitemap URL input
   - Automatic caching
   - 10-retry download logic
   - Sitemap index support
   - Selective sub-sitemap downloads

7. **`file_selector.py`** (197 lines) ✨
   - Interactive file selection from `input/`
   - File metadata display
   - Multi-select support
   - Processed file management

8. **`page_scraper.py`** (380 lines) ✨
   - Web page content scraping
   - Extract title, meta tags, headings
   - Batch processing
   - Resume capability
   - Statistics tracking

---

## 📂 Working Directories

### `input/`
**Purpose**: Store Excel files exported from Google Search Console

**Contents**:
- `.gitkeep` - Preserves directory in git
- `*.xlsx` - Your Search Console data files

**Usage**:
```bash
# Copy your files here
cp ~/Downloads/Queries*.xlsx input/

# View files
ls input/
```

**Gitignore**: ✅ All Excel files ignored (except .gitkeep)

---

### `sitemaps/`
**Purpose**: Cache downloaded sitemaps to avoid re-downloading

**Contents**:
- `.gitkeep` - Preserves directory
- `{domain}_{hash}.xml` - Cached sitemap files

**Filename Format**: `example.com_a3f2d1b9c8e7.xml`

**Auto-managed**: Created and updated by `sitemap_manager.py`

**Gitignore**: ✅ All XML files ignored

---

### `output/`
**Purpose**: Store generated Excel reports

**Contents**:
- `.gitkeep` - Preserves directory
- `improvements_*.xlsx` - Content optimization suggestions
- `new_content_*.xlsx` - New article ideas with outlines
- `seo_data_*.xlsx` - Scraped SEO data from sitemaps

**Example Files**:
```
improvements_example-blog.xlsx
new_content_example-blog.xlsx
seo_data_example.com.xlsx
```

**Gitignore**: ✅ All Excel files ignored

---

### `logs/`
**Purpose**: Store application execution logs

**Contents**:
- `.gitkeep` - Preserves directory
- `seo_toolkit.log` - Main application log

**Log Format**:
```
2025-10-11 14:32:15,123 - __main__ - INFO - Starting analysis
2025-10-11 14:32:20,456 - src.data_loader - INFO - Loaded 1000 queries
```

**Rotation**: Manual (can implement log rotation if needed)

**Gitignore**: ✅ All log files ignored

---

## 🔐 Gitignore Strategy

### Ignored Items
✅ `config.yaml` - Contains sensitive API keys  
✅ `input/` - User's private Excel data  
✅ `sitemaps/` - Cached sitemap files  
✅ `output/` - Generated reports  
✅ `logs/` - Log files  
✅ `venv/` - Virtual environment  
✅ `__pycache__/` - Python cache  
✅ `*.pyc` - Compiled Python  
✅ `.DS_Store` - macOS files  
✅ `*_backup.*` - Backup files

### Preserved Items (via .gitkeep)
📌 `input/.gitkeep`  
📌 `sitemaps/.gitkeep`  
📌 `output/.gitkeep`  
📌 `logs/.gitkeep`

### Committed Items
📝 All source code (`src/*.py`)  
📝 Main scripts (`main.py`, `test_connection.py`)  
📝 Documentation (`*.md`)  
📝 Configuration template (`config.sample.yaml`)  
📝 Dependencies (`requirements.txt`)

---

## 📊 Statistics

### Code Metrics
- **Total Lines of Code**: ~2,500+
- **Number of Modules**: 8 core + 3 new = 11 total
- **Documentation Pages**: 6 markdown files
- **Total Project Files**: ~25 (excluding generated/cached)

### Module Sizes
```
main.py                 455 lines
src/page_scraper.py     380 lines
src/sitemap_manager.py  386 lines
src/ai_processor.py     325 lines
src/data_loader.py      230 lines
src/excel_writer.py     220 lines
src/file_selector.py    197 lines
src/clustering.py       180 lines
src/analyzer.py         150 lines
```

### Documentation Sizes
```
README.md               568 lines
QUICKSTART.md           471 lines
CHANGELOG.md            322 lines
FEATURES.md             296 lines
EXAMPLES.md             [original]
```

---

## 🚀 Quick Navigation

### For Users
- New to the tool? → Start with **QUICKSTART.md**
- Need details? → Read **README.md**
- Want examples? → Check **EXAMPLES.md**
- Feature questions? → See **FEATURES.md**

### For Developers
- Project overview → This file
- Code organization → `src/` modules
- Version history → **CHANGELOG.md**
- Testing → `test_connection.py`

### For Contributors
- Architecture → Module descriptions above
- Gitignore → See strategy section
- Logging → `logs/` directory
- Configuration → `config.sample.yaml`

---

## 📝 File Naming Conventions

### Excel Input Files
- Format: `{source}_{date}.xlsx`
- Example: `example-blog_2025-10.xlsx`
- Location: `input/`

### Excel Output Files
- Improvements: `improvements_{source}.xlsx`
- New Content: `new_content_{source}.xlsx`
- SEO Data: `seo_data_{domain}.xlsx`
- Location: `output/`

### Sitemap Cache Files
- Format: `{domain}_{hash}.xml`
- Example: `example.com_a3f2d1b9c8e7.xml`
- Location: `sitemaps/`

### Log Files
- Main log: `seo_toolkit.log`
- Location: `logs/`

---

## 🔄 Workflow Diagram

```
User
  │
  ├─→ Place Excel files in input/
  │
  ├─→ Run: python3 main.py
  │     │
  │     ├─→ Select Mode
  │     │     ├─→ Content Optimization
  │     │     │     ├─→ Select Excel files
  │     │     │     ├─→ Enter sitemap URL
  │     │     │     ├─→ Download/Cache sitemap
  │     │     │     ├─→ Analyze with AI
  │     │     │     └─→ Generate output/*.xlsx
  │     │     │
  │     │     └─→ SEO Data Collection
  │     │           ├─→ Enter sitemap URL
  │     │           ├─→ Download/Cache sitemap
  │     │           ├─→ Scrape pages in batches
  │     │           └─→ Generate seo_data_*.xlsx
  │     │
  │     └─→ Logs saved to logs/
  │
  └─→ Review results in output/
```

---

## 🛠️ Maintenance

### Regular Tasks
- Review `logs/seo_toolkit.log` for errors
- Clean old files from `output/` periodically
- Update dependencies: `pip install -r requirements.txt --upgrade`
- Clear sitemap cache if URLs change: `rm sitemaps/*`

### Git Management
```bash
# Safe to commit
git add src/ *.py *.md requirements.txt config.sample.yaml

# Never commit
# config.yaml, input/, output/, logs/, sitemaps/ are gitignored
```

---

**Last Updated**: 2025-10-11  
**Version**: 2.0.0


# Feature Documentation - Seo Toolkit v2.5.0

Comprehensive guide to all features including URL Index Diff, AI Content Generation, and Multi-Model Support.

Repository: https://github.com/aghaapesar/seo-toolkit

See also: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | [docs/INDEX_DIFF.md](docs/INDEX_DIFF.md)

---

## 📋 Table of Contents

1. [Operational Modes](#operational-modes)
2. [AI Content Generation (NEW v2.3)](#ai-content-generation-new-v23)
3. [Multi-Model AI Support (NEW v2.3)](#multi-model-ai-support-new-v23)
4. [Smart Internal Linking (NEW v2.3)](#smart-internal-linking-new-v23)
5. [Interactive Features](#interactive-features)
6. [Sitemap Management](#sitemap-management)
7. [File Management](#file-management)
8. [Test Mode](#test-mode)
9. [AI Integration](#ai-integration)
10. [Resume Capability](#resume-capability)
11. [Progress Tracking](#progress-tracking)

---

## Operational Modes

### Mode 6: URL Index Diff (NEW v2.5)

**Purpose**: Compare a live sitemap against URLs already submitted to an indexing tool.

**Input**: Domain name + sitemap URL (optional import txt)  
**Output**: `new_urls_*.txt` and `already_submitted_*.txt` under `output/index_diff/`

```bash
python main.py --mode index-diff --domain example.com
python main.py --mode index-diff --domain example.com --import old_urls.txt
python main.py --mode index-diff --domain example.com --mark-submitted
```

**Storage**: `index_history/{domain}/history.json`

See [docs/INDEX_DIFF.md](docs/INDEX_DIFF.md) for full guide.

### Mode 1: Content Optimization

**Purpose**: Analyze Search Console data to improve existing content and discover new opportunities.

**Input**: Excel files from Google Search Console  
**Output**: Two Excel files per input file
- `improvements_[filename].xlsx` - Suggestions for existing pages
- `new_content_[filename].xlsx` - New article ideas with outlines

**Process**:
1. Load Search Console queries
2. Identify high-potential opportunities (position > 10, high impressions)
3. Match queries to existing URLs from sitemap
4. Generate AI-powered improvement suggestions for matched pages
5. Cluster unmatched queries into new content topics
6. Create structured article outlines with H2/H3 headings

**Command**:
```bash
python3 main.py --mode content
```

**Use Cases**:
- Monthly content audits
- Finding quick wins (positions 11-20)
- Discovering content gaps
- Generating data-driven content strategies

---

### Mode 3: AI Content Generation ✨ NEW v2.3

**Purpose**: Generate complete SEO-optimized articles from content optimization suggestions.

**Input**: Excel files from Mode 1 (Content Optimization)  
**Output**: Complete articles in Word and HTML format with internal linking

**Process**:
1. Read Excel files from `output/` directory (from Mode 1 results)
2. Extract main topic from first column
3. Identify H2 heading columns (containing "هدینگ H2")
4. Interactive word count distribution (total → per heading)
5. Generate content for each heading using AI
6. Create introduction and conclusion based on generated content
7. Apply smart internal linking (max 1 link per 300-400 words)
8. Export to Word (.docx) and HTML formats
9. Update Excel with generated title and meta description

**Command**:
```bash
python3 main.py --mode generation
```

**Features**:
- Multi-AI model selection (Claude, GPT-4, Gemini, Grok, etc.)
- Persian SEO-optimized content generation
- Smart internal linking with semantic analysis
- Word and HTML export with proper formatting
- E-E-A-T principles integration
- Interactive word count management

**Use Cases**:
- Converting content ideas into full articles
- Scaling content production
- Maintaining SEO best practices
- Creating editor-ready content

---

## 🤖 AI Content Generation (NEW v2.3)

### Complete Article Generation

**Purpose**: Transform content optimization suggestions into full, SEO-optimized articles.

**Input Flow**:
```
Excel (Mode 1) → Topic + Headings → Word Counts → AI Generation → Complete Article
```

**Content Structure**:
1. **Introduction** (AI-generated based on headings)
2. **Body Sections** (one per H2 heading)
3. **Conclusion** (AI-generated based on content)
4. **SEO Elements** (title, meta description)

### Interactive Word Count Management

**Feature**: Smart distribution of total word count across article sections.

**How it Works**:
```
📝 Article 1 of 5
======================================================================

📌 Topic: راهنمای کاشت و نگهداری گلهای زیبا

📋 Headings (5):
   1. معرفی گل لیلیوم
   2. نحوه کاشت گل همیشه بهار
   3. نگهداری از گل سایه دوست
   4. روشهای آبیاری بگونیا
   5. (empty - will be skipped)

📊 Enter total word count for this article (recommended: 2500-4000): 3000

📝 Word count distribution:
   Total words: 3000
   Available for headings: 2600 (3000 - 200 intro - 200 conclusion)

📝 Enter word count for each heading:

   [1] معرفی گل لیلیوم: 650 words
   [2] نحوه کاشت گل همیشه بهار: 650 words  
   [3] نگهداری از گل سایه دوست: 650 words
   [4] روشهای آبیاری بگونیا: 650 words
   
   ✅ Total: 2600 words (matches available)
```

**Features**:
- Automatic calculation of available words
- Validation that total matches target
- Skip empty headings
- Smart recommendations

### Persian SEO Content Generation

**Specialized Prompts**: Customized for Persian language SEO best practices.

**Content Quality Features**:
- E-E-A-T (Expertise, Experience, Authoritativeness, Trustworthiness)
- Natural keyword integration
- Readable formatting with proper spacing
- Structured content with clear sections
- Actionable information

### Document Export System

**Word Export (.docx)**:
- Proper heading hierarchy (H1, H2, H3)
- Bold text for emphasis
- SEO metadata (title, description)
- Professional formatting

**HTML Export**:
- Editor-ready HTML (no `<html>`, `<head>`, `<body>` tags)
- Clean markup for CMS integration
- Preserved formatting and structure
- Internal links properly formatted

---

## 🔄 Multi-Model AI Support (NEW v2.3)

### Supported AI Providers

**Complete Provider List**:
1. **OpenAI** (GPT-4, GPT-4o, GPT-4o-mini)
2. **Anthropic** (Claude 3 Opus, Sonnet, Haiku)
3. **Google** (Gemini Pro, Gemini Pro Vision)
4. **Grok** (Llama 3, Mixtral)
5. **OpenAI-Compatible** (Liara.ir, LM Studio, Ollama, etc.)

### Model Selection Interface

**Connection Testing**:
```
🔍 Testing AI model connections...

✅ Connected Models:
  [1] liara_gpt4o_mini (OpenAI Compatible - Liara)
  [2] claude_sonnet (Anthropic - Claude 3.5 Sonnet)
  [3] gemini_pro (Google - Gemini Pro)

❌ Failed Models:
  - openai_gpt4 (Invalid API key)
  - grok_llama3 (Connection timeout)

🤖 Default model: liara_gpt4o_mini
```

**Per-Operation Selection**:
```
📝 Content Generation - Model Selection

Choose AI model for this operation:
  [1] Use default (liara_gpt4o_mini)
  [2] claude_sonnet - Best for creative content
  [3] gemini_pro - Good for technical content
  [4] Select different model for each section

Your choice: 4

📝 Introduction generation - Choose model:
  [1] liara_gpt4o_mini
  [2] claude_sonnet  
  [3] gemini_pro

Your choice: 2
```

### Configuration Management

**Flexible API Key Management**:
```yaml
# Direct keys
liara_gpt4o_mini:
  api_key: "sk-your-actual-key"

# Environment variables  
claude_sonnet:
  api_key: "env:ANTHROPIC_API_KEY"

# Multiple models per provider
openai_gpt4:
  provider: "openai"
  api_key: "env:OPENAI_API_KEY"
  model: "gpt-4"
  
openai_gpt4o:
  provider: "openai" 
  api_key: "env:OPENAI_API_KEY"
  model: "gpt-4o"
```

### Model-Specific Optimization

**Provider-Specific Features**:
- **OpenAI**: JSON mode, function calling
- **Anthropic**: Structured output, longer context
- **Gemini**: Multimodal capabilities, fast responses
- **Grok**: High-speed inference, cost-effective

---

## 🔗 Smart Internal Linking (NEW v2.3)

### Intelligent Link Placement

**Core Rules**:
1. **Frequency**: Maximum 1 link per 300-400 words
2. **Placement**: Never within headings (H1, H2, H3)
3. **Priority**: Categories > Products > Blog posts
4. **Distribution**: Mix content types across article
5. **Anchor Text**: Exact match preferred, closest phrase (max 5 syllables) as fallback

### Sitemap Analysis

**URL Categorization**:
```
📊 Analyzing sitemap for internal linking...

✅ Found 1,247 URLs:
   📁 Categories: 45 URLs
   🛍️ Products: 892 URLs  
   📝 Blog Posts: 310 URLs

🔗 Internal linking candidates: 1,247 URLs
```

**Smart URL Classification**:
- **Categories**: `/category/`, `/categories/`, `/shop/category/`
- **Products**: `/product/`, `/products/`, `/shop/product/`, `/item/`
- **Blog Posts**: `/blog/`, `/post/`, `/article/`, `/news/`

### Semantic Content Matching

**AI-Powered Relevance**:
```
📝 Generating content for: "معرفی گل لیلیوم"

🔍 Analyzing content for internal linking...

📊 Semantic analysis results:
   Best match: "گل لیلیوم سفید" (product)
   Relevance: 95%
   Anchor text: "گل لیلیوم سفید"
   
   Alternative: "گل‌های زینتی" (category)  
   Relevance: 87%
   Anchor text: "گل‌های زینتی"
```

**Matching Process**:
1. Extract key concepts from paragraph
2. Compare with URL titles/descriptions
3. Calculate semantic similarity
4. Select best match with proper anchor text
5. Ensure no duplicate links in same article

### Link Distribution Strategy

**Balanced Approach**:
```
📊 Link distribution for 3000-word article:
   📁 Category links: 2 (33%)
   🛍️ Product links: 2 (33%)  
   📝 Blog links: 2 (33%)
   
   📍 Placement:
   - Paragraph 2: [گل‌های زینتی](category)
   - Paragraph 4: [گل لیلیوم سفید](product)
   - Paragraph 6: [راهنمای کاشت گل](blog)
   - Paragraph 8: [بذر گل](category)
   - Paragraph 10: [کود مخصوص گل](product)
   - Paragraph 12: [نحوه آبیاری گل‌ها](blog)
```

**Quality Assurance**:
- No more than 2 links to same page
- Diverse anchor text
- Natural placement within content
- Contextually relevant links only

---

### Mode 2: SEO Data Collection

**Purpose**: Scrape and audit all pages in your sitemap for SEO data.

**Input**: Sitemap URL  
**Output**: One Excel file per sitemap
- `seo_data_[domain].xlsx` - Complete SEO audit data

**Collected Data**:
- Page URL
- `<title>` tag
- `<meta name="description">` tag
- First `<h1>` tag
- `<link rel="canonical">` URL
- Open Graph tags (`og:title`, `og:description`)
- Twitter Card tags (`twitter:title`, `twitter:description`)

**Process**:
1. Download sitemap(s)
2. Extract all URLs
3. Scrape each page for SEO elements
4. Save results with status tracking
5. Support resume for interrupted sessions

**Command**:
```bash
python3 main.py --mode scraping
```

**Use Cases**:
- Complete site SEO audits
- Finding missing/duplicate titles
- Identifying thin or missing meta descriptions
- Checking canonical tag consistency
- Social media tag verification

---

## 🖱️ Interactive Features

### File Selection

**Feature**: Interactive selection of Excel files from `input/` folder.

**How it Works**:
```
📊 FOUND 2 EXCEL FILE(S)
  [1] example-blog.xlsx (94.5 KB | 2025-10-11 14:32)
  [2] example-product.xlsx (102.1 KB | 2025-10-11 14:30)

Selection options:
  - Enter numbers separated by commas (e.g., 1,3)
  - Enter 'all' to select all files
  - Enter 'finish' or 'exit' to quit

Your selection: 1,2
```

**Features**:
- Display file size and modification date
- Multi-select support (comma-separated)
- Select all option
- Clear exit command

---

### Mode Selection

**Feature**: Interactive prompt to choose operational mode if not specified via CLI.

**How it Works**:
```
Please select operational mode:

  [1] Content Optimization
      Analyze Search Console data for content improvements
      Input: Excel files from Google Search Console
      Output: Improvement suggestions + New content ideas

  [2] SEO Data Collection
      Scrape page titles and meta tags from sitemap
      Input: Sitemap URL
      Output: Excel with SEO data for all pages

Your selection (1 or 2): 
```

**Trigger**: Launched automatically when running `python3 main.py` without `--mode` flag.

---

## 🗺️ Sitemap Management

### Interactive URL Input

**Feature**: Prompt user for sitemap URL with validation.

**How it Works**:
```
🗺️  SITEMAP CONFIGURATION
Enter your sitemap URL (e.g., https://example.com/sitemap.xml): 
```

**Validation**:
- ❌ Rejects empty input
- ❌ Requires http:// or https:// prefix
- ✅ Accepts valid URLs

---

### Automatic Caching

**Feature**: Downloaded sitemaps are cached locally to avoid re-downloads.

**Cache Location**: `sitemaps/` folder

**Filename Format**: `{domain}_{hash}.xml`

**How it Works**:
```
✅ Using cached sitemap: example.com_a3f2d1b9c8e7.xml
   Download again? (y/N): 
```

**Benefits**:
- Faster re-runs
- Reduces server load
- Saves bandwidth
- User can force re-download if needed

---

### Retry Logic (10 Attempts)

**Feature**: Automatic retry with exponential backoff for failed downloads.

**How it Works**:
```
📥 Downloading sitemap: https://example.com/sitemap.xml
   Attempt 1/10... ✅ Success!
```

If fails:
```
   Attempt 1/10... ❌ Failed: Connection timeout
   Waiting 2s before retry...
   Attempt 2/10... ❌ Failed: Connection timeout
   Waiting 4s before retry...
   ...
   Attempt 10/10... ❌ Failed: Connection timeout

❌ All 10 download attempts failed!

Do you want to try again? (y/N): 
```

**Backoff Strategy**: 2^attempt seconds, capped at 30s

**User Control**: After all attempts fail, user can manually retry or abort.

---

### Sitemap Index Support

**Feature**: Detect sitemap indices and let user select which sub-sitemaps to download.

**How it Works**:
```
🔗 This is a sitemap index containing 5 sub-sitemaps

📋 FOUND 5 SUB-SITEMAPS
  [1] posts - https://example.com/sitemap-posts.xml
  [2] pages - https://example.com/sitemap-pages.xml
  [3] products - https://example.com/sitemap-products.xml
  [4] categories - https://example.com/sitemap-categories.xml
  [5] tags - https://example.com/sitemap-tags.xml

Selection options:
  - Enter numbers separated by commas (e.g., 1,3,5)
  - Enter 'all' to download all sitemaps
  - Enter 'none' to skip

Your selection: 1,3
```

**Features**:
- Automatic detection of `<sitemapindex>` elements
- Extract readable names from URLs
- Selective download
- Combined URL extraction from selected sitemaps

---

## 📁 File Management

### Organized Folder Structure

```
SEOContentAnalysis/
├── input/                    # User places Excel files here
│   └── processed/           # Auto-moved after processing (optional)
├── sitemaps/                 # Cached sitemap downloads
│   ├── example.com_hash1.xml
│   └── blog.com_hash2.xml
├── output/                   # Generated Excel reports
│   ├── improvements_file1.xlsx
│   ├── new_content_file1.xlsx
│   └── seo_data_domain.xlsx
├── main.py
├── config.yaml
└── seo_toolkit.log        # Detailed logs
```

**Benefits**:
- Clean separation of inputs/outputs
- Easy to find results
- Prevents accidental overwriting
- Automatic cleanup options

---

### Backup Creation

**Feature**: Automatic backup of input Excel files before processing.

**How it Works**:
```
📋 Creating backup: example-blog_backup.xlsx
✅ Backup created
```

**Location**: Same folder as original file

**Purpose**: Safety net in case of processing errors or data corruption.

---

## 🧪 Test Mode

### Purpose

Quick validation with limited data before running full analysis.

### Limits

- **Content Optimization**: 10 queries
- **SEO Data Collection**: 10 pages

### Activation

```bash
# Via CLI flag
python3 main.py --mode content --test
python3 main.py --mode scraping --test

# Indicated in output
🧪 TEST MODE ENABLED: Will process only 10 items
```

### Use Cases

1. **First-Time Setup**: Verify everything works before processing thousands of items
2. **New Sitemap**: Test a new site's sitemap structure
3. **API Testing**: Ensure AI provider is responding correctly
4. **Quick Preview**: See output format before full run
5. **Debugging**: Isolate issues with smaller dataset

### Output

Same format as full mode, just limited data.

---

## 🤖 AI Integration

### Multi-Provider Support

**Supported Providers**:
1. OpenAI (GPT-4, GPT-4o-mini, etc.)
2. Azure OpenAI
3. Anthropic (Claude)
4. OpenAI-Compatible APIs (Liara.ir, LM Studio, Ollama, etc.)

### JSON Mode

**Feature**: Forces AI to return structured JSON for reliable parsing.

**Implementation**: Automatically includes "json" in prompts when using OpenAI-compatible APIs.

**Example Response**:
```json
{
  "primary_improvements": [
    "Add FAQ section with common questions",
    "Expand introduction with more context",
    "Include comparison table"
  ],
  "recommended_keywords": [
    "keyword 1",
    "keyword 2"
  ],
  "priority_level": "high"
}
```

### Rate Limiting

**Feature**: Configurable queries-per-second (QPS) to respect API limits.

**Config**:
```yaml
ai:
  qps: 1.0  # 1 request per second
```

**Implementation**: Automatic delay between requests based on QPS setting.

### Retry Logic

**Feature**: Automatic retry for failed API calls.

**Config**:
```yaml
ai:
  max_retries: 3
  retry_base_delay: 1.5  # seconds
```

**Strategy**: Exponential backoff (1.5s → 3s → 6s)

---

## 🔄 Resume Capability

### SEO Data Collection Mode

**Feature**: Continue scraping from where you left off if interrupted.

**How it Works**:

First run:
```
🔄 Scraping batch: 1 to 50 of 1,250
Scraping pages: 100%|███████████| 50/50
✅ Batch complete. Scraped: 50/1,250

⏸️  Scraped 50/1,250 pages. Continue? (Y/n): n

⏹️  Scraping paused. 1,200 URLs remaining.
   Run again to resume from where you left off.
```

Second run (same sitemap):
```
📊 Found existing data: 50 URLs already scraped
📋 URLs to scrape: 1,200 (Total: 1,250)

🔄 Scraping batch: 51 to 100 of 1,200
```

**Implementation**:
- Excel file stores all scraped URLs
- On restart, loads existing file
- Skips URLs already present
- Continues from next unscraped URL

**Benefits**:
- No lost work if interrupted (Ctrl+C, network failure, etc.)
- Can pause and resume anytime
- Flexible batch processing for large sites

---

## 📊 Progress Tracking

### Section Headers

**Feature**: Clear visual separators for each processing stage.

**Example**:
```
======================================================================
[1/7] Loading Search Console Data
======================================================================
```

### Real-Time Status Messages

**Feature**: Descriptive messages with emoji indicators.

**Status Types**:
- ✅ Success (green checkmark)
- ❌ Error (red X)
- ⚠️ Warning (yellow warning)
- 📥 Downloading
- 🔄 Processing
- 💾 Saving
- 🧪 Test Mode
- ⏸️ Paused
- 📊 Statistics

**Example**:
```
📥 Downloading sitemap...
   Attempt 1/10... ✅ Success!
✅ Extracted 1,250 URLs from sitemap

🔄 Processing existing URLs...
   📌 Matched to existing pages: 45
   ✨ New content opportunities: 32

💾 Saving results...
   ✅ Created: improvements_blog.xlsx
   ✅ Created: new_content_blog.xlsx
```

### Progress Bars

**Feature**: Visual progress indicators for long-running operations.

**Library**: `tqdm`

**Example**:
```
Scraping pages: 100%|████████████████████| 50/50 [00:42<00:00,  1.18it/s]
Processing sitemaps: 100%|█████████████████| 5/5 [00:15<00:00,  3.12s/it]
```

**Used For**:
- Page scraping
- AI processing of multiple URLs
- Sitemap downloads

### Statistics Summary

**Feature**: Final statistics after completion.

**Example (Content Optimization)**:
```
======================================================================
🎉 ALL FILES PROCESSED SUCCESSFULLY!
======================================================================
📁 Output directory: /path/to/output
📊 Processed 2 file(s)
✅ Generated 4 report(s)
```

**Example (SEO Data Collection)**:
```
======================================================================
📊 SCRAPING STATISTICS
======================================================================
  ✅ Successful: 48
  ❌ Errors: 2
  ⏱️  Timeouts: 0
  📄 Total: 50
----------------------------------------------------------------------
  💾 Output file: seo_data_example.com.xlsx
======================================================================
```

---

## 🔐 Security & Privacy

### Local Processing

- All scraping and file processing happens locally
- Only AI API calls go external
- Sitemaps cached locally
- No data sent to third parties (except configured AI provider)

### API Key Safety

- Keys stored in `config.yaml` (gitignored)
- Never logged in plain text
- Only last 10 chars shown in connection test

### Backup Protection

- Original files never modified
- Backups created before processing
- Resume functionality prevents data loss

---

## 🚀 Performance Optimization

### Caching

- Sitemaps cached to avoid re-downloads
- Existing scraped data reused on resume
- Reduces API calls and bandwidth

### Batch Processing

- Configurable batch sizes
- User-controlled pauses
- Memory-efficient for large sites

### Parallel Operations

- Could be extended with async processing (future enhancement)
- Currently sequential for reliability and rate limit compliance

---

## 📝 Logging

### Log File

**Location**: `seo_toolkit.log`

**Format**:
```
2025-10-11 14:32:15,123 - __main__ - INFO - Seo Toolkit initialized
2025-10-11 14:32:20,456 - src.data_loader - INFO - Loaded 1000 queries
2025-10-11 14:32:25,789 - src.sitemap_manager - INFO - Downloaded sitemap
```

###Levels

- **INFO**: Normal operations
- **WARNING**: Non-fatal issues (e.g., single page scrape failed)
- **ERROR**: Recoverable errors (e.g., API retry)
- **DEBUG**: Detailed diagnostic info (with `-v` flag)

### Viewing Logs

```bash
# View recent logs
tail -f seo_toolkit.log

# Search for errors
grep ERROR seo_toolkit.log

# View with verbose mode
python3 main.py --mode content -v
```

---

## 💡 Best Practices

### Content Optimization Mode

1. **Monthly cadence**: Run monthly to track improvements
2. **Focus on quick wins**: Target positions 11-20 first
3. **Implement top 10**: Don't overwhelm yourself, start with top opportunities
4. **Track results**: Re-export Search Console data after 30 days

### SEO Data Collection Mode

1. **Start with test mode**: Verify sitemap structure first
2. **Use manageable batches**: 50-100 pages for large sites
3. **Resume capability**: Pause anytime, no pressure to finish
4. **Fix and re-scrape**: After fixing issues, scrape again to verify

### General

1. **Test mode first**: Always test before full run
2. **Review AI suggestions**: AI provides ideas, you make final decisions
3. **Version control**: Keep old Excel outputs for comparison
4. **Regular audits**: Schedule quarterly comprehensive audits

---

**For more information, see [README.md](README.md) and [QUICKSTART.md](QUICKSTART.md)**


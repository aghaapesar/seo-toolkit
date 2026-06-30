# Usage Examples & Workflow - Seo Toolkit

Real-world examples and workflows for **Seo Toolkit** (Persian SEO automation).

Repository: https://github.com/aghaapesar/seo-toolkit

---

## Example 0: URL Index Diff (Mode 6)

### Scenario
You submit sitemap URLs to an indexing tool weekly and need only **new** URLs each time.

### Workflow

1. **Import previous batch (first time only)**
```bash
python main.py --mode index-diff --domain example.com --import previous_urls.txt
```

2. **Run diff against live sitemap**
```bash
python main.py --mode index-diff --domain example.com
```

3. **Submit output to indexing tool**
   - Use `output/index_diff/example_com/new_urls_*.txt`
   - Confirm marking URLs as submitted when prompted

4. **Web UI alternative**
```bash
uvicorn web.app.main:app --reload --port 8000
# Open http://127.0.0.1:8000/index-diff
```

---

## 📊 Example 1: Basic Analysis

### Scenario
You have a blog with 200 queries in Google Search Console, and you want to find content opportunities.

### Workflow

1. **Export Data from Google Search Console**
   - Filter: Last 3 months
   - Export all queries (not filtered by page)
   - Save as `blog_queries_q4_2024.xlsx`

2. **Configure the tool**
```yaml
app:
  sitemap_url: "https://yourblog.com/sitemap.xml"
  min_position: 10
  input_excel_path: "blog_queries_q4_2024.xlsx"
```

3. **Run analysis**
```bash
python main.py -i blog_queries_q4_2024.xlsx
```

4. **Review results**
   - Check `existing_content_improvements.xlsx` for pages ranking 11-20
   - Check `new_content_suggestions.xlsx` for new article ideas

### Expected Output
- 20-30 existing pages with improvement suggestions
- 10-15 new content ideas clustered by topic

---

## 📊 Example 2: E-commerce Site Optimization

### Scenario
E-commerce site with 1000+ product pages. Want to improve product descriptions and category pages.

### Workflow

1. **Filter Search Console Data**
   - Export queries for specific sections
   - Or export all and filter position > 15

2. **Configure for high-traffic focus**
```yaml
app:
  min_position: 15  # Focus on queries further from page 1
  clustering_threshold: 0.8  # Stricter clustering for product-focused content
```

3. **Run with verbose logging**
```bash
python main.py -i products_queries.xlsx -v
```

4. **Analyze results**
   - Improvement suggestions → Update product descriptions
   - Keyword clusters → Create new category pages

---

## 📊 Example 3: Multi-language Site

### Scenario
Website with English and Spanish versions. Analyze each separately.

### Workflow

1. **Filter by language in Search Console**
   - Export English queries → `queries_en.xlsx`
   - Export Spanish queries → `queries_es.xlsx`

2. **Create separate configs**

`config_en.yaml`:
```yaml
ai:
  provider: openai_compatible
  model: openai/gpt-4o-mini
  # ... API settings
app:
  sitemap_url: "https://example.com/en/sitemap.xml"
  input_excel_path: "queries_en.xlsx"
  output_directory: "output/en"
```

`config_es.yaml`:
```yaml
ai:
  provider: openai_compatible
  model: openai/gpt-4o-mini
  # ... API settings
app:
  sitemap_url: "https://example.com/es/sitemap.xml"
  input_excel_path: "queries_es.xlsx"
  output_directory: "output/es"
```

3. **Run separately**
```bash
python main.py -c config_en.yaml
python main.py -c config_es.yaml
```

---

## 📊 Example 4: Local Business SEO

### Scenario
Local service business (e.g., plumber, lawyer) wanting to rank for local queries.

### Workflow

1. **Export geo-specific data**
   - Filter by country/region in Search Console
   - Focus on "near me" and location-based queries

2. **Configure for local SEO**
```yaml
app:
  sitemap_url: "https://localbusiness.com/sitemap.xml"
  min_position: 5  # Even position 6-10 matters for local
  max_headings_per_article: 6  # Shorter, local-focused content
```

3. **AI prompts will focus on**
   - Local intent keywords
   - Service area coverage
   - Local landing pages

---

## 📊 Example 5: Content Gap Analysis

### Scenario
Competitor analysis - find topics they rank for but you don't.

### Workflow

1. **Gather competitor queries** (manual or tools)
   - Create `competitor_queries.xlsx` with same format
   - Columns: Query, Clicks (set to 0), Impressions (estimated), CTR, Position (estimated)

2. **Run analysis**
```bash
python main.py -i competitor_queries.xlsx
```

3. **Focus on new_content_suggestions.xlsx**
   - These are topics you're missing
   - AI provides structure to create competitive content

---

## 📊 Example 6: AI Content Generation Workflow ✨ NEW

### Scenario
You've identified 15 high-potential content opportunities from Search Console analysis, and now you want to generate full SEO-optimized articles with internal linking.

### Complete Workflow

#### Step 1: Analyze and Get Ideas
```bash
# First, run content optimization to get ideas
python3 main.py --mode content

# This creates: output/new_content_blog.xlsx
# Contains: Article titles, recommended keywords, H2/H3 suggestions
```

#### Step 2: Configure Multiple AI Models
Edit `config.yaml`:
```yaml
ai_models:
  default: "claude_sonnet"  # Use Claude as default
  
  claude_sonnet:
    provider: "anthropic"
    api_key: "env:ANTHROPIC_API_KEY"
    model: "claude-3-5-sonnet-20241022"
  
  openai_gpt4o:
    provider: "openai"
    api_key: "env:OPENAI_API_KEY"
    base_url: "https://api.openai.com/v1"
    model: "gpt-4o"
  
  gemini_pro:
    provider: "gemini"
    api_key: "env:GOOGLE_API_KEY"
    model: "gemini-pro"
```

Set environment variables:
```bash
export ANTHROPIC_API_KEY="sk-ant-your-key"
export OPENAI_API_KEY="sk-your-key"
export GOOGLE_API_KEY="your-google-key"
```

#### Step 3: Generate Content
```bash
python3 main.py --mode generation

# Interactive process:
# 1. System tests all 3 models → Shows connection status
# 2. Choose: "Use default for all" (Claude Sonnet)
# 3. Select: new_content_blog.xlsx
# 4. Enter project: "myblog.com"
# 5. Enter topic: "Gardening & Plants"
# 6. Confirm model: Claude Sonnet
# 7. Set word count: 800 words per article
# 8. Confirm: Generate 15 articles
```

#### Step 4: Add Internal Links
```bash
# During generation, when prompted:
Add internal links? (Y/n): y

# Enter sitemap
Enter sitemap URL: https://myblog.com/sitemap.xml

# System will:
# - Parse 500+ URLs from sitemap
# - Categorize: 30 categories, 250 products, 200 blog posts
# - Add semantic links to each article
# - 1 link per 300-400 words
# - Priority to category pages
```

#### Step 5: Review Outputs

**Excel Output** (`output/content_generated/content_blog.xlsx`):
| Article Title | H2_1 | H2_2 | SEO_Title | Meta_Description | Generated_Content |
|--------------|------|------|-----------|-----------------|-------------------|
| Complete Guide to Growing Tomatoes | Seed Selection | Soil Prep | Best Methods for Growing Tomatoes | Complete guide to planting... | `<h2>Introduction</h2>...` |

**Word Documents** (`output/documents/`):
```
content_myblog.com_1_complete-guide-growing-tomatoes.docx
content_myblog.com_2_organic-pest-control-methods.docx
...
```

Each Word doc contains:
- SEO Title (copyable)
- Meta Description (copyable)
- Full formatted content with headings, bold, lists, internal links

**HTML Files** (`output/documents/`):
```html
<!-- content_myblog.com_1_complete-guide-growing-tomatoes.html -->

<!-- SEO Title -->
<!-- Best Methods for Growing Tomatoes at Home -->

<!-- Meta Description -->
<!-- Complete guide to planting and growing tomatoes with expert tips -->

<!-- Content Start -->
<h2>Introduction</h2>
<p>Growing tomatoes in your home garden...</p>

<h2>Selecting the Right Seeds</h2>
<p>The first step is choosing <strong>quality seeds</strong>...</p>
<p>Visit our <a href="https://myblog.com/category/seeds/">seed selection guide</a> for more details.</p>

<h3>Types of Tomato Seeds</h3>
<ul>
  <li>Cherry tomatoes</li>
  <li><a href="https://myblog.com/products/heirloom-tomato-seeds/">Heirloom varieties</a></li>
  <li>Beefsteak tomatoes</li>
</ul>
...
<!-- Content End -->
```

#### Step 6: Publish Content

**Option A: Manual Publishing**
1. Open Word document
2. Copy SEO title → Paste in CMS title field
3. Copy meta description → Paste in SEO description field
4. Copy content from HTML file → Paste in CMS editor

**Option B: Automated Publishing** (via CMS API)
```python
# Example script to publish via WordPress API
import pandas as pd
import requests

df = pd.read_excel('output/content_generated/content_blog.xlsx')

for _, row in df.iterrows():
    data = {
        'title': row['SEO_Title'],
        'content': row['Generated_Content'],
        'excerpt': row['Meta_Description'],
        'status': 'draft'
    }
    
    response = requests.post(
        'https://myblog.com/wp-json/wp/v2/posts',
        json=data,
        auth=('username', 'app_password')
    )
```

### Expected Results

**Immediate:**
- 15 complete, SEO-optimized articles (12,000+ words total)
- Each with 5-8 internal links
- All in 3 formats (Excel, Word, HTML)
- Processing time: ~30 minutes

**After 30 Days:**
- 50-60% of articles indexed by Google
- 30-40% ranking on page 1-3 for target keywords
- Increased internal link equity to category/product pages

**After 90 Days:**
- 80%+ indexed
- 50%+ ranking on page 1
- Measurable increase in organic traffic

### Pro Tips for Content Generation

1. **Model Selection Strategy:**
   - Use Claude Sonnet for long-form, natural content
   - Use GPT-4 for technical/factual content
   - Use Gemini Pro for multilingual content

2. **Word Count Guidelines:**
   - Blog posts: 800-1200 words
   - Ultimate guides: 2000-3000 words
   - Product reviews: 1500-2000 words
   - FAQ pages: 500-800 words

3. **Internal Linking Best Practices:**
   - Always enable internal linking
   - Ensure sitemap is up-to-date
   - Review generated links before publishing
   - Adjust anchor text if needed

4. **Quality Control:**
   - Review first 2-3 generated articles completely
   - Check for factual accuracy
   - Verify internal links work
   - Adjust prompt if needed (edit `content_generator.py`)

5. **Batch Processing:**
   - Process 10-15 articles at a time
   - Don't exceed API rate limits
   - Save progress regularly

### Troubleshooting

**Issue: "No connected models"**
```bash
# Check API keys
echo $ANTHROPIC_API_KEY
echo $OPENAI_API_KEY

# Test connection manually
curl -H "Authorization: Bearer $ANTHROPIC_API_KEY" \
     https://api.anthropic.com/v1/messages
```

**Issue: "Failed to generate content"**
- Check API quota/credits
- Try different model
- Reduce word count
- Check internet connection

**Issue: "No internal links added"**
- Verify sitemap URL is accessible
- Check sitemap has valid URLs
- Ensure content has enough words (>300)

---

## 📊 Example 7: Multi-Model Comparison ✨ NEW

### Scenario
You want to test which AI model produces the best content for your niche.

### Workflow

#### Step 1: Generate Same Content with Different Models

**Run 1: Claude Sonnet**
```bash
python3 main.py --mode generation
# Select: Claude Sonnet
# Generate: 5 test articles
# Output: content_claude/
```

**Run 2: GPT-4**
```bash
python3 main.py --mode generation
# Select: GPT-4
# Generate: Same 5 articles
# Output: content_gpt4/
```

**Run 3: Gemini Pro**
```bash
python3 main.py --mode generation
# Select: Gemini Pro
# Generate: Same 5 articles
# Output: content_gemini/
```

#### Step 2: Compare Results

Create comparison spreadsheet:

| Metric | Claude | GPT-4 | Gemini |
|--------|--------|-------|--------|
| Avg word count | 850 | 820 | 900 |
| Natural language score | 9/10 | 8/10 | 7/10 |
| SEO optimization | 8/10 | 9/10 | 8/10 |
| Internal links quality | 9/10 | 8/10 | 7/10 |
| Processing time | 25 min | 20 min | 30 min |
| Cost per 1000 words | $0.15 | $0.30 | $0.05 |

#### Step 3: Choose Winner

Based on your priorities:
- **Best quality:** Claude Sonnet
- **Best SEO:** GPT-4
- **Best value:** Gemini Pro
- **Fastest:** GPT-4

Set as default in config.yaml:
```yaml
ai_models:
  default: "claude_sonnet"  # Winner!
```

---

## 🔄 Monthly Workflow

### Week 1: Data Collection
```bash
# Export fresh data from Search Console
# Name with date: queries_2024_10.xlsx
```

### Week 2: Analysis
```bash
# Run analysis
python main.py -i queries_2024_10.xlsx

# Compare with previous month
# Track improvements
```

### Week 3-4: Implementation
- Implement top 10 improvements from existing content
- Create 3-5 new articles from suggestions
- Track in project management tool

### Next Month: Measure Results
- Re-export data
- Compare rankings and traffic
- Iterate

---

## 💡 Pro Tips

### 1. Filtering Input Data
Before importing to the tool, filter Excel data:
- Remove branded queries (your brand name)
- Remove low-volume queries (< 10 impressions)
- Focus on specific sections if large site

### 2. Customizing AI Output
After getting suggestions, you can:
- Adjust H2 headings to match brand voice
- Combine similar article ideas
- Add brand-specific sections

### 3. Batch Processing
```bash
# Process multiple files
for file in data/*.xlsx; do
  python main.py -i "$file"
done
```

### 4. Integration with CMS
- Export improvement suggestions
- Import to your CMS via API or CSV
- Automate content briefs for writers

### 5. A/B Testing
- Implement AI suggestions on 50% of pages
- Compare performance after 30 days
- Roll out to remaining pages if successful

---

## 🔧 Advanced Configuration Examples

### High-Volume Site (10k+ queries)
```yaml
ai:
  qps: 2.0  # Faster processing if API allows
  temperature: 0.0  # Consistent results

app:
  min_position: 15  # Focus on biggest opportunities
  clustering_threshold: 0.8  # Stricter clustering
```

### Quality-Focused Site
```yaml
ai:
  qps: 0.5  # Slower, more thoughtful processing
  temperature: 0.3  # Slightly more creative suggestions
  
app:
  max_headings_per_article: 10  # Comprehensive outlines
```

### Budget-Conscious (minimize API calls)
```yaml
ai:
  qps: 0.3  # Slower to avoid rate limits
  max_retries: 2  # Fewer retries
  
# Pre-filter Excel to top 100 queries before processing
```

---

## 📈 Success Metrics

Track these metrics monthly:

1. **Queries moving from page 2 to page 1**
   - Target: 20% of improved pages

2. **New content ranking within 3 months**
   - Target: 50% of new articles on page 1-3

3. **Impressions increase**
   - Target: 30% increase in 3 months

4. **CTR improvement**
   - Target: 15% average CTR increase

---

## 🎯 Use Case Checklist

- [ ] Blog content optimization
- [ ] E-commerce product & category pages
- [ ] Local business SEO
- [ ] SaaS feature pages
- [ ] News & magazine sites
- [ ] Affiliate content sites
- [ ] Portfolio & agency sites
- [ ] Educational content
- [ ] Documentation sites
- [ ] Community & forum sites

---

## 🔍 Example 10: Keyword Synonym Finder - Comprehensive SEO Coverage

### Scenario
You have a list of primary keywords for your products/content, but you want to discover ALL possible ways users might search for them - including Persian, Finglish, keyboard mistakes, and misspellings.

### Workflow

1. **Prepare Input Excel**
   - Create an Excel file with keywords in column 1
   - First row is header ("کلمه اصلی")
   - One keyword per row
   
   Example: `input/keywords.xlsx`
   ```
   | کلمه اصلی |
   |----------|
   | گوشی     |
   | بذر      |
   | لپ‌تاپ    |
   | کیف      |
   ```

2. **Run Mode 5**
   ```bash
   python3 main.py --mode synonyms
   ```

3. **Interactive Steps**
   - System tests all AI models
   - Choose default model or select manually
   - Select your Excel file from `input/` folder
   - AI processes each keyword

4. **Review Output**
   - Excel file created in `output/synonyms/`
   - 9 columns with comprehensive variations

### Example Output

For keyword "گوشی" (phone):

| کلمه اصلی | مترادف‌های فارسی | فینگلیش | کیبورد انگلیسی | اختصارات | غلط‌املایی | معادل انگلیسی | مخفف | واژگان مرتبط |
|----------|-----------------|---------|----------------|---------|-----------|--------------|------|--------------|
| گوشی | موبایل، تلفن همراه، تلفن | gooshi, gushi, gooshy, gushy | ',ad, y,ad | موبایل | گوشئ، گوشیی، کوشی | mobile, phone, smartphone, cellphone | mob | اسمارت فون، تلفن هوشمند، موبایل فون |

For keyword "بذر" (seed):

| کلمه اصلی | مترادف‌های فارسی | فینگلیش | کیبورد انگلیسی | اختصارات | غلط‌املایی | معادل انگلیسی | مخفف | واژگان مرتبط |
|----------|-----------------|---------|----------------|---------|-----------|--------------|------|--------------|
| بذر | تخم، دانه | bazr, takhm, dane | f`v, jolh | بذر | بذرر، بذور | seed | - | نهال، کاشت، کشت، گیاه |

### Use Cases

#### 1. SEO Content Optimization
Use all variations in your content naturally:
- **Headers**: Use Persian synonyms
- **Body text**: Mix Persian and Finglish
- **Meta tags**: Include English equivalents
- **Alt text**: Use related terms

#### 2. Keyword Research
Identify which variations have search volume:
- Check Google Trends for each variation
- Use in Google Ads Keyword Planner
- Discover untapped search opportunities

#### 3. Search Console Analysis
Cross-reference with actual user queries:
- Compare variations with GSC data
- Find patterns in how users search
- Optimize for highest-volume variations

#### 4. Internal Search Optimization
Improve site search:
- Add all variations to search dictionary
- Handle misspellings automatically
- Support Finglish searches

#### 5. Content Localization
Create targeted content for different audiences:
- Persian speakers: Use formal Persian
- Younger audience: Include Finglish
- International: Use English equivalents
- Cover all bases: Use all variations

### Real-World Example: E-commerce Store

**Product**: Samsung Phone

**Step 1**: Generate synonyms for "گوشی سامسونگ"
```
کلمه اصلی: گوشی سامسونگ
```

**Step 2**: AI finds 50+ variations including:
- موبایل سامسونگ
- تلفن همراه سامسونگ
- gooshi samsung
- mobile samsung
- y,ad shls,kn (keyboard mistake)
- گوشی سامسونگ (misspelling: گوشئ سامسونگ)

**Step 3**: Use in content
```html
<h1>گوشی سامسونگ - خرید موبایل Samsung</h1>
<meta name="keywords" content="گوشی سامسونگ, موبایل samsung, gooshi samsung">
<p>تلفن همراه سامسونگ (Samsung Mobile) با بهترین قیمت...</p>
```

**Step 4**: Track performance
- Monitor which variations drive traffic
- Optimize for top-performing variations
- Create dedicated pages for high-volume variations

### Benefits

✅ **Complete Coverage**: Never miss a search variation
✅ **User Intent**: Understand how users search
✅ **Competitive Advantage**: Rank for variations competitors miss
✅ **Long-tail SEO**: Capture misspellings and variations
✅ **Localization**: Handle multilingual audiences
✅ **Content Ideas**: Generate content for each variation

### Tips

1. **Process in Batches**: For large keyword lists, split into batches of 50-100
2. **Validate Results**: Check search volume for AI-generated variations
3. **Natural Usage**: Use variations naturally, not keyword stuffing
4. **Update Regularly**: Re-run quarterly to find new variations
5. **Combine Modes**: Use with Mode 3 to generate content with variations

### Common Scenarios

#### Scenario A: Product Keywords
```
Input: Product names
Output: All possible ways customers search
Action: Optimize product titles and descriptions
```

#### Scenario B: Blog Topics
```
Input: Main blog topics
Output: Related keywords and variations
Action: Create content clusters around variations
```

#### Scenario C: Brand Names
```
Input: Your brand/product names
Output: Common misspellings and variations
Action: Create redirects and capture misspelled searches
```

### Success Story

**Before**: Ranking for "گوشی" only → 1,000 impressions/month

**After**: Optimized for 30+ variations
- گوشی → 1,000 impressions
- موبایل → 800 impressions
- gooshi → 300 impressions
- mobile → 500 impressions
- Misspellings → 200 impressions

**Total**: 2,800 impressions/month (+180% increase!)

---

**Each use case may require different configuration. Experiment and iterate!**


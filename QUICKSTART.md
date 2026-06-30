# Quick Start Guide - Seo Toolkit

Get up and running with Seo Toolkit in 5 minutes!

## 📋 Prerequisites

- Python 3.8 or higher
- Internet connection for AI API calls
- Google Search Console access (for Mode 1)
- Website sitemap URL (for all modes)

## ⚡ 5-Minute Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Keys
```bash
# Copy sample config
cp config.sample.yaml config.yaml

# Edit with your API keys
nano config.yaml
```

**Minimum setup for testing:**
```yaml
ai_models:
  default: "your_model_name"
  
  your_model_name:
    provider: "openai_compatible"
    api_key: "your-api-key"
    base_url: "your-api-url"
    model: "your-model"
```

### 3. Test the Setup
```bash
# Quick test with 10 items
python3 main.py --mode content --test
```

## 🎯 Three Ways to Use

### Mode 1: Content Optimization (Analyze & Get Ideas)
```bash
python3 main.py --mode content
```
**Input:** Google Search Console Excel files  
**Output:** Content improvement suggestions + New article ideas

### Mode 2: SEO Data Collection (Audit Your Site)
```bash
python3 main.py --mode scraping
```
**Input:** Sitemap URL  
**Output:** Complete SEO audit of all pages

### Mode 6: URL Index Diff (new vs submitted URLs)
```bash
python3 main.py --mode index-diff --domain example.com
```
**Input:** Sitemap URL + domain name  
**Output:** `new_urls_*.txt` + `already_submitted_*.txt`

## File Structure

```
seo-toolkit/
├── input/              # Search Console Excel files
├── output/             # Generated files
├── index_history/      # Submitted URL tracking per domain
├── config.yaml         # Your API configuration
└── main.py             # Run this file
```

## 🔑 API Keys Setup

### Option 1: Direct in config.yaml
```yaml
your_model:
  api_key: "sk-your-actual-key"
```

### Option 2: Environment Variables (Recommended)
```bash
export OPENAI_API_KEY="sk-your-key"
export ANTHROPIC_API_KEY="sk-ant-your-key"
```

Then in config.yaml:
```yaml
your_model:
  api_key: "env:OPENAI_API_KEY"
```

## 📊 Example Workflow

### Complete SEO Content Strategy:
```bash
# 1. Analyze your current performance
python3 main.py --mode content

# 2. Generate full articles from ideas
python3 main.py --mode generation

# 3. Audit your site SEO
python3 main.py --mode scraping
```

### Expected Results:
- **Mode 1**: 10-50 content improvement suggestions
- **Mode 2**: Complete SEO audit of 100-1000+ pages  
- **Mode 3**: 5-20 complete articles (2000+ words each)

## 🆘 Common Issues

### "No Excel files found"
```bash
# Copy your Search Console export to input folder
cp ~/Downloads/search_console_data.xlsx input/
```

### "API key not configured"
```bash
# Check your config.yaml has real API keys (not placeholders)
grep "YOUR_" config.yaml  # Should return nothing
```

### "No connected models"
```bash
# Test your API key manually
curl -H "Authorization: Bearer YOUR_KEY" https://api.openai.com/v1/models
```

## 📈 Next Steps

1. **Read the full documentation**: [README.md](README.md)
2. **See examples**: [EXAMPLES.md](EXAMPLES.md)
3. **Track changes**: [CHANGELOG.md](CHANGELOG.md)

## 🎉 You're Ready!

Run `python3 main.py` and start optimizing your SEO content!

---

**Need help?** Check the full documentation or create an issue on GitHub.
"""Interactive CLI prompts for Seo Toolkit."""

from src.cli.sections import print_section


def read_version() -> str:
    """
    Read version string from VERSION file.

    Output:
        Version string or fallback value.
    """
    try:
        with open("VERSION", "r", encoding="utf-8") as handle:
            return handle.read().strip()
    except FileNotFoundError:
        return "2.5.0"


def print_banner() -> None:
    """
    Display Seo Toolkit application banner.

    Output:
        Prints branded banner to stdout.
    """
    version = read_version()
    print("\n" + "=" * 70)
    print("Seo Toolkit")
    print("=" * 70)
    print(
        f"Version: {version} | Persian SEO + Multi-Model AI + Index Diff + Content Tools"
    )
    print("=" * 70 + "\n")


def get_project_name_interactive() -> str:
    """
    Collect project/domain name from the user.

    Output:
        Confirmed project name string.
    """
    print("\n" + "=" * 70)
    print("PROJECT IDENTIFICATION")
    print("=" * 70)
    print("\nEnter a name for this project (e.g., website domain or brand name)")
    print("This will be used to track content history and avoid duplicates.")
    print("\nExamples:")
    print("  - example.com")
    print("  - my-website")
    print("  - blog-project")
    print("-" * 70)

    while True:
        project_name = input("\nProject name: ").strip()

        if not project_name:
            print("Project name cannot be empty. Please try again.")
            continue

        if len(project_name) < 3:
            print("Project name must be at least 3 characters.")
            continue

        print(f"\nProject name: {project_name}")
        confirm = input("   Is this correct? (Y/n): ").strip().lower()

        if confirm not in ["n", "no"]:
            return project_name

        print("\n   Let's try again...")


def select_mode_interactive() -> str:
    """
    Interactive operational mode selection.

    Output:
        Mode key: content, scraping, generation, linking, synonyms, or index-diff.
    """
    print_banner()
    print("Please select operational mode:\n")
    print("  [1] Content Optimization")
    print("      Analyze Search Console data for content improvements")
    print("      Input: Excel files from Google Search Console")
    print("      Output: Improvement suggestions + New content ideas\n")
    print("  [2] SEO Data Collection")
    print("      Scrape page titles and meta tags from sitemap")
    print("      Input: Sitemap URL")
    print("      Output: Excel with SEO data for all pages\n")
    print("  [3] AI Content Generation")
    print("      Generate SEO-optimized content with AI")
    print("      Input: Excel file with headings")
    print("      Output: Full content in Excel, Word, and HTML formats\n")
    print("  [4] Internal Linking Only")
    print("      Add internal links to existing content")
    print("      Input: HTML/Word files with content")
    print("      Output: Updated content with internal links\n")
    print("  [5] Keyword Synonym Finder")
    print("      Find all semantic equivalents for keywords")
    print("      Input: Excel file with keywords (column 1)")
    print("      Output: Excel with all variations\n")
    print("  [6] URL Index Diff")
    print("      Compare sitemap URLs with previously submitted URLs")
    print("      Input: Sitemap URL + domain name")
    print("      Output: new_urls.txt + already_submitted.txt\n")
    print("-" * 70)

    mapping = {
        "1": "content",
        "2": "scraping",
        "3": "generation",
        "4": "linking",
        "5": "synonyms",
        "6": "index-diff",
    }

    while True:
        choice = input("Your selection (1-6): ").strip()
        if choice in mapping:
            return mapping[choice]
        print("Invalid choice. Please enter 1, 2, 3, 4, 5, or 6.")

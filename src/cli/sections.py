"""Section header formatting for CLI output."""


def print_section(title: str, step: str = "") -> None:
    """
    Print a formatted section header.

    Input:
        title: Section title text.
        step: Optional step indicator (e.g. "1/7").

    Output:
        Prints formatted header to stdout.
    """
    if step:
        print(f"\n{'=' * 70}")
        print(f"[{step}] {title}")
        print(f"{'=' * 70}\n")
    else:
        print(f"\n{'=' * 70}")
        print(f"{title}")
        print(f"{'=' * 70}\n")

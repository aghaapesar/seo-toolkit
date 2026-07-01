"""HTML form value parsing helpers."""


def parse_form_bool(value) -> bool:
    """
    Parse checkbox / form string values into bool.

    Input:
        value: bool, or string from multipart form ("true"/"false").

    Output:
        True when value represents an enabled checkbox.
    """
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("1", "true", "yes", "on")

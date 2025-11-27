import os
import requests

def fetch_calendar(source: str) -> str:
    """
    Fetches iCal data.
    - If 'source' is a URL (starts with http), download it.
    - If it's a file path, read it from disk.
    Returns raw ICS text.
    """

    # Case 1: URL mode
    if source.startswith("http://") or source.startswith("https://"):
        response = requests.get(source, timeout=10)
        response.raise_for_status()
        return response.text

    # Case 2: Local file mode
    if os.path.exists(source):
        with open(source, "r", encoding="utf-8") as f:
            return f.read()

    raise FileNotFoundError(f"Could not fetch calendar from: {source}")

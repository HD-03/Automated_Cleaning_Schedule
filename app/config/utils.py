import os
import yaml

def load_config(path: str = "config.yaml") -> dict:
    """
    Loads YAML configuration file and returns a dictionary.
    """

    
    # Find directory containing THIS file (utils.py)
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Config file is one level above: app/config.yaml
    config_path = os.path.abspath(os.path.join(base_dir, "..", path))

    with open(config_path, "r") as f:
        return yaml.safe_load(f)
    

def merge_bookings(bookings_lists):
    """
    Takes a list of booking lists (from multiple calendars)
    and merges them into one clean, sorted, deduplicated list.
    """

    merged = []

    # Combine everything into one list
    for lst in bookings_lists:
        merged.extend(lst)

    # Sort by start date
    merged.sort(key=lambda x: x["start"])

    # Deduplicate using UID (if available) OR start/end dates
    unique = []
    seen = set()

    for b in merged:
        # Deduping key
        key = (b["start"], b["end"])

        if key not in seen:
            seen.add(key)
            unique.append(b)

    return unique


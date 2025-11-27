import yaml

def load_config(path: str = "config.yaml") -> dict:
    """
    Loads YAML configuration file and returns a dictionary.
    """
    with open(path, "r") as f:
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


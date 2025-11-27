def diff_events(old_events: dict, new_events: dict) -> dict:
    """
    Compares old and new event dictionaries.
    Returns a dictionary describing added, removed, changed, and unchanged events.

    old_events: { id: { date, type, assigned_cleaner } }
    new_events: { id: { date, type, assigned_cleaner } }
    """

    added = {}
    removed = {}
    changed = {}
    unchanged = {}

    # Check for added & changed
    for event_id, new_data in new_events.items():
        if event_id not in old_events:
            added[event_id] = new_data
        else:
            old_data = old_events[event_id]
            if old_data == new_data:
                unchanged[event_id] = new_data
            else:
                changed[event_id] = {
                    "old": old_data,
                    "new": new_data
                }

    # Check for removed
    for event_id, old_data in old_events.items():
        if event_id not in new_events:
            removed[event_id] = old_data

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged
    }

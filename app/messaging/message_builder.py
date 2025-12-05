from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def format_event_line(event: dict) -> str:
    """
    Format a single cleaning event as a readable line.
    Example: "Tue 02 Dec – Cleaning: Checkin Not Same Day (CleanerA)"
    """
    # Convert "dd/mm/yyyy" to datetime
    dt = datetime.strptime(event["date"], "%d/%m/%Y")

    date_str = dt.strftime("%a %d %b")  # e.g. "Tue 02 Dec"
    cleaner = event.get("assigned_cleaner") or "Unassigned"

    return f"{date_str} – {event['type']} ({cleaner})"


def build_current_week_remaining_message(property_name: str, events: dict) -> str:
    """
    Show ALL remaining cleanings for THIS WEEK:
    - Starting from NOW (current time)
    - Ending at the upcoming Sunday 14:00 UK
    
    This is used for change notifications to show what's left in the current week.
    """

    # Current UK time
    now_uk = datetime.now(ZoneInfo("Europe/London"))

    # Compute the upcoming Sunday at 14:00 UK
    days_until_sunday = (6 - now_uk.weekday()) % 7
    
    # If today is Sunday
    if now_uk.weekday() == 6:
        # If it's before 14:00, cutoff is today at 14:00
        # If it's 14:00 or later, cutoff is next Sunday
        if now_uk.hour < 14 or (now_uk.hour == 14 and now_uk.minute < 10):
            days_until_sunday = 0
        else:
            days_until_sunday = 7
    
    sunday_2pm = (now_uk + timedelta(days=days_until_sunday)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )

    def in_remaining_window(ev):
        """Check if event falls between now and Sunday 14:00."""
        dt = datetime.strptime(ev["date"], "%d/%m/%Y").replace(
            tzinfo=ZoneInfo("Europe/London")
        )
        # Include events from now until Sunday 14:00
        return now_uk.date() <= dt.date() <= sunday_2pm.date()

    # Filter events
    window_events = [ev for ev in events.values() if in_remaining_window(ev)]

    # Sort chronologically
    window_events.sort(
        key=lambda e: datetime.strptime(e["date"], "%d/%m/%Y")
    )

    lines = [
        f"Updated Cleaning Schedule – {property_name}",
        f"{now_uk.strftime('%d %b')} → Sunday {sunday_2pm.strftime('%d %b %H:%M')}",
        "----------------------------------------",
    ]

    if not window_events:
        lines.append("No remaining cleanings for this week.")
    else:
        for event in window_events:
            lines.append(format_event_line(event))

    return "\n".join(lines)


def build_weekly_message(property_name: str, events: dict) -> str:
    """
    Build schedule for NEXT WEEK only (Monday → Sunday).
    This is sent on Sunday at 14:00 as a preview of the upcoming week.
    
    FIXED: Now uses UK timezone instead of naive datetime.
    """

    # Use UK timezone to ensure correct week calculation
    today = datetime.now(ZoneInfo("Europe/London"))

    # --- TEST OVERRIDE (uncomment to simulate specific dates) ---
    # Force the system to behave as if today is a specific date.
    # Example: pretend it's Sunday 7 Dec 2025 at 14:05
    # today = datetime(2025, 12, 7, 14, 5, tzinfo=ZoneInfo("Europe/London"))
    # -------------------------------------------------------------

    # Calculate next Monday (start of next week)
    days_to_monday = (7 - today.weekday()) % 7
    if days_to_monday == 0:  # If today is Monday
        days_to_monday = 7    # Get next Monday instead
    
    next_monday = today + timedelta(days=days_to_monday)
    
    # Calculate next Sunday (end of next week)
    next_sunday = next_monday + timedelta(days=6)

    def in_next_week(ev):
        """Check if event falls in next week (Monday through Sunday)."""
        dt = datetime.strptime(ev["date"], "%d/%m/%Y")
        return next_monday.date() <= dt.date() <= next_sunday.date()

    # Filter events into next week
    next_week_events = [
        ev for ev in events.values() if in_next_week(ev)
    ]

    # Sort chronologically
    next_week_events.sort(key=lambda e: datetime.strptime(e["date"], "%d/%m/%Y"))

    lines = [
        f"Weekly Cleaning Schedule – {property_name}",
        f"{next_monday.strftime('%d %b')} → {next_sunday.strftime('%d %b')}",
        "----------------------------------------",
    ]

    if not next_week_events:
        lines.append("No cleanings scheduled next week.")
    else:
        for event in next_week_events:
            lines.append(format_event_line(event))

    return "\n".join(lines)


def build_change_message(property_name: str, new_events: dict, diff: dict) -> str:
    """
    Build a message showing the updated schedule + the changes.
    
    Args:
        property_name: Name of the property
        new_events: All current events (will be filtered by build_current_week_remaining_message)
        diff: Dictionary with keys: added, removed, changed, unchanged
              Should be pre-filtered to only include changes before the cutoff
    
    The message includes:
    1. Current week remaining schedule (now → Sunday 14:00)
    2. List of changes that occurred
    """

    # First show the updated schedule (automatically filtered to current week)
    message = build_current_week_remaining_message(property_name, new_events)
    message += "\n\nChanges since last update:\n"

    # Handle added events
    if diff["added"]:
        for eid, event in diff["added"].items():
            dt = datetime.strptime(event["date"], "%d/%m/%Y")
            date_str = dt.strftime("%a %d %b")
            cleaner = event.get("assigned_cleaner") or "Unassigned"
            message += f"+ Added: {date_str} – {event['type']} ({cleaner})\n"

    # Handle removed events
    if diff["removed"]:
        for eid, event in diff["removed"].items():
            dt = datetime.strptime(event["date"], "%d/%m/%Y")
            date_str = dt.strftime("%a %d %b")
            cleaner = event.get("assigned_cleaner") or "Unassigned"
            message += f"- Removed: {date_str} – {event['type']} ({cleaner})\n"

    # Handle changed events
    if diff["changed"]:
        for eid, change in diff["changed"].items():
            old = change["old"]
            new = change["new"]

            dt = datetime.strptime(new["date"], "%d/%m/%Y")
            date_str = dt.strftime("%a %d %b")

            # Detect what changed
            changes = []
            if old.get("type") != new.get("type"):
                changes.append(f"type: {old.get('type')} → {new.get('type')}")
            if old.get("assigned_cleaner") != new.get("assigned_cleaner"):
                old_cleaner = old.get("assigned_cleaner") or "Unassigned"
                new_cleaner = new.get("assigned_cleaner") or "Unassigned"
                changes.append(f"cleaner: {old_cleaner} → {new_cleaner}")

            change_details = ", ".join(changes) if changes else "details updated"
            message += f"* Updated: {date_str} ({change_details})\n"

    # Handle "no changes" case
    if (not diff["added"] 
        and not diff["removed"] 
        and not diff["changed"]):
        message += "No changes.\n"

    return message
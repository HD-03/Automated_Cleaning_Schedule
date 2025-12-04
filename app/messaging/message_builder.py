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
    - Starting from the beginning of TODAY (00:00)
    - Ending at Sunday 14:00 UK
    """

    # Current UK time
    now_uk = datetime.now(ZoneInfo("Europe/London"))

    # Start of today (00:00 UK)
    start_of_today = now_uk.replace(hour=0, minute=0, second=0, microsecond=0)

    # Compute this coming Sunday at 14:00 UK
    days_until_sunday = (6 - now_uk.weekday()) % 7
    sunday_2pm = (now_uk + timedelta(days=days_until_sunday)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )

    def in_remaining_window(ev):
        dt = datetime.strptime(ev["date"], "%d/%m/%Y").replace(
            tzinfo=ZoneInfo("Europe/London")
        )
        # Include today fully, then up to Sunday 14:00
        return start_of_today.date() <= dt.date() <= sunday_2pm.date()

    # Filter events
    window_events = [ev for ev in events.values() if in_remaining_window(ev)]

    # Sort chronologically
    window_events.sort(
        key=lambda e: datetime.strptime(e["date"], "%d/%m/%Y")
    )

    lines = [
        f"Updated Cleaning Schedule – {property_name}",
        f"{start_of_today.strftime('%d %b')} → Sunday {sunday_2pm.strftime('%d %b %H:%M')}",
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
    Build schedule for NEXT WEEK only.
    """

    today = datetime.now()

    # --- TEST OVERRIDE ---
    # Force the system to behave as if today is a specific date.
    # Example: pretend it's 20 Jan 2025 (2025, 1, 20)
    #today = datetime(2025, 12, 28)



    # Next Monday
    next_monday = today + timedelta(days=(7 - today.weekday()))
    # Next Sunday
    next_sunday = next_monday + timedelta(days=6)

    def in_next_week(ev):
        dt = datetime.strptime(ev["date"], "%d/%m/%Y")
        return next_monday.date() <= dt.date() <= next_sunday.date()

    # Filter events into next week
    next_week_events = [
        ev for ev in events.values() if in_next_week(ev)
    ]

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
    diff = { added, removed, changed, unchanged }
    """

    # First show the updated schedule
    message = build_current_week_remaining_message(property_name, new_events)
    message += "\n\nChanges since last update:\n"

    # Handle added
    if diff["added"]:
        for eid, event in diff["added"].items():
            dt = datetime.strptime(event["date"], "%d/%m/%Y")
            date_str = dt.strftime("%a %d %b")
            message += f"+ Added cleaning on {date_str}\n"

    # Handle removed
    if diff["removed"]:
        for eid, event in diff["removed"].items():
            dt = datetime.strptime(event["date"], "%d/%m/%Y")
            date_str = dt.strftime("%a %d %b")
            message += f"- Removed cleaning on {date_str}\n"

    # Handle changed
    if diff["changed"]:
        for eid, change in diff["changed"].items():
            old = change["old"]
            new = change["new"]

            dt = datetime.strptime(new["date"], "%d/%m/%Y")
            date_str = dt.strftime("%a %d %b")

            message += f"* Updated cleaning on {date_str} (type changed)\n"

    # Handle "no changes"
    if (not diff["added"] 
        and not diff["removed"] 
        and not diff["changed"]):
        message += "No changes.\n"

    return message

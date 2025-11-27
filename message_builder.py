from datetime import datetime, timedelta


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
    message = build_weekly_message(property_name, new_events)
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

from config.utils import load_config, merge_bookings
from calendars.fetch_calendars import fetch_calendar
from calendars.parse_ical import parse_ical
from utils.save_ics_index import append_ics_index
from schedule.generate_schedule import detect_changeovers, save_schedule_csv
from schedule.generate_ics import save_schedule_ics, upload_to_gcs
from schedule.state_manager import load_previous_state, save_state
from schedule.diff_events import diff_events

from messaging.message_builder import build_weekly_message, build_change_message

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from messaging.emailer import send_email

open("ics_index.txt", "w").close()   # clear the file for fresh run


def event_dt(e):
    """Convert event dict to datetime object in UK timezone."""
    return datetime.strptime(e["date"], "%d/%m/%Y").replace(
        tzinfo=ZoneInfo("Europe/London")
    )


def change_before_cutoff(diff, cutoff, now_uk):
    """
    Check if any changes exist that fall within the window: now -> cutoff.
    Returns True if there are any added/removed/changed events in this window.
    """
    # Check added events
    for e in diff["added"].values():
        if now_uk <= event_dt(e) < cutoff:
            return True
    
    # Check removed events
    for e in diff["removed"].values():
        if now_uk <= event_dt(e) < cutoff:
            return True
    
    # Check changed events
    for c in diff["changed"].values():
        if now_uk <= event_dt(c["new"]) < cutoff:
            return True
    
    return False


def filter_diff_by_cutoff(diff, cutoff, now_uk):
    """
    Filter the diff to only include changes that happen between now and cutoff.
    This ensures we only report on changes relevant to the current week.
    """
    filtered = {"added": {}, "removed": {}, "changed": {}, "unchanged": {}}

    # Filter added events
    for k, e in diff["added"].items():
        if now_uk <= event_dt(e) < cutoff:
            filtered["added"][k] = e

    # Filter removed events
    for k, e in diff["removed"].items():
        if now_uk <= event_dt(e) < cutoff:
            filtered["removed"][k] = e

    # Filter changed events
    for k, c in diff["changed"].items():
        if now_uk <= event_dt(c["new"]) < cutoff:
            filtered["changed"][k] = c

    return filtered


def same_week(ts_iso: str, now: datetime) -> bool:
    """
    Check if timestamp (ISO string) is in the same calendar week as now.
    Uses ISO week numbering (year, week_number).
    """
    try:
        ts = datetime.fromisoformat(ts_iso)
    except Exception:
        return False

    # ISO week number comparison (year + week number)
    return ts.isocalendar()[:2] == now.isocalendar()[:2]


def calculate_next_sunday_cutoff(now_uk):
    """
    Calculate the next Sunday at 14:00 UK time from now.
    
    Rules:
    - If it's before Sunday 14:00 this week -> return this Sunday 14:00
    - If it's Sunday 14:00 or later -> return next Sunday 14:00
    """
    # How many days until next Sunday (0=Monday, 6=Sunday)
    days_until_sunday = (6 - now_uk.weekday()) % 7
    
    # If today is Sunday
    if now_uk.weekday() == 6:
        # If it's before 14:00, cutoff is today at 14:00
        # If it's 14:00 or later, cutoff is next Sunday
        if now_uk.hour < 14 or (now_uk.hour == 14 and now_uk.minute < 10):
            days_until_sunday = 0
        else:
            days_until_sunday = 7
    
    # Calculate the cutoff datetime
    cutoff = (now_uk + timedelta(days=days_until_sunday)).replace(
        hour=14, minute=0, second=0, microsecond=0
    )
    
    return cutoff


def main():
    config = load_config()

    for prop in config["properties"]:
        name = prop["name"]
        calendars = prop["calendars"]
        cleaners = prop.get("cleaners", [])
        pmc = prop.get("property_management_company")

        print(f"\n{'='*60}")
        print(f"Processing property: {name}")
        print(f"{'='*60}")

        # Fetch & parse each calendar
        bookings_lists = []
        for cal in calendars:
            raw_ical = fetch_calendar(cal)
            bookings = parse_ical(raw_ical)
            bookings_lists.append(bookings)

        # Merge into single list
        merged_bookings = merge_bookings(bookings_lists)

        # Detect cleaning tasks
        tasks = detect_changeovers(merged_bookings, name, cleaners)
        print(f"  → {len(tasks)} cleaning tasks found.")

        # Save CSV file for the property
        safe_name = name.replace(" ", "")
        csv_filename = f"{safe_name}.csv"
        save_schedule_csv(tasks, path=csv_filename)
        print(f"  → Saved CSV: {csv_filename}")

        # Save ICS file for the property
        ics_filename = f"{safe_name}.ics"
        public_url = save_schedule_ics(tasks, name, path=ics_filename, cleaners=cleaners)
        append_ics_index(
            company=prop["property_management_company"],
            property_name=prop["name"],
            public_url=public_url
        )
        print(f"  → Saved ICS: {ics_filename}")

        # -----------------------------------------------------------
        # EMAIL LOGIC
        # -----------------------------------------------------------

        # Build dictionary of new events keyed by ID
        new_events = {
            f"{name}-{t['date']}": {
                "date": t["date"],
                "type": t["type"],
                "assigned_cleaner": t["assigned_cleaner"]
            }
            for t in tasks
        }

        # Load previous state from GCS
        prev_state = load_previous_state(name)
        old_events = prev_state.get("events", {})

        # Diff old vs new to detect changes
        diff = diff_events(old_events, new_events)

        # Get current UK time
        now_utc = datetime.now(timezone.utc)
        now_uk = now_utc.astimezone(ZoneInfo("Europe/London"))

        # ===== TESTING OVERRIDE (uncomment to simulate specific times) =====
        # Simulate Sunday 2:05 PM UK:
        # now_uk = datetime(2025, 12, 7, 14, 5, tzinfo=ZoneInfo("Europe/London"))
        # Simulate Monday 10 AM UK:
        # now_uk = datetime(2025, 12, 8, 10, 0, tzinfo=ZoneInfo("Europe/London"))
        # ===================================================================

        print(f"  → Current time (UK): {now_uk.strftime('%A %d %b %Y, %H:%M')}")

        # Calculate cutoff (next Sunday @ 14:00 UK)
        cutoff = calculate_next_sunday_cutoff(now_uk)
        print(f"  → Cutoff time (next Sunday 14:00): {cutoff.strftime('%A %d %b %Y, %H:%M')}")

        # Check if it's Sunday summary time (Sunday between 14:00-14:09)
        # This narrow window matches the 10-minute cron schedule
        is_sunday_summary = (
            now_uk.weekday() == 6 and  # Sunday
            now_uk.hour == 14 and      # 2 PM hour
            now_uk.minute < 10         # First 10 minutes only
        )

        print(f"  → Is Sunday summary time? {is_sunday_summary}")

        # Check if any changes exist at all
        changes_exist = bool(diff["added"] or diff["removed"] or diff["changed"])
        print(f"  → Changes detected? {changes_exist}")

        # Check if changes are relevant (happen before cutoff)
        changes_before_cutoff = change_before_cutoff(diff, cutoff, now_uk)
        print(f"  → Changes before cutoff? {changes_before_cutoff}")

        # -----------------------------------------------------------
        # DECISION LOGIC
        # -----------------------------------------------------------

        # Weekly summary – must only be sent ONCE per week
        last_full = prev_state.get("last_full_message")
        already_sent_weekly = last_full and same_week(last_full, now_uk)

        should_send_weekly = is_sunday_summary and not already_sent_weekly
        should_send_change = (
            not is_sunday_summary and 
            changes_exist and 
            changes_before_cutoff
        )

        print(f"  → Should send weekly? {should_send_weekly}")
        print(f"  → Should send change? {should_send_change}")

        should_send_email = should_send_weekly or should_send_change

        # -----------------------------------------------------------
        # MESSAGE BUILDING
        # -----------------------------------------------------------

        if should_send_email:
            if is_sunday_summary:
                # Build weekly summary for next 7 days
                message = build_weekly_message(name, new_events)
                message_type = "WEEKLY SUMMARY"
            else:
                # Build change message with remaining week schedule + changes
                filtered_diff = filter_diff_by_cutoff(diff, cutoff, now_uk)
                message = build_change_message(name, new_events, filtered_diff)
                message_type = "CHANGE NOTIFICATION"

            print(f"\n--- {message_type} Message ---")
            print(message)
            print("---" + "-" * len(message_type) + "-----------")

            # -----------------------------------------------------------
            # SEND EMAIL
            # -----------------------------------------------------------

            print(f"\n📨 Attempting to send email...")
            
            try:
                subject = f"Cleaning Update – {name}"
                send_email(subject, message)
                print("✅ Email sent successfully!")

                # Only update state after successful send
                if should_send_weekly:
                    prev_state["last_full_message"] = now_utc.isoformat()
                    print("  → Marked weekly summary as sent")

            except Exception as e:
                print(f"❌ Email send failed: {str(e)}")
                print("  → State NOT saved. Will retry next run.")
                # Don't save state, so we retry next time
                continue

        else:
            print(f"\n⏭️  No email needed this run.")
            print(f"   Reason: ", end="")
            if is_sunday_summary and already_sent_weekly:
                print("Weekly summary already sent this week")
            elif not changes_exist:
                print("No changes detected")
            elif not changes_before_cutoff:
                print("Changes exist but not before cutoff")
            else:
                print("Not Sunday summary time and no relevant changes")

        # -----------------------------------------------------------
        # SAVE STATE
        # -----------------------------------------------------------

        # Save updated state back to GCS
        new_state = {
            "events": new_events,
            "last_full_message": prev_state.get("last_full_message")
        }
        save_state(name, new_state)
        print(f"  → State saved for {name}")

    print(f"\n{'='*60}")
    print("All properties processed.")
    print(f"{'='*60}\n")
    
    # Upload index of all ICS files
    upload_to_gcs("ics_index.txt", "cleaning-scheduler-bucket", "all_ics_links.txt")


if __name__ == "__main__":
    main()
from config.utils import load_config, merge_bookings
from calendars.fetch_calendars import fetch_calendar
from calendars.parse_ical import parse_ical
from utils.save_ics_index import append_ics_index
from schedule.generate_schedule import detect_changeovers, save_schedule_csv
from schedule.generate_ics import save_schedule_ics, upload_to_gcs
from schedule.state_manager import load_previous_state, save_state
from schedule.diff_events import diff_events

from messaging.message_builder import build_weekly_message, build_change_message

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from messaging.emailer import send_email

open("ics_index.txt", "w").close()   # clear the file for fresh run

def same_week(ts_iso: str, now: datetime) -> bool:
    """Check if timestamp (ISO string) is in the same calendar week as now."""
    try:
        ts = datetime.fromisoformat(ts_iso)
    except Exception:
        return False

    # ISO week number
    return ts.isocalendar()[:2] == now.isocalendar()[:2]


def main():
    config = load_config()

    for prop in config["properties"]:
        name = prop["name"]
        calendars = prop["calendars"]
        cleaners = prop.get("cleaners", [])
        pmc = prop.get("property_management_company")

        print(f"\nProcessing property: {name}")

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
        print(f"  → Saved file: {csv_filename}")

        # Save ICS file for the property
        ics_filename = f"{safe_name}.ics"
        public_url = save_schedule_ics(tasks, name, path=ics_filename, cleaners=cleaners)
        append_ics_index(
            company=prop["property_management_company"],
            property_name=prop["name"],
            public_url=public_url
        )
        print(f"  → Saved ICS file: {ics_filename}")

        # Print tasks for debugging
        #for t in tasks:
        #    print("   ", t)

        # -----------------------------------------------------------
        # --- WEEKLY / CHANGE MESSAGE LOGIC ---
        # -----------------------------------------------------------

        # Build dictionary of new events keyed by ID
        new_events = {
            t["id"]: {
                "date": t["date"],
                "type": t["type"],
                "assigned_cleaner": t["assigned_cleaner"]
            }
            for t in tasks
        }

        # Load previous state
        prev_state = load_previous_state(name)
        old_events = prev_state.get("events", {})

        # Diff old vs new
        diff = diff_events(old_events, new_events)

        # Determine if weekly summary time (Sunday @ 14:00 UTC)
        # Get current UK time
        now_utc = datetime.now(timezone.utc)
        now_uk = now_utc.astimezone(ZoneInfo("Europe/London"))

        # For testing, uncomment the line below to simulate Sunday 2PM UK time
        #now_uk = datetime(2025, 12, 7, 14, 0, tzinfo=ZoneInfo("Europe/London"))

        # True when it's Sunday 2PM UK time
        is_sunday_summary = (now_uk.weekday() == 6 and now_uk.hour == 14)

        # Draft message
        if is_sunday_summary:
            message = build_weekly_message(name, new_events)
            #prev_state["last_full_message"] = now_utc.isoformat()
        else:
            message = build_change_message(name, new_events, diff)

        # Log the drafted message
        print("--- Drafted Message ---")
        print(message.replace("\n", "\\n"))
        print("------------------------")

        #decide if message should be sent
        changes_exist = diff["added"] or diff["removed"] or diff["changed"]

        # Weekly summary – must only be sent ONCE per week
        last_full = prev_state.get("last_full_message")
        already_sent_weekly = last_full and same_week(last_full, now_uk)

        should_send_weekly = is_sunday_summary and not already_sent_weekly
        should_send_change = (not is_sunday_summary) and changes_exist

        should_send_email = should_send_weekly or should_send_change

        if should_send_email:
            print("📨 Sending email...")

            subject = f"Cleaning Update – {name}"
            send_email(subject, message)

            # Record weekly summary timestamp
            if should_send_weekly:
                prev_state["last_full_message"] = now_utc.isoformat()




        # Save updated state back to bucket
        new_state = {
            "events": new_events,
            "last_full_message": prev_state.get("last_full_message")
        }
        save_state(name, new_state)

    print("\nAll properties processed.\n")
    upload_to_gcs("ics_index.txt", "cleaning-scheduler-bucket", "all_ics_links.txt")



if __name__ == "__main__":
    main()

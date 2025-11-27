from config.utils import load_config, merge_bookings
from calendars.fetch_calendars import fetch_calendar
from calendars.parse_ical import parse_ical

from schedule.generate_schedule import detect_changeovers, save_schedule_csv
from schedule.generate_ics import save_schedule_ics
from schedule.state_manager import load_previous_state, save_state
from schedule.diff_events import diff_events

from messaging.message_builder import build_weekly_message, build_change_message

from datetime import datetime, timezone
from zoneinfo import ZoneInfo




def main():
    config = load_config()

    for prop in config["properties"]:
        name = prop["name"]
        calendars = prop["calendars"]
        cleaners = prop.get("cleaners", [])

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
        save_schedule_ics(tasks, name, path=ics_filename)
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
            prev_state["last_full_message"] = now_utc.isoformat()
        else:
            message = build_change_message(name, new_events, diff)

        # Log the drafted message
        print("--- Drafted Message ---")
        print(message.replace("\n", "\\n"))
        print("------------------------")



        # Save updated state back to bucket
        new_state = {
            "events": new_events,
            "last_full_message": prev_state.get("last_full_message")
        }
        save_state(name, new_state)

    print("\nAll properties processed.\n")


if __name__ == "__main__":
    main()

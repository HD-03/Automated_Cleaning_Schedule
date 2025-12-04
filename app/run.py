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

# Only consider changes happening before cutoff
def change_before_cutoff(diff, cutoff, now_uk):
    # added
    for e in diff["added"].values():
        if now_uk <= event_dt(e) < cutoff:
            return True
    # removed
    for e in diff["removed"].values():
        if now_uk <= event_dt(e) < cutoff:
            return True
    # changed
    for c in diff["changed"].values():
        if now_uk <= event_dt(c["new"]) < cutoff:
            return True
    return False

def filter_diff_by_cutoff(diff, cutoff, now_uk):
    filtered = {"added": {}, "removed": {}, "changed": {}, "unchanged": {}}

    # added
    for k, e in diff["added"].items():
        if now_uk <= event_dt(e) < cutoff:
            filtered["added"][k] = e

    # removed
    for k, e in diff["removed"].items():
        if now_uk <= event_dt(e) < cutoff:
            filtered["removed"][k] = e

    # changed
    for k, c in diff["changed"].items():
        if now_uk <= event_dt(c["new"]) < cutoff:
            filtered["changed"][k] = c

    return filtered

def event_dt(e):
    return datetime.strptime(e["date"], "%d/%m/%Y").replace(
        tzinfo=ZoneInfo("Europe/London")
    )


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
        property_change_email_sent = False
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
            f"{name}-{t['date']}": {
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
        
        # Compute next Sunday @ 14:00 UK
        days_to_sunday = (6 - now_uk.weekday()) % 7
        if days_to_sunday == 0 and now_uk.hour >= 14:
            days_to_sunday = 7
        # True when it's Sunday 2PM UK time
        is_sunday_summary = (now_uk.weekday() == 6 and now_uk.hour == 14)
        cutoff = (now_uk + timedelta(days=days_to_sunday)).replace(
            hour=14, minute=0, second=0, microsecond=0
        )
        # Draft message
        if is_sunday_summary:
            message = build_weekly_message(name, new_events)
            #prev_state["last_full_message"] = now_utc.isoformat()
        else:
           #message = build_change_message(name, new_events, diff)
           filtered = filter_diff_by_cutoff(diff, cutoff, now_uk)
           message = build_change_message(name, new_events, filtered)


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



        #should_send_change = (not is_sunday_summary) and changes_exist
        should_send_change = (
        not is_sunday_summary
        and changes_exist
        and change_before_cutoff(diff, cutoff, now_uk)
        )


        should_send_email = should_send_weekly or should_send_change

        if should_send_email and not property_change_email_sent:
            print("📨 Sending email...")

            subject = f"Cleaning Update – {name}"
            send_email(subject, message)
            property_change_email_sent = True


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

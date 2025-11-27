from utils import load_config, merge_bookings
from fetch_calendars import fetch_calendar
from parse_ical import parse_ical
from generate_schedule import detect_changeovers, save_schedule_csv
from generate_ics import save_schedule_ics



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

        #save csv files for the property

        safe_name = name.replace(" ", "")
        csv_filename = f"{safe_name}.csv"

        save_schedule_csv(tasks, path=csv_filename)

        print(f"  → Saved file: {csv_filename}")

        #save ics files for the property
        
        ics_filename = f"{safe_name}.ics"
        save_schedule_ics(tasks, path=ics_filename)
        print(f"  → Saved ICS file: {ics_filename}")


        # Print tasks for debugging
        for t in tasks:
            print("   ", t)

    print("\nAll properties processed.\n")


if __name__ == "__main__":
    main()

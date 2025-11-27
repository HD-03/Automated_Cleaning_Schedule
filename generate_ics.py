from icalendar import Calendar, Event
from datetime import datetime

def save_schedule_ics(tasks, path):
    """
    Creates an ICS calendar file containing all cleaning tasks for a property.
    """

    cal = Calendar()
    cal.add("prodid", "-//Cleaning Schedule//EN")
    cal.add("version", "2.0")

    for task in tasks:
        event = Event()

        # Convert "27 November 2025" → datetime object
        date_obj = datetime.strptime(task["date"], "%d/%m/%Y").date()

        event.add("uid", task["id"])
        event.add("summary", f"{task['type']} – {task['property']}")
        event.add("dtstart", date_obj)
        event.add("dtend", date_obj)  # all-day event

        cal.add_component(event)

    with open(path, "wb") as f:
        f.write(cal.to_ical())

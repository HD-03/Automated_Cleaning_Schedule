from icalendar import Calendar
from datetime import date
from typing import List

def parse_ical(ical_text: str) -> List[dict]:
    """
    Parses raw iCal text and extracts booking events.
    Returns a list of dicts, each representing one booking.
    """

    cal = Calendar.from_ical(ical_text)
    bookings = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("DTSTART").dt
        dtend = component.get("DTEND").dt

        # Normalize to date objects (ICS may include time or just date)
        if hasattr(dtstart, "date"):
            dtstart = dtstart.date()
        if hasattr(dtend, "date"):
            dtend = dtend.date()

        summary = str(component.get("SUMMARY", ""))
        uid = str(component.get("UID", ""))
        # Skip Airbnb blocked days only
        if summary.strip().lower() == "airbnb (not available)":
            continue


        bookings.append({
            "start": dtstart,
            "end": dtend,
            "summary": summary,
            "uid": uid,
        })

    return bookings

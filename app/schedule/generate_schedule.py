from typing import List, Dict
from datetime import date
import csv


def detect_changeovers(bookings: List[Dict], property_name: str, cleaners: List[str]):
    """
    Takes a sorted list of bookings for a property.
    Generates a list of cleaning tasks.
    """

    tasks = []

    for i, booking in enumerate(bookings):
        checkout_day = booking["end"]
        task_id = f"{property_name.replace(' ', '')}-{checkout_day.strftime('%d%m%Y')}"


        # Default type
        task_type = "Cleaning: Checkin Not Same Day"

        # Check for same-day check-in
        if i + 1 < len(bookings):
            next_booking = bookings[i + 1]
            if next_booking["start"] == checkout_day:
                task_type = "Cleaning: Checkin Same Day"

        tasks.append({
            "id": task_id,
            "date": checkout_day.strftime("%d/%m/%Y"),
            "property": property_name,
            "type": task_type,
            "assigned_cleaner": cleaners[0] if cleaners else None,
            #"booking_summary": booking["summary"],
        })

    return tasks

def save_schedule_csv(tasks, path="schedule.csv"):
    """
    Saves cleaning tasks to a CSV file.
    """

    fieldnames = ["id", "date", "property", "type", "assigned_cleaner"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(tasks)

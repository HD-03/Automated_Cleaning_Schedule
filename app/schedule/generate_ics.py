from icalendar import Calendar, Event
from datetime import datetime
from google.cloud import storage

def upload_to_gcs(local_path, bucket_name, object_name):
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(object_name)
    blob.upload_from_filename(local_path)
    return f"https://storage.googleapis.com/{bucket_name}/{object_name}"

def save_schedule_ics(tasks, property_name, path, cleaners = None):
    cal = Calendar()
    cal.add("prodid", "-//Cleaning Schedule//EN")
    cal.add("version", "2.0")

    # This sets the calendar name users see in Google/Apple Calendar
    cal.add("X-WR-CALNAME", f"{property_name} – Cleaning Schedule")


    for task in tasks:
        event = Event()

        # Convert "27 November 2025" → datetime object
        date_obj = datetime.strptime(task["date"], "%d/%m/%Y").date()

        event.add("uid", task["id"])
        event.add("summary", f"{task['type']} – {task['property']}")

        if cleaners:
            if isinstance(cleaners, list):
                clean_str = ", ".join(cleaners)
            else:
                clean_str = cleaners

            event.add("description", f"Cleaner: {clean_str}")

        event.add("dtstart", date_obj)
        event.add("dtend", date_obj)  # all-day event

        cal.add_component(event)

    # Write to local file first
    with open(path, "wb") as f:
        f.write(cal.to_ical())

    # Upload to GCS
    bucket_name = "cleaning-scheduler-bucket"
    object_name = path 
    public_url = upload_to_gcs(path, bucket_name, object_name)

    print(f"Uploaded to: {public_url}")
    return public_url


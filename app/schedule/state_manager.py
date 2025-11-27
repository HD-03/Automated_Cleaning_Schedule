import json
from google.cloud import storage
from google.api_core.exceptions import NotFound

BUCKET_NAME = "cleaning-scheduler-bucket"


def _get_blob(property_name: str):
    """
    Returns the GCS blob object for the property’s state file.
    """
    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    filename = f"{property_name}_state.json"
    return bucket.blob(filename)


def load_previous_state(property_name: str) -> dict:
    """
    Loads the previous state for a property from GCS.
    If the file does not exist, returns an empty default structure.
    """
    blob = _get_blob(property_name)

    try:
        data = blob.download_as_text()
        return json.loads(data)
    except NotFound:
        # No previous state exists yet
        return {
            "events": {},              # empty dictionary of events
            "last_full_message": None  # no weekly message ever sent
        }


def save_state(property_name: str, state: dict):
    """
    Saves the given state dictionary to GCS as JSON.
    """
    blob = _get_blob(property_name)
    blob.upload_from_string(
        json.dumps(state, indent=2),
        content_type="application/json"
    )
    print(f"Saved state for {property_name} to {blob.name}")

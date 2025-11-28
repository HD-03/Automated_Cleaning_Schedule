import requests
import json
import os


def send_whatsapp_message(to_number: str, message: str) -> bool:
    """
    Sends a WhatsApp message via the WhatsApp Cloud API.
    
    Args:
      to_number (str): Recipient phone number in international format (e.g. "+447123456789")
      message (str): The message body text

    Returns:
      bool: True if sent successfully, False otherwise
    """

    # Load from environment variables
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")

    if not token or not phone_number_id:
        raise ValueError("WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID must be set")

    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": message
        }
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        return True

    print("WhatsApp send error:", response.status_code, response.text)
    return False

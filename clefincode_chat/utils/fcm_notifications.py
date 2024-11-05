import frappe
import json
import firebase_admin
from firebase_admin import  credentials, messaging
from bs4 import BeautifulSoup

def initialize_firebase():
    firebase_server_key = frappe.db.get_single_value("ClefinCode Chat Settings", "firebase_server_key")
    cleaned_key = firebase_server_key.strip() if firebase_server_key else None

    if not cleaned_key:
        return
    else:
        cred_dict = json.loads(cleaned_key)
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)

initialize_firebase()

@frappe.whitelist(allow_guest = True)
def send_notification_via_firebase(registration_token, info, realtime_type, platform=None, title=None, body=None, same_user=None, is_call=None):
    message = None

    try:
        # Case 1: Specific real-time types or same user
        if realtime_type in ["typing", "update_sub_channel_for_last_message"] or same_user == 1:
            message = messaging.Message(
                notification=messaging.Notification(title=None, body=None),
                data={
                    "route": str(info),
                    "realtime_type": realtime_type,
                    "content_available": "true",
                    "same_user": str(same_user)
                },
                token=registration_token,
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(content_available=True, sound="default")
                    )
                )
            )
            messaging.send(message)

        # Case 2: Different behavior for iOS platform
        else:
            # Handle iOS-specific modifications
            if platform == "ios":
                # Modify voice clip content if applicable
                if info and info.get("is_voice_clip") == "1":
                    soup = BeautifulSoup(info["content"], 'html.parser')
                    voice_clip_containers = soup.find_all('div', class_='voice-clip-container')
                    for container in voice_clip_containers:
                        for child in container.find_all('button', recursive=False):
                            child.decompose()
                    info["content"] = str(soup)

                # Send the first message with minimal details
                message = messaging.Message(
                    notification=messaging.Notification(title=None, body=None),
                    data={
                        "route": str(info),
                        "realtime_type": realtime_type,
                        "notification_title": title or '',
                        "notification_body": body or '',
                        "no_duplicate": "true",
                        "content_available": "true",
                        "same_user": str(same_user)
                    },
                    token=registration_token,
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(content_available=True, sound="default")
                        )
                    )
                )
                messaging.send(message)

                # Send the second message with full notification details
                message1 = messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data={
                        "route": str(info),
                        "realtime_type": realtime_type,
                        "notification_title": title or '',
                        "notification_body": body or '',
                        "same_user": str(same_user),
                        "content_available": "true"
                    },
                    token=registration_token,
                    apns=messaging.APNSConfig(
                        payload=messaging.APNSPayload(
                            aps=messaging.Aps(content_available=True, sound="default")
                        )
                    )
                )
                messaging.send(message1)

            # Case 3: For non-iOS platforms (e.g., Android)
            else:
                message = messaging.Message(
                    notification=messaging.Notification(),
                    data={
                        "route": str(info),
                        "realtime_type": realtime_type,
                        "notification_title": title or '',
                        "notification_body": body or ''
                    },
                    token=registration_token
                )
                messaging.send(message)

    except Exception as e:
        error_type = "IOS Error" if platform == "ios" else "Android Error" if platform else "General Error"
        frappe.log_error(f"{error_type} in sending notifications: {str(e)}")
# # ============================================================================


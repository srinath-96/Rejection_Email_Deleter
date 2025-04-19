# gmail_utils.py
import os
import base64
import traceback
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Import configuration constants
import config

def get_gmail_service():
    """
    Authenticates with Gmail API using configured settings.
    Returns the authenticated Gmail service object or None on failure.
    """
    creds = None
    print(f"--- Starting Gmail Authentication ---")
    if os.path.exists(config.GMAIL_TOKEN_PATH):
        print(f"Loading Gmail credentials from: {config.GMAIL_TOKEN_PATH}")
        try:
            creds = Credentials.from_authorized_user_file(config.GMAIL_TOKEN_PATH, config.GMAIL_SCOPES)
        except Exception as e:
            print(f"Error loading {config.GMAIL_TOKEN_PATH}: {e}. Will re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        print("Gmail credentials not found, invalid, or expired.")
        if creds and creds.expired and creds.refresh_token:
            print("Attempting to refresh Gmail token...")
            try:
                creds.refresh(Request())
                print("Gmail token refreshed successfully.")
                try:
                    with open(config.GMAIL_TOKEN_PATH, 'w') as token: token.write(creds.to_json())
                    print(f"Refreshed Gmail token saved to {config.GMAIL_TOKEN_PATH}")
                except Exception as e: print(f"Error saving refreshed Gmail token: {e}")
            except Exception as e:
                print(f"Error refreshing Gmail token: {e}. Need to re-authenticate.")
                creds = None
                if os.path.exists(config.GMAIL_TOKEN_PATH):
                     try: os.remove(config.GMAIL_TOKEN_PATH); print(f"Removed invalid Gmail token file: {config.GMAIL_TOKEN_PATH}")
                     except OSError as oe: print(f"Error removing token file {config.GMAIL_TOKEN_PATH}: {oe}")


        if not creds:
            print("Starting new Gmail authentication flow...")
            if not os.path.exists(config.GMAIL_CREDENTIALS_PATH):
                print(f"CRITICAL ERROR: Gmail credentials '{config.GMAIL_CREDENTIALS_PATH}' not found."); return None
            try:
                flow = InstalledAppFlow.from_client_secrets_file(config.GMAIL_CREDENTIALS_PATH, config.GMAIL_SCOPES)
                print("-" * 60 + "\nStarting local server for Gmail Auth. Follow browser instructions.\n" + "-" * 60)
                creds = flow.run_local_server(port=config.GMAIL_AUTH_PORT, open_browser=False)
                print("--- Gmail run_local_server process completed ---")
            except Exception as e: print(f"!!! Error during Gmail authentication flow !!!"); traceback.print_exc(); return None

            if creds:
                print("Gmail authentication successful, saving credentials...")
                try:
                    with open(config.GMAIL_TOKEN_PATH, 'w') as token: token.write(creds.to_json())
                    print(f"Credentials saved to {config.GMAIL_TOKEN_PATH}")
                except Exception as e: print(f"Error saving token: {e}")
            else: print("Gmail authentication flow did not result in valid credentials."); return None

    print("Attempting to build Gmail service...")
    try:
        if creds and creds.valid:
            service = build('gmail', 'v1', credentials=creds)
            print("Gmail service created successfully.")
            return service # Return the service object
        else: print("Authentication failed or credentials invalid, cannot create Gmail service."); return None
    except Exception as e: print(f'An unexpected error occurred building the Gmail service:'); traceback.print_exc(); return None


def get_email_details(gmail_service, message_id):
    """
    Fetches full email details including subject, sender, and plain text body.
    Requires the authenticated gmail_service object.
    """
    if not gmail_service:
        print("  [Error] Gmail service object not provided to get_email_details.")
        return None
    try:
        message_data = gmail_service.users().messages().get(userId='me', id=message_id, format='full').execute()
        payload = message_data.get('payload', {})
        headers = payload.get('headers', [])
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), 'Unknown Sender')
        body = ""
        def decode_part(data): return base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
        if 'parts' in payload:
            parts_queue = list(payload['parts'])
            while parts_queue:
                part = parts_queue.pop(0)
                mime_type = part.get('mimeType', '')
                if mime_type == 'text/plain' and 'data' in part.get('body', {}):
                    body = decode_part(part['body']['data']); break
                # Look inside multipart containers
                elif 'parts' in part and mime_type.startswith('multipart/'):
                     # Prepend nested parts to process them next (DFS-like)
                    parts_queue = part['parts'] + parts_queue

        elif 'body' in payload and 'data' in payload['body']:
             if 'text/plain' in payload.get('mimeType', ''): body = decode_part(payload['body']['data'])
        if not body: body = message_data.get('snippet', ''); print(f"  [Warning] Using snippet for msg {message_id}.")

        return {'id': message_id, 'subject': subject, 'sender': sender, 'body': body}

    except HttpError as error: print(f"  [Error] Gmail API error fetching message {message_id}: {error}"); return None
    except Exception as e: print(f"  [Error] Unexpected error fetching message {message_id}:"); traceback.print_exc(); return None
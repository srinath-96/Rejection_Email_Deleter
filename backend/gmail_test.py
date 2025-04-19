import os
import os.path
import traceback # For detailed error printing

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import webbrowser # Still useful for catching potential errors

# --- Configuration ---
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
TOKEN_PATH = 'token.json'
CREDENTIALS_PATH = '/Users/srinathmurali/Desktop/email_cleanup/credentials.json'
AUTH_PORT = 8888 # Make sure this matches your Cloud Console setup!

# --- Check for Credentials File ---
# (No upload needed locally, just check existence)
if not os.path.exists(CREDENTIALS_PATH):
    print(f"CRITICAL ERROR: '{CREDENTIALS_PATH}' not found in the current directory.")
    print("Please download it from Google Cloud Console and place it here.")
    exit() # Stop the script if credentials are missing
else:
    print(f"'{CREDENTIALS_PATH}' found.")

# --- Authentication Function (Based on your provided code, with open_browser=False) ---
def get_gmail_service():
    creds = None
    print("--- Starting Authentication ---")
    if os.path.exists(TOKEN_PATH):
        try:
           creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
           print(f"Loaded credentials from {TOKEN_PATH}")
        except Exception as e:
            print(f"Error loading {TOKEN_PATH}: {e}. Re-authenticating.")
            if os.path.exists(TOKEN_PATH):
                os.remove(TOKEN_PATH) # Remove invalid token file
            creds = None

    if not creds or not creds.valid:
        print("Credentials not found, invalid, or expired.")
        if creds and creds.expired and creds.refresh_token:
            print("Attempting to refresh token...")
            try:
                creds.refresh(Request())
                print("Token refreshed successfully.")
                # Save refreshed token
                try:
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                    print(f"Refreshed token saved to {TOKEN_PATH}")
                except Exception as e:
                    print(f"Error saving refreshed token: {e}")
            except Exception as e:
                print(f"Error refreshing token: {e}. Need to re-authenticate.")
                creds = None
                if os.path.exists(TOKEN_PATH):
                    os.remove(TOKEN_PATH)
                    print(f"Removed potentially invalid token file: {TOKEN_PATH}")

        if not creds: # Only run the flow if creds are missing/invalid/refresh failed
            print("Starting new authentication flow...")
            # CREDENTIALS_PATH check already done above
            try:
                print(f"Creating InstalledAppFlow from {CREDENTIALS_PATH}")
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_PATH, SCOPES)

                # *** Use run_local_server with open_browser=False for local script ***
                print("-" * 60)
                print(f"Attempting to start local server on port {AUTH_PORT} for authentication.")
                print("The script will print a URL. Please open it in your browser.")
                print("Make sure you are logged into the correct Google Account.")
                print("Grant permissions, and then ignore the 'This site can’t be reached' error in the browser.")
                print("The script should automatically detect the successful authorization and continue.")
                print("-" * 60)
                # Changed open_browser to False
                creds = flow.run_local_server(port=AUTH_PORT, open_browser=False)
                # Script should pause here until browser auth is done
                print("--- run_local_server process completed ---")

            except webbrowser.Error as wb_error:
                # This error is less likely with open_browser=False
                print(f"Webbrowser error during auth flow: {wb_error}")
                return None
            except Exception as e:
                 print(f"!!! Error during authentication flow !!!")
                 traceback.print_exc()
                 return None

            if creds: # Save the credentials only if flow succeeded
                print("Authentication successful, saving credentials...")
                try:
                    with open(TOKEN_PATH, 'w') as token:
                        token.write(creds.to_json())
                    print(f"Credentials saved to {TOKEN_PATH}")
                except Exception as e:
                    print(f"Error saving token: {e}")
            else:
                print("Authentication flow did not result in valid credentials.")
                return None # Stop if auth failed

    # Build and return the service
    print("Attempting to build Gmail service...")
    try:
        if creds and creds.valid: # Ensure creds exist and are valid before building
            service = build('gmail', 'v1', credentials=creds)
            print("Gmail service created successfully.")
            return service
        else:
            print("Authentication failed or credentials invalid, cannot create Gmail service.")
            return None
    except HttpError as error:
        print(f'An error occurred building the service: {error}')
        return None
    except Exception as e:
        print(f'An unexpected error occurred building the service: {e}')
        traceback.print_exc()
        return None

# --- Now call the function ---
service = get_gmail_service()

# --- Test listing emails (from your original script block) ---
if service:
    print("\n--- Attempting to list emails ---")
    try:
        # List labels as a simple test instead of messages first
        print("Fetching labels...")
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])

        if not labels:
            print("No labels found.")
        else:
            print("Labels:")
            for label in labels[:10]: # Print first 10 labels
                print(f"- {label['name']} (ID: {label['id']})")

        # Original email listing test
        print("\nFetching first 5 Inbox messages (metadata)...")
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=5).execute()
        messages = results.get('messages', [])
        if not messages:
            print("No messages found in Inbox.")
        else:
            print("Inbox messages (up to 5):")
            for message in messages:
                # Request specific headers for efficiency
                msg = service.users().messages().get(userId='me', id=message['id'], format='metadata', metadataHeaders=['Subject', 'From', 'Date']).execute()
                subject = 'No Subject'
                sender = 'Unknown Sender'
                date_val = 'Unknown Date'
                if 'payload' in msg and 'headers' in msg['payload']:
                     headers = msg['payload']['headers']
                     subject_header = next((h for h in headers if h['name'].lower() == 'subject'), None)
                     from_header = next((h for h in headers if h['name'].lower() == 'from'), None)
                     date_header = next((h for h in headers if h['name'].lower() == 'date'), None)
                     if subject_header:
                         subject = subject_header['value']
                     if from_header:
                         sender = from_header['value']
                     if date_header:
                         date_val = date_header['value']
                print(f"- ID: {message['id']}, From: {sender}, Date: {date_val}, Subject: {subject}")

    except HttpError as error:
        print(f'An error occurred listing labels/emails: {error}')
    except Exception as e:
        print(f'An unexpected error occurred listing labels/emails:')
        traceback.print_exc()
else:
    print("\nGmail service not available, cannot list labels/emails.")

print("\n--- Script Finished ---")
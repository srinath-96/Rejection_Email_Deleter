import os
import os.path
import traceback # For detailed error printing
import base64 # Needed for the tool's potential future use, though not directly here

# --- Google API / Gmail ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# Gmail API Settings (same as before)
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
GMAIL_TOKEN_PATH = 'gmail_token.json'
GMAIL_CREDENTIALS_PATH = '/Users/srinathmurali/Desktop/email_cleanup/credentials.json'
GMAIL_AUTH_PORT = 8888 # Port used for Gmail OAuth flow

# --- Global variable to hold the Gmail service ---
gmail_service_global = None

# --- Gmail Authentication Function (Copied from previous working version) ---
def get_gmail_service():
    """Authenticates with Gmail API and returns True if successful, populating gmail_service_global."""
    global gmail_service_global
    creds = None
    print(f"--- Starting Gmail Authentication ---")
    if os.path.exists(GMAIL_TOKEN_PATH):
        print(f"Loading Gmail credentials from: {GMAIL_TOKEN_PATH}")
        try:
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_PATH, GMAIL_SCOPES)
        except Exception as e:
            print(f"Error loading {GMAIL_TOKEN_PATH}: {e}. Will re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        print("Gmail credentials not found, invalid, or expired.")
        if creds and creds.expired and creds.refresh_token:
            print("Attempting to refresh Gmail token...")
            try:
                creds.refresh(Request())
                print("Gmail token refreshed successfully.")
                try:
                    with open(GMAIL_TOKEN_PATH, 'w') as token: token.write(creds.to_json())
                    print(f"Refreshed Gmail token saved to {GMAIL_TOKEN_PATH}")
                except Exception as e: print(f"Error saving refreshed Gmail token: {e}")
            except Exception as e:
                print(f"Error refreshing Gmail token: {e}. Need to re-authenticate.")
                creds = None
                if os.path.exists(GMAIL_TOKEN_PATH): os.remove(GMAIL_TOKEN_PATH); print(f"Removed invalid Gmail token file: {GMAIL_TOKEN_PATH}")

        if not creds:
            print("Starting new Gmail authentication flow...")
            if not os.path.exists(GMAIL_CREDENTIALS_PATH):
                print(f"CRITICAL ERROR: Gmail credentials '{GMAIL_CREDENTIALS_PATH}' not found."); return False
            try:
                flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDENTIALS_PATH, GMAIL_SCOPES)
                print("-" * 60 + "\nStarting local server for Gmail Auth. Follow browser instructions.\n" + "-" * 60)
                creds = flow.run_local_server(port=GMAIL_AUTH_PORT, open_browser=False)
                print("--- Gmail run_local_server process completed ---")
            except Exception as e: print(f"!!! Error during Gmail authentication flow !!!"); traceback.print_exc(); return False

            if creds:
                print("Gmail authentication successful, saving credentials...")
                try:
                    with open(GMAIL_TOKEN_PATH, 'w') as token: token.write(creds.to_json())
                    print(f"Credentials saved to {GMAIL_TOKEN_PATH}")
                except Exception as e: print(f"Error saving token: {e}")
            else: print("Gmail authentication flow did not result in valid credentials."); return False

    print("Attempting to build Gmail service...")
    try:
        if creds and creds.valid:
            gmail_service_global = build('gmail', 'v1', credentials=creds) # Assign to global
            print("Gmail service created successfully.")
            return True # Indicate success
        else: print("Authentication failed or credentials invalid, cannot create Gmail service."); return False
    except Exception as e: print(f'An unexpected error occurred building the Gmail service:'); traceback.print_exc(); return False


# --- Tool Definition (Exactly as intended for ADK) ---
def delete_email_tool(message_id: str) -> dict:
    """
    Deletes the specified email message by moving it to the Trash in Gmail.
    Use this ONLY after confirming an email IS a job rejection.

    Args:
        message_id (str): The unique ID of the Gmail message to be deleted.

    Returns:
        dict: A dictionary indicating the status ('success' or 'error')
              and an optional 'message'.
    """
    # This print is helpful for seeing when the function is called in testing
    print(f"\n--- Attempting to execute delete_email_tool ---")
    print(f"--- Target message_id: {message_id} ---")

    if not gmail_service_global:
        print("  [Test Error] Gmail service is not available.")
        return {"status": "error", "message": "Gmail service not initialized."}
    if not message_id or not isinstance(message_id, str) or len(message_id) < 5: # Basic check
        print(f"  [Test Error] Invalid message_id provided: '{message_id}'.")
        return {"status": "error", "message": "Invalid or missing message_id argument."}

    try:
        # Use the globally available gmail_service object
        gmail_service_global.users().messages().trash(userId='me', id=message_id).execute()
        print(f"  [Tool Success] Moved message {message_id} to Trash via Gmail API.")
        return {"status": "success", "message": f"Email {message_id} moved to Trash."}
    except HttpError as error:
        # Specifically check for 404 Not Found, which means the ID was likely invalid
        if error.resp.status == 404:
             print(f"  [Tool Error] Failed to move message {message_id} to Trash: 404 Not Found. Likely an invalid message ID.")
             return {"status": "error", "message": f"API Error deleting message {message_id}: 404 Not Found (Invalid ID?)."}
        else:
            print(f"  [Tool Error] Failed to move message {message_id} to Trash: {error}")
            return {"status": "error", "message": f"API Error deleting message {message_id}: {error}"}
    except Exception as e:
        print(f"  [Tool Error] Unexpected error moving message {message_id}:")
        traceback.print_exc()
        return {"status": "error", "message": f"Unexpected error deleting message {message_id}: {e}"}

# --- Function to List Recent Emails (for getting a test ID) ---
def list_recent_emails(max_results=10):
    """Lists recent emails from the Inbox to help find a test ID."""
    print("\n--- Fetching recent emails to find a test ID ---")
    if not gmail_service_global:
        print("Gmail service not available. Cannot list emails.")
        return

    try:
        results = gmail_service_global.users().messages().list(
            userId='me', labelIds=['INBOX'], maxResults=max_results
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No messages found in Inbox.")
            return

        print(f"Found {len(messages)} messages in Inbox. Details:")
        print("-" * 30)
        for i, message in enumerate(messages):
            msg_id = message['id']
            try:
                # Get metadata for display
                msg = gmail_service_global.users().messages().get(
                    userId='me', id=msg_id, format='metadata', metadataHeaders=['Subject', 'From', 'Date']
                ).execute()
                subject = 'No Subject'
                sender = 'Unknown Sender'
                date_val = 'Unknown Date'
                if 'payload' in msg and 'headers' in msg['payload']:
                     headers = msg['payload']['headers']
                     subject_header = next((h for h in headers if h['name'].lower() == 'subject'), None)
                     from_header = next((h for h in headers if h['name'].lower() == 'from'), None)
                     date_header = next((h for h in headers if h['name'].lower() == 'date'), None)
                     if subject_header: subject = subject_header['value']
                     if from_header: sender = from_header['value']
                     if date_header: date_val = date_header['value']
                print(f"{i+1}. ID: {msg_id}")
                print(f"   From: {sender}")
                print(f"   Subject: {subject[:80]}...") # Truncate long subjects
                print(f"   Date: {date_val}")
                print("-" * 10)
            except HttpError as detail_error:
                print(f"{i+1}. ID: {msg_id} - Error fetching details: {detail_error}")
                print("-" * 10)
        print("-" * 30)

    except HttpError as error:
        print(f"An error occurred listing emails: {error}")
    except Exception as e:
        print(f"An unexpected error occurred listing emails:")
        traceback.print_exc()


# --- Main Execution Logic for Testing ---
def main():
    """Main function to authenticate, get user input, and test the tool."""
    print("--- Starting Gmail Tool Test Script ---")

    # 1. Authenticate with Gmail
    if not get_gmail_service():
        print("\nExiting: Failed to initialize Gmail service.")
        return

    # 2. List recent emails to help user find an ID
    list_recent_emails()

    # 3. Get message ID from user
    print("\n--- Tool Test Input ---")
    print("Find the 'ID' of an email from the list above (or from your Gmail) that you want to TEST deleting.")
    print("!!! WARNING: This will move the selected email to the Trash !!!")
    message_id_to_test = input("Enter the message ID to test deleting (or press Enter to skip): ").strip()

    if not message_id_to_test:
        print("\nSkipping tool test.")
        print("--- Script Finished ---")
        return

    # 4. Confirm Deletion
    print(f"\nYou entered message ID: {message_id_to_test}")
    confirmation = input("Are you ABSOLUTELY SURE you want to move this email to Trash? (y/n): ").lower().strip()

    if confirmation == 'y':
        # 5. Call the tool function directly
        result = delete_email_tool(message_id_to_test)

        # 6. Print the result from the tool
        print("\n--- Tool Execution Result ---")
        print(f"Status: {result.get('status')}")
        print(f"Message: {result.get('message')}")
    else:
        print("\nDeletion cancelled by user.")

    print("\n--- Script Finished ---")


# --- Run the main function ---
if __name__ == "__main__":
    # Ensure prerequisites before running:
    # 1. `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib`
    # 2. `credentials.json` (for Gmail) exists.
    # 3. Delete `gmail_token.json` to force re-auth if needed.
    main()
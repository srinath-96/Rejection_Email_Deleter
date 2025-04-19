import os
import os.path
import traceback
import base64
import time
from email.message import EmailMessage

# --- Google API / Gmail ---
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
# Use 'gmail.send' scope, which is sufficient for sending.
# If your existing token used 'gmail.modify', that will also work.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
# Use a separate token file if you want to isolate auth for this script
# Or use the same 'gmail_token.json' as your main app
TOKEN_PATH = 'sender_token.json' # Or 'gmail_token.json'
# Assumes credentials.json is in the same directory as this script
CREDENTIALS_PATH = '/Users/srinathmurali/Desktop/email_cleanup/backend/credentials.json'
# Port for the *local* server during the OAuth flow (only used for first auth)
AUTH_PORT = 8888 # Use a different port than your main app if running simultaneously

# --- Fixed Email Content ---
EMAIL_SUBJECT_TEMPLATE = "Update on Your Recent Application (Mock #{})"
EMAIL_BODY_TEMPLATE = """Dear Applicant,

Thank you for your interest and for applying. This is mock email #{}.

After careful consideration, we have decided to move forward with other candidates whose qualifications more closely match the requirements of this particular role at this time.

This was a difficult decision due to the high caliber of applicants. We appreciate you taking the time to apply and encourage you to keep an eye on future openings.

We wish you the best in your job search.

Sincerely,
The Mock Hiring Team
"""

# --- Gmail Authentication Function (Similar to previous) ---
def get_gmail_service():
    """Authenticates with Gmail API for sending and returns the service object."""
    creds = None
    print(f"--- Starting Gmail Authentication for Sender ---")
    if os.path.exists(TOKEN_PATH):
        print(f"Loading sender credentials from: {TOKEN_PATH}")
        try:
            # Pass correct scopes here
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as e:
            print(f"Error loading {TOKEN_PATH}: {e}. Will re-authenticate.")
            creds = None

    if not creds or not creds.valid:
        print("Sender credentials not found, invalid, or expired.")
        if creds and creds.expired and creds.refresh_token:
            print("Attempting to refresh sender token...")
            try:
                creds.refresh(Request())
                print("Sender token refreshed successfully.")
                try:
                    with open(TOKEN_PATH, 'w') as token: token.write(creds.to_json())
                    print(f"Refreshed sender token saved to {TOKEN_PATH}")
                except Exception as e: print(f"Error saving refreshed sender token: {e}")
            except Exception as e:
                print(f"Error refreshing sender token: {e}. Need to re-authenticate.")
                creds = None
                if os.path.exists(TOKEN_PATH):
                     try: os.remove(TOKEN_PATH); print(f"Removed invalid sender token file: {TOKEN_PATH}")
                     except OSError as oe: print(f"Error removing sender token file {TOKEN_PATH}: {oe}")

        if not creds:
            print("Starting new Gmail authentication flow for sender...")
            if not os.path.exists(CREDENTIALS_PATH):
                print(f"CRITICAL ERROR: Credentials file '{CREDENTIALS_PATH}' not found."); return None
            try:
                # Pass correct scopes here
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                print("-" * 60 + "\nStarting local server for Sender Auth. Follow browser instructions.\n" + "-" * 60)
                creds = flow.run_local_server(port=AUTH_PORT, open_browser=False)
                print("--- Sender run_local_server process completed ---")
            except Exception as e: print(f"!!! Error during sender authentication flow !!!"); traceback.print_exc(); return None

            if creds:
                print("Sender authentication successful, saving credentials...")
                try:
                    with open(TOKEN_PATH, 'w') as token: token.write(creds.to_json())
                    print(f"Credentials saved to {TOKEN_PATH}")
                except Exception as e: print(f"Error saving token: {e}")
            else: print("Sender authentication flow did not result in valid credentials."); return None

    print("Attempting to build Gmail service for sender...")
    try:
        if creds and creds.valid:
            service = build('gmail', 'v1', credentials=creds)
            print("Gmail service (sender) created successfully.")
            return service
        else: print("Authentication failed or credentials invalid, cannot create Gmail service."); return None
    except Exception as e: print(f'An unexpected error occurred building the Gmail service:'); traceback.print_exc(); return None

# --- Function to Create and Encode Email ---
def create_message(sender, to, subject, message_text):
    """Creates an EmailMessage object and encodes it for the Gmail API."""
    message = EmailMessage()
    message.set_content(message_text)
    message['To'] = to
    message['From'] = sender # Usually 'me' for authenticated user
    message['Subject'] = subject

    # Encode message to bytes, then base64url encode
    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode('ascii')
    return {'raw': encoded_message}

# --- Function to Send Email ---
def send_message(service, user_id, message):
    """Sends the prepared message using the Gmail API."""
    try:
        sent_message = service.users().messages().send(userId=user_id, body=message).execute()
        print(f"  Message sent successfully. ID: {sent_message['id']}")
        return sent_message
    except HttpError as error:
        print(f"  An error occurred sending message: {error}")
        return None
    except Exception as e:
        print(f"  An unexpected error occurred sending message:")
        traceback.print_exc()
        return None

# --- Main Script Logic ---
def main():
    print("--- Mock Rejection Email Sender ---")

    # 1. Authenticate
    service = get_gmail_service()
    if not service:
        print("\nExiting: Could not authenticate with Gmail.")
        return

    # 2. Get User Input
    while True:
        recipient_email ="smk2069@gmail.com" #input("Enter the recipient email address: ").strip()
        if '@' in recipient_email and '.' in recipient_email: # Basic validation
            break
        else:
            print("Invalid email format. Please try again.")

    while True:
        try:
            num_emails_str = "5" #input(f"How many mock rejection emails to send to {recipient_email}? ")
            num_emails = int(num_emails_str)
            if num_emails > 0:
                break
            else:
                print("Please enter a number greater than 0.")
        except ValueError:
            print("Invalid input. Please enter a whole number.")

    print(f"\nPreparing to send {num_emails} email(s) to {recipient_email}...")
    confirmation = input("Are you sure you want to proceed? (y/n): ").lower().strip()

    if confirmation != 'y':
        print("Operation cancelled.")
        return

    # 3. Send Emails in a Loop
    send_count = 0
    fail_count = 0
    for i in range(num_emails):
        print(f"\nSending email {i+1} of {num_emails}...")
        subject = EMAIL_SUBJECT_TEMPLATE.format(i+1)
        body = EMAIL_BODY_TEMPLATE.format(i+1)

        # Create the message body for the API
        message_body = create_message('me', recipient_email, subject, body)

        # Send the message
        result = send_message(service, 'me', message_body)

        if result:
            send_count += 1
        else:
            fail_count += 1

        # Add a small delay to avoid hitting sending limits too quickly
        if i < num_emails - 1: # Don't sleep after the last one
            time.sleep(1.5) # Sleep for 1.5 seconds

    # 4. Print Summary
    print("\n--- Sending Complete ---")
    print(f"Successfully sent: {send_count}")
    print(f"Failed to send:   {fail_count}")

# --- Run Main Function ---
if __name__ == "__main__":
    main()


import traceback
from googleapiclient.errors import HttpError



def delete_email_tool(gmail_service, message_id: str) -> dict:
    """
    Deletes the specified email message by moving it to the Trash in Gmail.
    Use this ONLY after confirming an email IS a job rejection.
    Requires the authenticated Gmail service object to be provided.

    Args:
        gmail_service: The authenticated Google API client service instance for Gmail.
        message_id (str): The unique ID of the Gmail message to be deleted.

    Returns:
        dict: A dictionary indicating the status ('success' or 'error')
              and an optional 'message'.
    """
    print(f"--- Tool: delete_email_tool executing for message_id: {message_id} ---")
    if not gmail_service:
        print("  [Tool Error] Gmail service object was not provided.")
        # This shouldn't happen if called correctly via partial
        return {"status": "error", "message": "Internal error: Gmail service not available to tool."}
    if not message_id:
        print("  [Tool Error] No message_id provided.")
        return {"status": "error", "message": "Missing message_id argument."}

    try:
        gmail_service.users().messages().trash(userId='me', id=message_id).execute()
        print(f"  [Tool Success] Moved message {message_id} to Trash via Gmail API.")
        return {"status": "success", "message": f"Email {message_id} moved to Trash."}
    except HttpError as error:
        if error.resp.status == 404:
             print(f"  [Tool Error] Failed to move message {message_id}: 404 Not Found (Invalid ID?).")
             return {"status": "error", "message": f"API Error deleting message {message_id}: 404 Not Found (Invalid ID?)."}
        else:
            print(f"  [Tool Error] Failed to move message {message_id}: {error}")
            return {"status": "error", "message": f"API Error deleting message {message_id}: {error}"}
    except Exception as e:
        print(f"  [Tool Error] Unexpected error moving message {message_id}:")
        traceback.print_exc()
        return {"status": "error", "message": f"Unexpected error deleting message {message_id}: {e}"}

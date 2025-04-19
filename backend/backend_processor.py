# backend/backend_processor.py
import asyncio
import traceback
import functools
import os # Make sure os is imported

# Import backend components (relative imports might work if run from root,
# but explicit sys.path modification might be needed if run differently)
# Assuming this script is run in a context where 'backend' is importable
# or adjusting sys.path if needed. For simplicity, let's assume direct imports work.
try:
    import config
    import gmail_utils
    import adk_tools
    import agent_config
except ImportError:
    # If running flet_app.py from root, Python might not find backend modules directly.
    # Add backend directory to path if needed (less clean, but works)
    import sys
    backend_dir = os.path.dirname(__file__)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    import config
    import gmail_utils
    import adk_tools
    import agent_config


# Import ADK components
from google.adk.agents import Agent
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as adk_types
from googleapiclient.errors import HttpError

# --- Global variable for Gmail service ---
_gmail_service = None

# --- Function to run the analysis for a single email ---
async def _analyze_single_email(runner, session_service, email_details: dict, log_callback):
    """Analyzes a single email using ADK and calls log_callback with updates."""
    if not email_details or 'id' not in email_details:
        log_callback(f"  [Error] Invalid email details received.")
        return

    message_id = email_details['id']
    subject = email_details.get('subject', 'No Subject')
    body = email_details.get('body', '')[:config.MAX_BODY_CHARS_FOR_PROMPT] # Truncate

    log_callback(f"\n>>> Analyzing Email ID: {message_id}")
    log_callback(f"    Subject: {subject[:100]}...")

    session_id = f"analyze_{message_id}"
    session = session_service.create_session(
        app_name=config.APP_NAME, user_id=config.USER_ID, session_id=session_id
    )

    prompt_text = f"""Analyze the following email content.
Message ID: {message_id}
Subject: {subject}

Body:
{body}
"""
    content = adk_types.Content(role='user', parts=[adk_types.Part(text=prompt_text)])

    final_response_text = "Agent analysis did not complete or produce a response."
    try:
        async for event in runner.run_async(user_id=config.USER_ID, session_id=session_id, new_message=content):
            if event.is_final_response() and event.content and event.content.parts:
                final_response_text = event.content.parts[0].text
                break
        log_callback(f"<<< Agent Final Thought: {final_response_text}")

    except Exception as e:
        log_callback(f"  [Error] Exception during ADK runner execution for {message_id}:")
        log_callback(traceback.format_exc()) # Log full traceback
    finally:
        try:
            session_service.delete_session(
                app_name=config.APP_NAME, user_id=config.USER_ID, session_id=session_id
            )
        except Exception as del_e:
             log_callback(f"  [Warning] Error deleting session {session_id}: {del_e}")

# --- Main Processing Function (Callable from Flet) ---
async def process_rejection_emails(log_callback):
    """
    Authenticates, fetches emails, runs ADK analysis, and uses log_callback for UI updates.
    Returns summary message.
    """
    global _gmail_service
    processed_count = 0
    deleted_count = 0 # We need the tool to report back if deletion happened

    log_callback("--- Starting Email Rejection Processor ---")

    # 1. Authenticate with Gmail
    if not _gmail_service: # Authenticate only if needed
        log_callback("Attempting Gmail authentication...")
        _gmail_service = gmail_utils.get_gmail_service() # This uses paths from config.py
        if not _gmail_service:
            log_callback("ERROR: Failed to initialize Gmail service.")
            # Check if token path exists, maybe prompt user to delete it if auth keeps failing
            if os.path.exists(config.GMAIL_TOKEN_PATH):
                 log_callback(f"  Hint: Try deleting '{config.GMAIL_TOKEN_PATH}' and restarting if authentication fails repeatedly.")
            return "Error: Gmail authentication failed."
        log_callback("Gmail authentication successful.")
    else:
        log_callback("Using existing Gmail authentication.")


    # 2. Verify API Key (Basic Check)
    if not config.GOOGLE_API_KEY or config.GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE":
         log_callback("CRITICAL ERROR: GOOGLE_API_KEY not set correctly in config.py or environment.")
         return "Error: Gemini API Key not configured."
    log_callback("API key seems configured.")

    # 3. Prepare ADK Tool with current Gmail service
    def delete_email_wrapper(message_id: str) -> dict:
        """Deletes the specified email message by moving it to the Trash in Gmail. Use this ONLY after confirming an email IS a job rejection.

        Args:
            message_id (str): The unique ID of the Gmail message to be deleted.

        Returns:
            dict: A dictionary indicating the status ('success' or 'error') and an optional 'message'.
        """
        log_callback(f"--- Wrapper: Attempting delete_email_tool for message_id: {message_id} ---")
        result = adk_tools.delete_email_tool(_gmail_service, message_id)
        log_callback(f"  [Tool Result] Status: {result.get('status')}, Msg: {result.get('message')}")
        return result

    prepared_tools = [delete_email_wrapper]

    # 4. Create ADK Agent Instance
    log_callback("Creating ADK Agent...")
    try:
        # Ensure LiteLLM wrapper is used if ADK_MODEL_STRING needs it

        # Or if using a direct model name compatible with Agent's default:
        # agent_model = config.ADK_MODEL_STRING # e.g., "gemini-1.5-flash-latest"

        rejection_agent = Agent(
            name=agent_config.AGENT_NAME,
            model = "gemini-2.0-flash",
            description=agent_config.AGENT_DESCRIPTION,
            instruction=agent_config.AGENT_INSTRUCTION,
            tools=prepared_tools, # Provide the wrapper tool function
        )
        log_callback(f"Agent '{rejection_agent.name}' created.")
    except Exception as agent_e:
        log_callback(f"!!! Error Creating ADK Agent: {agent_e}")
        log_callback(traceback.format_exc())
        return "Error: Failed to create ADK Agent."

    # 5. Set up ADK Runner and Session Service
    session_service = InMemorySessionService()
    runner = Runner(
        agent=rejection_agent,
        app_name=config.APP_NAME,
        session_service=session_service,
    )
    log_callback("ADK Runner and Session Service initialized.")

    # 6. Fetch Emails from Gmail
    log_callback("Fetching Emails from Gmail...")
    # Make sure the search query in config.py or here is what you want
    search_query = 'in:inbox label:inbox is:unread category:primary' # Example
    log_callback(f"Using Gmail search query: '{search_query}' (Limit: {config.MAX_EMAILS_PER_RUN})")
    emails_to_analyze = []
    try:
        results = _gmail_service.users().messages().list(
            userId='me', q=search_query, maxResults=config.MAX_EMAILS_PER_RUN
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            log_callback("No new messages found matching the query.")
        else:
            log_callback(f"Found {len(messages)} emails. Fetching details...")
            for message_info in messages:
                await asyncio.sleep(0.1) # Small delay
                msg_id = message_info['id']
                details = gmail_utils.get_email_details(_gmail_service, msg_id)
                if details:
                    emails_to_analyze.append(details)
                else:
                    log_callback(f"  Skipping message {msg_id} due to fetch error.")
            log_callback(f"Fetched details for {len(emails_to_analyze)} emails.")

    except HttpError as error:
        log_callback(f"ERROR during Gmail search: {error}")
        log_callback(traceback.format_exc())
    except Exception as e:
        log_callback(f"ERROR during Gmail search:")
        log_callback(traceback.format_exc())

    # 7. Process Emails with ADK Agent
    if emails_to_analyze:
        log_callback(f"--- Analyzing {len(emails_to_analyze)} Emails with ADK Agent ---")
        processed_count = len(emails_to_analyze)
        for email in emails_to_analyze:
            await _analyze_single_email(runner, session_service, email, log_callback)
            await asyncio.sleep(1) # Delay between emails
    else:
        log_callback("No emails fetched to analyze.")

    summary = f"Processing complete. Analyzed: {processed_count} emails."
    log_callback(f"\n--- Finished ---\n{summary}")
    return summary
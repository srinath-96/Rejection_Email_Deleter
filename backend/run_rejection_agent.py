# run_rejection_agent.py
import asyncio
import traceback
import functools

# Import configurations and utilities
import config
import gmail_utils
import adk_tools
import agent_config

# Import ADK components
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types as adk_types
from googleapiclient.errors import HttpError

# --- analyze_email_with_adk function remains the same ---
async def analyze_email_with_adk(runner, session_service, email_details: dict):
    # ... (keep existing code for this function) ...
    if not email_details or 'id' not in email_details or 'subject' not in email_details or 'body' not in email_details:
        print("  [Error] Invalid email details passed to analyze_email_with_adk.")
        return

    message_id = email_details['id']
    subject = email_details['subject']
    body = email_details['body'][:config.MAX_BODY_CHARS_FOR_PROMPT]

    print(f"\n>>> Analyzing Email ID: {message_id} with ADK Agent")
    print(f"    Subject: {subject[:100]}...")

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
        print(f"<<< Agent Final Thought: {final_response_text}")
    except Exception as e:
        print(f"  [Error] Exception during ADK runner execution for {message_id}:")
        traceback.print_exc()
    finally:
        try:
            session_service.delete_session(
                app_name=config.APP_NAME, user_id=config.USER_ID, session_id=session_id
            )
        except Exception as del_e:
             print(f"  [Warning] Error deleting session {session_id}: {del_e}")


# --- Main Execution Logic ---
async def main():
    """Main async function to set up and run the agent process."""
    print("--- Starting Email Rejection Processor (Modular ADK Version) ---")

    # 1. Authenticate with Gmail (gets service object)
    gmail_service = gmail_utils.get_gmail_service()
    if not gmail_service:
        print("Exiting: Failed to initialize Gmail service.")
        return

    # 2. Verify API Key Configuration
    if config.GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY_HERE":
         print("CRITICAL ERROR: GOOGLE_API_KEY not set correctly in config.py or environment.")
         return
    print("API key seems configured.")

    # 3. Prepare ADK Tool(s)
    # ***********************************************************************
    # *** CHANGE HERE: Define wrapper with signature ADK can parse ***
    # ***********************************************************************

    # Define a wrapper function that ONLY takes arguments the LLM needs to provide.
    # The gmail_service is accessed via the closure.
    # Copy the DOCSTRING manually for ADK.
    def delete_email_wrapper(message_id: str) -> dict:
        # Manually copy the essential part of the docstring for the LLM
        """Deletes the specified email message by moving it to the Trash in Gmail. Use this ONLY after confirming an email IS a job rejection.

        Args:
            message_id (str): The unique ID of the Gmail message to be deleted.

        Returns:
            dict: A dictionary indicating the status ('success' or 'error') and an optional 'message'.
        """
        # The 'gmail_service' used here is the one from the outer scope of main()
        print(f"--- Wrapper: delete_email_wrapper called for message_id: {message_id} ---") # Add print here
        return adk_tools.delete_email_tool(gmail_service, message_id)

    # We don't need @functools.wraps anymore because we define the signature
    # directly as ADK needs it (only message_id).
    # We manually ensure the docstring is present.
    prepared_tools = [delete_email_wrapper]
    # ***********************************************************************
    # *** End of Change ***
    # ***********************************************************************

    # 4. Create the ADK Agent Instance
    print("\n--- Creating ADK Agent ---")
    try:
        rejection_agent = Agent(
            name=agent_config.AGENT_NAME,
            model = "gemini-2.0-flash",
            description=agent_config.AGENT_DESCRIPTION,
            instruction=agent_config.AGENT_INSTRUCTION,
            tools=prepared_tools, # Provide the wrapper tool function
        )
        print(f"Agent '{rejection_agent.name}' created successfully.")
    except Exception as agent_e:
        print(f"!!! Error Creating ADK Agent: {agent_e}")
        traceback.print_exc()
        return

    # 5. Set up ADK Runner and Session Service (remains the same)
    session_service = InMemorySessionService()
    runner = Runner(
        agent=rejection_agent,
        app_name=config.APP_NAME,
        session_service=session_service,
    )
    print("ADK Runner and Session Service initialized.")

    # 6. Fetch Emails from Gmail (remains the same)
    print("\n--- Fetching Emails from Gmail ---")
    search_query = 'in:inbox label:inbox is:unread category:primary'
    print(f"Using Gmail search query: '{search_query}' (Limit: {config.MAX_EMAILS_PER_RUN})")
    emails_to_analyze = []
    try:
        results = gmail_service.users().messages().list(
            userId='me', q=search_query, maxResults=config.MAX_EMAILS_PER_RUN
        ).execute()
        messages = results.get('messages', [])

        if not messages:
            print("No messages found matching the query.")
        else:
            print(f"Found {len(messages)} emails. Fetching details...")
            for message_info in messages:
                msg_id = message_info['id']
                details = gmail_utils.get_email_details(gmail_service, msg_id)
                if details:
                    emails_to_analyze.append(details)
                else:
                    print(f"  Skipping message {msg_id} due to fetch error.")
    except HttpError as error:
        print(f"\nAn error occurred during Gmail search: {error}")
    except Exception as e:
        print(f"\nAn unexpected error occurred during Gmail search:")
        traceback.print_exc()

    # 7. Process Emails with ADK Agent (remains the same logic)
    if emails_to_analyze:
        print(f"\n--- Analyzing {len(emails_to_analyze)} Emails with ADK Agent ---")
        for email in emails_to_analyze:
            await analyze_email_with_adk(runner, session_service, email)
            await asyncio.sleep(1) # Keep delay for safety
    else:
        print("\nNo emails fetched to analyze.")

    print("\n--- Script Finished ---")

# --- Run the main async function (remains the same) ---
if __name__ == "__main__":
    asyncio.run(main())
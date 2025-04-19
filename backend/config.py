# backend/config.py
import os
from dotenv import load_dotenv
load_dotenv()

# --- Gmail API Settings ---
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.modify']
# GMAIL_TOKEN_PATH assumes it will be created in the 'backend' folder
GMAIL_TOKEN_PATH = 'gmail_token.json'
# *** USE ABSOLUTE PATH or ensure relative path works from execution context ***
# Absolute path is usually safest when run via external tools like Flet
GMAIL_CREDENTIALS_PATH = '/Users/srinathmurali/Desktop/email_cleanup/backend/credentials.json' # <-- Verify this absolute path
# GMAIL_CREDENTIALS_PATH = 'credentials.json' # <-- Alternative if running script FROM backend folder

GMAIL_AUTH_PORT = 8888 # Port for Gmail OAuth flow callback

# --- ADK / LiteLLM Settings ---
# Use environment variable for API key
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Ensure ADK uses direct GenAI keys if GOOGLE_API_KEY is set
if GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
    print("Attempting to use GOOGLE_API_KEY from environment.")
else:
    print("WARNING: GOOGLE_API_KEY environment variable not found.")
    print("         Please set it for the agent to function.")

# Define the model ADK will use via LiteLLM prefix format
ADK_MODEL_STRING = "gemini/gemini-1.5-flash-latest" # Use LiteLLM format

# --- Application Settings ---
APP_NAME = "email_rejection_agent_app"
USER_ID = "user_main"
MAX_EMAILS_PER_RUN = 15 # Limit per run
MAX_BODY_CHARS_FOR_PROMPT = 5000

print("Configuration loaded.")
if not GOOGLE_API_KEY:
    print("!!! Reminder: Set the GOOGLE_API_KEY environment variable !!!")
# Rejection_Email_Deleter

A desktop application built with Python, Flet, and Google ADK that automatically identifies job rejection emails in your Gmail inbox using AI (Gemini) and moves them to the Trash.

<img width="800" alt="image" src="https://github.com/user-attachments/assets/8eecf255-f43f-463a-a032-142a2b8a2734" />


## Features

*   Connects securely to your Gmail account using OAuth 2.0.
*   Fetches recent unread emails from your primary inbox category.
*   Utilizes Google's Agent Development Kit (ADK) and a Gemini language model (via LiteLLM) to analyze email content.
*   Identifies emails likely to be job application rejections based on content analysis.
*   Automatically moves identified rejection emails to the Gmail Trash folder using the Gmail API.
*   Provides a simple desktop Graphical User Interface (GUI) built with Flet.
*   Displays real-time status and logs during the cleaning process.
*   Includes a separate utility script (`send_mock_rejections.py`) to send test emails for development purposes.

## Technology Stack

*   **Backend & Frontend:** Python 3.10+
*   **GUI Framework:** [Flet](https://flet.dev/)
*   **Agent Framework:** [Google Agent Development Kit (ADK)](https://github.com/google/agent-development-kit)
*   **LLM Interface:** [LiteLLM](https://github.com/BerriAI/litellm) (used by ADK)
*   **AI Model:** Google Gemini (e.g., `gemini-1.5-flash-latest` via Google AI Studio API)
*   **Google Services:**
    *   Gmail API
    *   Google Cloud Platform (for OAuth Credentials)
    *   Google AI Studio (for Gemini API Key)
*   **Authentication:** Google OAuth 2.0 Client Library for Python
*   **API Interaction:** Google API Client Library for Python

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/srinath-96/Rejection_Email_Deleter
    cd Rejection_Email_Deleter
    ```

2.  **Create and Activate Virtual Environment:**
    (Make sure you have Python 3.10+ installed)
    ```bash
    # Create venv (macOS/Linux)
    python3 -m venv .venv
    # Activate venv (macOS/Linux)
    source .venv/bin/activate

    # Create venv (Windows)
    python -m venv .venv
    # Activate venv (Windows CMD)
    .\.venv\Scripts\activate
    # Activate venv (Windows PowerShell)
    .\.venv\Scripts\Activate.ps1
    ```

3.  **Install Dependencies:**
    ```bash
    pip install --upgrade pip
    pip install flet google-adk litellm google-api-python-client google-auth-httplib2 google-auth-oauthlib python-dotenv
    ```
    *(Alternatively, create a `requirements.txt` file and use `pip install -r requirements.txt`)*

4.  **Google Cloud Setup (Gmail API Credentials):**
    *   Go to the [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a new project or select an existing one.
    *   Enable the **Gmail API**.
    *   Go to "APIs & Services" -> "Credentials".
    *   Click "+ CREATE CREDENTIALS" -> "OAuth client ID".
    *   Select "Desktop app" as the Application type. Give it a name (e.g., "Flet Email Cleaner").
    *   Click "Create".
    *   Click "DOWNLOAD JSON" on the credential that was just created.
    *   **Rename the downloaded file to `credentials.json`**.
    *   **Place this `credentials.json` file inside the `backend/` directory** of your project.
    *   Go to "APIs & Services" -> "OAuth consent screen".
        *   Set User Type to "External".
        *   Fill in the required app name, user support email, and developer contact info.
        *   **Scopes:** You don't strictly need to add scopes here, as the script requests them, but ensure the consent screen is configured.
        *   **Test Users:** Add the Google Account email address (whose Gmail you want to clean) to the list of Test Users while the app is in "Testing" status.

5.  **Google AI Studio Setup (Gemini API Key):**
    *   Go to [Google AI Studio](https://aistudio.google.com/).
    *   Click "Get API key" -> "Create API key".
    *   Copy the generated API key.

6.  **Configure API Keys:**
    *   **Gemini API Key (Required):** The recommended way is to set an environment variable named `GOOGLE_API_KEY`.
        *   macOS/Linux: `export GOOGLE_API_KEY='YOUR_COPIED_API_KEY'`
        *   Windows CMD: `set GOOGLE_API_KEY=YOUR_COPIED_API_KEY`
        *   Windows PowerShell: `$env:GOOGLE_API_KEY='YOUR_COPIED_API_KEY'`
        *(Alternatively, you can paste the key directly into `backend/config.py`, replacing the `os.getenv(...)` fallback, but this is less secure).*
    *   **Gmail Credentials:** Ensure `backend/credentials.json` exists and the path in `backend/config.py` (`GMAIL_CREDENTIALS_PATH`) points to it correctly (absolute path recommended).

## Usage

1.  **Activate Virtual Environment:**
    ```bash
    # (If not already active)
    source .venv/bin/activate # macOS/Linux
    # .\.venv\Scripts\activate # Windows CMD
    ```

2.  **Set Environment Variable (if not done globally):**
    ```bash
    export GOOGLE_API_KEY='YOUR_COPIED_API_KEY' # macOS/Linux
    ```

3.  **Run the Flet Application:**
    ```bash
    python flet_app.py
    ```

4.  **First Run - Gmail Authentication:**
    *   The first time you run the app (or after deleting `backend/gmail_token.json`), the log area will display a Google authorization URL.
    *   Copy this URL and paste it into your web browser.
    *   Log in to the Google Account whose Gmail you want the app to access.
    *   Grant the requested permissions (it will ask for permission to view and manage your mail based on the `gmail.modify` scope).
    *   You can ignore the "This site can’t be reached" error in the browser after granting permission.
    *   The app should detect the successful authentication and save a `gmail_token.json` file in the `backend/` directory.

5.  **Clean Emails:**
    *   Click the "Clean Rejection Emails" button.
    *   The application will fetch recent unread emails, send them to the ADK agent (using Gemini) for analysis, and attempt to move identified rejections to the Trash.
    *   Monitor the "Status / Log" area for progress and results.

6.  **Subsequent Runs:** The app should automatically use the `gmail_token.json` file to refresh access without requiring browser authentication, unless the token becomes invalid or access is revoked.

## Backend Details

The core logic resides in the `backend/` directory:

*   `config.py`: Stores configuration like API paths, scopes, model names, etc.
*   `gmail_utils.py`: Handles Gmail API authentication and email fetching.
*   `adk_tools.py`: Defines the `delete_email_tool` function callable by the ADK agent.
*   `agent_config.py`: Contains the name, description, and detailed instructions for the ADK agent.
*   `backend_processor.py`: Orchestrates the backend process (auth, fetch, agent invocation) and provides progress updates via a callback to the Flet app.

## Utility Script: Send Mock Rejections

The `backend/send_mock_rejections.py` script can be used to send simple test emails to your account.

1.  **Activate Venv:** `source .venv/bin/activate`
2.  **Run:** `python backend/send_mock_rejections.py`
3.  **Follow Prompts:** It will guide you through authentication (if needed, saving to `backend/sender_token.json`) and ask for the recipient email and number of emails to send.

## Future Improvements / TODO

*   Improve rejection detection accuracy (more sophisticated prompting, fine-tuning, handling edge cases).
*   Add user configuration options within the Flet UI (e.g., API keys, Gmail search query, model selection, target label instead of Trash).
*   Implement more robust error handling and retries for API calls.
*   Provide clearer feedback on *which* specific emails were deleted.
*   Explore real-time processing (e.g., using Gmail Push Notifications - more complex setup).
*   Package the application into a standalone executable using PyInstaller or Briefcase.
*   Add unit and integration tests.

## License

This project is licensed under the MIT License - see the LICENSE.md file for details.

# flet_app.py
import flet as ft
import asyncio
import threading
import traceback
import sys
import os

# --- Add backend directory to Python path ---
backend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend'))
if backend_path not in sys.path:
    print(f"Adding to sys.path: {backend_path}")
    sys.path.insert(0, backend_path)

# Now import the backend processing function
try:
    from backend.backend_processor import process_rejection_emails
except ImportError as e:
    print(f"ERROR: Could not import backend_processor. Ensure it exists in '{backend_path}' and dependencies are installed.")
    print(f"ImportError: {e}")
    async def process_rejection_emails(log_callback):
        log_callback("FATAL ERROR: Backend processor could not be loaded.")
        log_callback("Check terminal for import errors.")
        await asyncio.sleep(0)
        return "Backend Error"

# --- Flet UI Main Function ---
def main(page: ft.Page):
    page.title = "Email Rejection Cleaner"
    page.vertical_alignment = ft.MainAxisAlignment.START
    page.window_width = 750
    page.window_height = 700
    page.padding = 20

    # --- UI Controls ---
    log_output = ft.TextField(
        value="Welcome! Activate venv and click button to start.\nMake sure GOOGLE_API_KEY environment variable is set.",
        read_only=True,
        multiline=True,
        expand=True,
        border_color=ft.colors.OUTLINE,
        border_radius=ft.border_radius.all(5),
        min_lines=15,
        text_size=12,
    )

    clean_button = ft.ElevatedButton(
        "Clean Rejection Emails",
        icon=ft.icons.DELETE_SWEEP_OUTLINED,
        bgcolor=ft.colors.RED_ACCENT_700,
        color=ft.colors.WHITE,
        height=50,
        tooltip="Starts the process to find and delete rejection emails"
    )
    progress_ring = ft.ProgressRing(visible=False, width=24, height=24, stroke_width=3)
    status_text = ft.Text("Ready", italic=True, size=11, color=ft.colors.SECONDARY)

    # --- State ---
    is_running = False

    # --- Functions ---
    def update_log(message: str):
        """Appends a message to the log view safely from any thread."""
        msg_str = str(message).strip()
        if not msg_str:
            return

        # Flet automatically handles thread safety for control updates
        current_value = log_output.value if log_output.value else ""
        log_output.value = current_value + "\n" + msg_str

        try:
            page.update() # Request UI update
        except Exception as e:
            print(f"Error updating page (likely closing): {e}")


    async def run_backend_task_async():
        """The async task that calls the backend processor."""
        nonlocal is_running
        try:
            update_log("Backend task started...")
            summary = await process_rejection_emails(update_log)
            # Summary is already logged by the processor
            # update_log(f"Backend task finished: {summary}") # Optional redundant log
        except Exception as e:
            update_log(f"--- FATAL ERROR in backend task ---")
            update_log(traceback.format_exc())
        finally:
            is_running = False
            # Directly update UI controls from the background thread.
            # Flet marshals these updates to the UI thread automatically.
            clean_button.disabled = False
            progress_ring.visible = False
            status_text.value = "Finished."
            # *** REMOVED page.run_thread_safe ***
            page.update() # Request final UI update

    def run_backend_in_thread():
        """Runs the async backend task in a separate thread."""
        update_log("Starting backend thread...")
        thread = threading.Thread(target=asyncio.run, args=(run_backend_task_async(),))
        thread.daemon = True
        thread.start()

    def clean_button_click(e):
        """Handles the button click event."""
        nonlocal is_running
        if is_running:
            print("Task already running.")
            return

        is_running = True
        log_output.value = ">>> Starting process..."
        clean_button.disabled = True
        progress_ring.visible = True
        status_text.value = "Running..."
        page.update()

        run_backend_in_thread()


    # --- Button Action ---
    clean_button.on_click = clean_button_click

    # --- Layout ---
    page.add(
        ft.Row(
            [clean_button, progress_ring, status_text],
            alignment=ft.MainAxisAlignment.START,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15
        ),
        ft.Text("Status / Log:", weight=ft.FontWeight.BOLD, size=14),
        ft.Container(
            content=log_output,
            expand=True,
            padding=ft.padding.only(top=5)
        )
    )
    page.update()


# --- Run the Flet App ---
if __name__ == "__main__":
    print("Starting Flet application...")
    # ... (rest of the startup messages) ...
    ft.app(target=main)
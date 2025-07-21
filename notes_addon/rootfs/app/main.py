import os
from flask import Flask, render_template, request, redirect, url_for
import logging

# --- NEW CUSTOM WSGI MIDDLEWARE ---
class ReverseProxied:
    """
    WSGI middleware to correctly set SCRIPT_NAME and APPLICATION_ROOT
    when running behind Home Assistant's Ingress.
    It reads the 'X-Ingress-Path' header provided by Home Assistant.
    """
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)

    def __call__(self, environ, start_response):
        self.logger.info("DEBUG - Inside ReverseProxied middleware: START")

        # --- EXHAUSTIVE ENVIRON LOGGING ---
        self.logger.info("DEBUG - Dumping relevant environ keys:")
        # Log ALL keys in environ, not just HTTP_ and specific ones, to be absolutely sure
        for key, value in environ.items():
            self.logger.info(f"DEBUG - Environ: {key} = '{value}'")
        # --- END EXHAUSTIVE ENVIRON LOGGING ---

        # Attempt to get the ingress path from environment
        # Try common variations for the header name within the WSGI environ
        script_name = environ.get('HTTP_X_INGRESS_PATH', '')
        if not script_name: # Fallback if not found under standard WSGI header name
            script_name = environ.get('X_INGRESS_PATH', '') # Some servers might pass it without HTTP_ prefix or with underscores
        if not script_name: # Final fallback for raw header name, though unlikely for WSGI environ
             script_name = environ.get('X-Ingress-Path', '')

        self.logger.info(f"DEBUG - Middleware detected script_name (attempted from environ): '{script_name}'")

        if script_name:
            environ['SCRIPT_NAME'] = script_name
            # Correct PATH_INFO if it starts with the script_name
            path_info = environ.get('PATH_INFO', '')
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
            # Flask uses APPLICATION_ROOT internally for url_for
            environ['APPLICATION_ROOT'] = script_name
            self.logger.info(f"DEBUG - Middleware SET SCRIPT_NAME to: '{environ['SCRIPT_NAME']}'")
        else:
            self.logger.warning("DEBUG - Middleware: HTTP_X_INGRESS_PATH (or alternatives) not found or empty in environ.")

        self.logger.info("DEBUG - Inside ReverseProxied middleware: END")
        return self.app(environ, start_response)
# --- END NEW CUSTOM WSGI MIDDLEWARE ---


# Get the absolute path to the directory containing main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'static'),    # Explicit absolute path
            template_folder=os.path.join(BASE_DIR, 'templates')) # Explicit absolute path

# APPLY THE CUSTOM MIDDLEWARE
app.wsgi_app = ReverseProxied(app.wsgi_app)

# Configure logging to stdout, which Docker captures.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
app.logger.setLevel(logging.INFO)

# --- DEBUGGING LOGS (Keep these to see Flask's final state) ---
@app.before_request
def log_request_info_after_middleware():
    app.logger.info(f"DEBUG - Full Request URL (Flask's view): {request.url}")
    app.logger.info(f"DEBUG - Request Path (Flask's view): {request.path}")
    app.logger.info(f"DEBUG - Script Root (Flask's view after middleware): {request.script_root}")
    app.logger.info(f"DEBUG - Base URL (Flask's view): {request.base_url}")
    if 'X-Ingress-Path' in request.headers:
        app.logger.info(f"DEBUG - X-Ingress-Path Header (Flask's view - direct header access): {request.headers['X-Ingress-Path']}")
    else:
        app.logger.info("DEBUG - X-Ingress-Path Header (Flask's view - direct header access): NOT FOUND (in request.headers)")
    # This will log all HTTP_ headers that Flask's request.environ can see AFTER middleware
    for key, value in request.environ.items():
        if key.startswith('HTTP_'):
            app.logger.info(f"DEBUG - request.environ header (Flask's view): {key} = '{value}'")
# --- END DEBUGGING LOGS ---


# Get notes directory from environment variable set in run.sh.
NOTES_DIR = os.environ.get('NOTES_DIR', '/config/notes')

@app.before_request # Use @app.before_request for Flask 2.3+ (replaces before_first_request)
def setup_notes_directory():
    """Ensures the notes directory exists before each request."""
    try:
        os.makedirs(NOTES_DIR, exist_ok=True)
        app.logger.info(f"Notes directory ensured at: {NOTES_DIR}")
    except OSError as e:
        app.logger.error(f"Error creating notes directory {NOTES_DIR}: {e}")

def get_all_notes():
    """Reads all .txt files from the notes directory and returns them as a list of dictionaries."""
    notes = []
    if os.path.exists(NOTES_DIR):
        for filename in sorted(os.listdir(NOTES_DIR)):
            if filename.endswith(".txt"):
                try:
                    filepath = os.path.join(NOTES_DIR, filename)
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    notes.append({'filename': filename, 'content': content})
                except Exception as e:
                    app.logger.error(f"Error reading note {filename}: {e}")
    return notes

# --- Flask Routes ---

@app.route('/')
def index():
    """Renders the main page displaying all notes."""
    notes = get_all_notes()
    return render_template('index.html', notes=notes)

@app.route('/create', methods=['GET', 'POST'])
def create_note():
    """Handles creating new notes."""
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        # Use a default title if none is provided
        filename = f"{title}.txt" if title.strip() else "untitled.txt"
        filepath = os.path.join(NOTES_DIR, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            app.logger.info(f"Note '{filename}' created.")
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error creating note '{filename}': {e}")
            return "Error creating note", 500
    # For GET requests, render the form to create a new note
    return render_template('edit_note.html', note={})

@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_note(filename):
    """Handles editing existing notes."""
    filepath = os.path.join(NOTES_DIR, filename)
    if request.method == 'POST':
        content = request.form['content']
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            app.logger.info(f"Note '{filename}' updated.")
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error updating note '{filename}': {e}")
            return "Error updating note", 500
    else:
        # For GET requests, load the note content for editing
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            note = {'filename': filename, 'content': content}
            return render_template('edit_note.html', note=note)
        except FileNotFoundError:
            app.logger.warning(f"Note '{filename}' not found for editing.")
            return "Note not found", 404
        except Exception as e:
            app.logger.error(f"Error reading note '{filename}' for editing: {e}")
            return "Error reading note", 500

@app.route('/delete/<filename>', methods=['POST'])
def delete_note(filename):
    """Handles deleting notes."""
    filepath = os.path.join(NOTES_DIR, filename)
    try:
        os.remove(filepath)
        app.logger.info(f"Note '{filename}' deleted.")
    except FileNotFoundError:
        app.logger.warning(f"Attempted to delete non-existent note '{filename}'.")
    except Exception as e:
        app.logger.error(f"Error deleting note '{filename}': {e}")
    # Redirect back to the index page after deletion
    return redirect(url_for('index'))

@app.route('/import', methods=['GET', 'POST'])
def import_note():
    """Handles importing notes via file upload."""
    if request.method == 'POST':
        if 'file' not in request.files:
            app.logger.warning("No file part in import request.")
            return "No file part", 400
        file = request.files['file']
        if file.filename == '':
            app.logger.warning("No selected file for import.")
            return "No selected file", 400
        if file:
            filename = file.filename
            filepath = os.path.join(NOTES_DIR, filename)
            try:
                file.save(filepath)
                app.logger.info(f"File '{filename}' imported successfully.")
                return redirect(url_for('index'))
            except Exception as e:
                app.logger.error(f"Error importing file '{filename}': {e}")
                return "Error importing file", 500
    # For GET requests (or if POST fails without file), redirect to index
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099)


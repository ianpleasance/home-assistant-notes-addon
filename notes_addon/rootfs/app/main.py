import os
from flask import Flask, render_template, request, redirect, url_for
import logging
from werkzeug.middleware.proxy_fix import ProxyFix

# Get the absolute path to the directory containing main.py
# This ensures Flask knows exactly where 'static' and 'templates' are relative to this file.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'static'),    # Explicit absolute path
            template_folder=os.path.join(BASE_DIR, 'templates')) # Explicit absolute path

# Apply the ProxyFix middleware for Home Assistant Ingress compatibility.
# x_prefix=1 is crucial for correctly handling the base URL when proxied by HA.
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

# Configure logging to stdout, which Docker captures.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
app.logger.setLevel(logging.INFO)

# --- DEBUGGING LOGS ---
# This function will run before every request and print valuable path information
@app.before_request
def log_ingress_path_and_request_info():
    app.logger.info(f"DEBUG - Full Request URL: {request.url}")
    app.logger.info(f"DEBUG - Request Path (after ingress prefix removal): {request.path}")
    app.logger.info(f"DEBUG - Script Root (Ingress Prefix detected by ProxyFix): {request.script_root}")
    app.logger.info(f"DEBUG - Base URL (including ingress prefix): {request.base_url}")
    if 'X-Ingress-Path' in request.headers:
        app.logger.info(f"DEBUG - X-Ingress-Path Header from HA: {request.headers['X-Ingress-Path']}")
    else:
        app.logger.info("DEBUG - X-Ingress-Path Header from HA: NOT FOUND")
# --- END DEBUGGING LOGS ---


# Get notes directory from environment variable set in run.sh.
# Defaults to '/config/notes' if the environment variable is not set.
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

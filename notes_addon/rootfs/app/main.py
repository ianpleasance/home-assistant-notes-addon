import os
import re
from flask import Flask, render_template, request, redirect, url_for, send_file
import logging
from zipfile import ZipFile
import io


# --- WSGI MIDDLEWARE ---
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
        script_name = environ.get('HTTP_X_INGRESS_PATH', '')
        if not script_name:
            script_name = environ.get('X_INGRESS_PATH', '')
        if not script_name:
            script_name = environ.get('X-Ingress-Path', '')

        if script_name:
            environ['SCRIPT_NAME'] = script_name
            path_info = environ.get('PATH_INFO', '')
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]
            environ['APPLICATION_ROOT'] = script_name

        return self.app(environ, start_response)
# --- END WSGI MIDDLEWARE ---


# Get the absolute path to the directory containing main.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__,
            static_folder=os.path.join(BASE_DIR, 'static'),
            template_folder=os.path.join(BASE_DIR, 'templates'))

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB upload limit

# APPLY THE CUSTOM MIDDLEWARE
app.wsgi_app = ReverseProxied(app.wsgi_app)

# Configure logging to stdout, which Docker captures.
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])
app.logger.setLevel(logging.INFO)


# Get notes directory from environment variable set in run.sh.
NOTES_DIR = os.environ.get('NOTES_DIR', '/config/notes')

# Ensure notes directory exists once at startup.
try:
    os.makedirs(NOTES_DIR, exist_ok=True)
    app.logger.info(f"Notes directory ensured at: {NOTES_DIR}")
except OSError as e:
    app.logger.error(f"Error creating notes directory {NOTES_DIR}: {e}")


def sanitise_filename(raw: str) -> str:
    """Derive a safe .txt filename from raw user content (first line of note)."""
    # Take first line only, strip whitespace
    name = raw.split('\n')[0].strip()
    if not name:
        name = 'untitled_note'
    # Replace anything that isn't alphanumeric, space, hyphen, or underscore
    name = re.sub(r'[^\w\s\-]', '_', name, flags=re.UNICODE)
    # Collapse multiple spaces/underscores, strip leading/trailing
    name = re.sub(r'[\s_]+', '_', name).strip('_')
    # Truncate to 100 characters
    name = name[:100]
    if not name:
        name = 'untitled_note'
    return name + '.txt'


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
                    title = content.split('\n')[0].strip() if content else filename.replace('.txt', '')
                    notes.append({'filename': filename, 'content': content, 'title': title})
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
        content = request.form['content']

        filename = sanitise_filename(content)
        filename_base = filename[:-4]  # strip .txt for counter loop

        # Ensure filename is unique
        counter = 0
        while os.path.exists(os.path.join(NOTES_DIR, filename)):
            counter += 1
            filename = f"{filename_base}_{counter}.txt"

        filepath = os.path.join(NOTES_DIR, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            app.logger.info(f"Note '{filename}' created.")
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error creating note '{filename}': {e}")
            return "Error creating note", 500

    return render_template('edit_note.html', note={'filename': '', 'content': ''})


@app.route('/edit/<filename>', methods=['GET', 'POST'])
def edit_note(filename):
    """Handles editing existing notes."""
    filename = os.path.basename(filename)
    if not filename or filename.startswith('.') or not filename.endswith('.txt'):
        return "Invalid filename", 400

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
    filename = os.path.basename(filename)
    if not filename or filename.startswith('.') or not filename.endswith('.txt'):
        return "Invalid filename", 400

    filepath = os.path.join(NOTES_DIR, filename)
    try:
        os.remove(filepath)
        app.logger.info(f"Note '{filename}' deleted.")
    except FileNotFoundError:
        app.logger.warning(f"Attempted to delete non-existent note '{filename}'.")
    except Exception as e:
        app.logger.error(f"Error deleting note '{filename}': {e}")
    return redirect(url_for('index'))


@app.route('/import', methods=['GET', 'POST'])
def import_note():
    """Handles importing notes from a .zip file."""
    if request.method == 'POST':
        if 'zip_file' not in request.files:
            app.logger.warning("No file part in import request.")
            return "No file part", 400
        file = request.files['zip_file']
        if file.filename == '':
            app.logger.warning("No selected file for import.")
            return "No selected file", 400
        if not file.filename.lower().endswith('.zip'):
            app.logger.warning(f"Rejected non-zip import: {file.filename}")
            return "Only .zip files are accepted", 400
        try:
            imported = 0
            with ZipFile(io.BytesIO(file.read())) as zf:
                for entry in zf.namelist():
                    # Zip-slip protection: reject any entry with path separators
                    entry_base = os.path.basename(entry)
                    if not entry_base or entry_base.startswith('.'):
                        continue
                    if not entry_base.endswith('.txt'):
                        continue
                    safe_name = re.sub(r'[^\w\s\-.]', '_', entry_base)
                    dest = os.path.join(NOTES_DIR, safe_name)
                    with zf.open(entry) as src, open(dest, 'wb') as dst:
                        dst.write(src.read())
                    imported += 1
            app.logger.info(f"Imported {imported} note(s) from zip.")
            return redirect(url_for('index'))
        except Exception as e:
            app.logger.error(f"Error importing zip: {e}")
            return "Error importing file", 500
    return redirect(url_for('index'))


@app.route('/export_notes')
def export_notes():
    """Exports all notes as a zip file."""
    app.logger.info("Export notes requested.")
    data = io.BytesIO()
    with ZipFile(data, 'w') as zipf:
        if os.path.exists(NOTES_DIR):
            for filename in os.listdir(NOTES_DIR):
                filepath = os.path.join(NOTES_DIR, filename)
                if os.path.isfile(filepath) and filename.endswith(".txt"):
                    try:
                        zipf.write(filepath, arcname=filename)
                    except Exception as e:
                        app.logger.error(f"Error adding {filename} to zip: {e}")
    data.seek(0)
    return send_file(data, mimetype='application/zip', as_attachment=True, download_name='all_notes.zip')


if __name__ == '__main__':
    # Dev fallback only — production uses gunicorn (see run.sh)
    app.run(host='0.0.0.0', port=8099)

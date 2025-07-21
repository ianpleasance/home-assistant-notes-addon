from flask import Flask, render_template, request, redirect, url_for, send_file, flash
import os
import uuid
import logging
import zipfile
import io
import re # For sanitizing filenames during import

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Get the notes directory from the environment variable set by run.sh
NOTES_DIR = os.environ.get('NOTES_DIR', '/data/notes_data') # Fallback if not set, though run.sh should set it

@app.before_first_request
def setup_notes_directory():
    """Ensures the notes directory exists before the first request."""
    try:
        os.makedirs(NOTES_DIR, exist_ok=True)
        app.logger.info(f"Notes directory ensured at: {NOTES_DIR}")
    except OSError as e:
        app.logger.error(f"Error creating notes directory {NOTES_DIR}: {e}")
        # In a real addon, you might want a more robust error page or shutdown
        # For now, it will likely fail later if the directory isn't writable.

@app.route('/')
def list_notes():
    """Displays a list of all notes."""
    notes = []
    try:
        for filename in os.listdir(NOTES_DIR):
            if filename.endswith(".txt"):
                filepath = os.path.join(NOTES_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        title = f.readline().strip()
                        # Use filename without extension as ID
                        note_id = os.path.splitext(filename)[0]
                        notes.append({
                            'id': note_id,
                            'title': title[:50] if title else "(No Title)"
                        })
                except Exception as e:
                    app.logger.warning(f"Could not read note file {filename}: {e}")
        # Sort notes by title for consistent display
        notes.sort(key=lambda x: x['title'].lower())
    except FileNotFoundError:
        app.logger.warning(f"Notes directory not found: {NOTES_DIR}")
    except Exception as e:
        app.logger.error(f"Error listing notes: {e}")

    return render_template('index.html', notes=notes)

@app.route('/new', methods=['GET', 'POST'])
def new_note():
    """Handles creating a new note."""
    if request.method == 'POST':
        content = request.form['content']
        if not content.strip():
            app.logger.info("Attempted to save an empty new note, redirecting.")
            return redirect(url_for('list_notes'))

        note_id = str(uuid.uuid4()) # Generate a unique ID for the filename
        filepath = os.path.join(NOTES_DIR, f"{note_id}.txt")
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            app.logger.info(f"New note '{note_id}' created.")
        except Exception as e:
            app.logger.error(f"Error creating new note '{note_id}': {e}")
            # Potentially show an error message to the user
        return redirect(url_for('list_notes'))

    # GET request: show the new note form
    return render_template('edit_note.html', note={'id': '', 'content': ''})

@app.route('/edit/<note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    """Handles editing an existing note."""
    filepath = os.path.join(NOTES_DIR, f"{note_id}.txt")

    if not os.path.exists(filepath):
        app.logger.warning(f"Note '{note_id}' not found for editing.")
        return "Note not found", 404

    if request.method == 'POST':
        content = request.form['content']
        if not content.strip():
            # If content is empty on edit, treat as a delete operation
            try:
                os.remove(filepath)
                app.logger.info(f"Note '{note_id}' deleted during empty edit save.")
            except Exception as e:
                app.logger.error(f"Error deleting note '{note_id}' (from empty edit save): {e}")
            return redirect(url_for('list_notes'))

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            app.logger.info(f"Note '{note_id}' updated.")
        except Exception as e:
            app.logger.error(f"Error updating note '{note_id}': {e}")
            # Potentially show an error message
        return redirect(url_for('list_notes'))
    else:
        # GET request: display the note content for editing
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            app.logger.error(f"Error reading note '{note_id}' for editing: {e}")
            return "Could not read note content", 500
        return render_template('edit_note.html', note={'id': note_id, 'content': content})

@app.route('/delete/<note_id>')
def delete_note(note_id):
    """Deletes a note."""
    filepath = os.path.join(NOTES_DIR, f"{note_id}.txt")
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            app.logger.info(f"Note '{note_id}' deleted.")
        except Exception as e:
            app.logger.error(f"Error deleting note '{note_id}': {e}")
            # Potentially show an error message
    else:
        app.logger.warning(f"Attempted to delete non-existent note '{note_id}'.")
    return redirect(url_for('list_notes'))

@app.route('/export_notes')
def export_notes():
    """Compresses all notes into a zip file and provides it for download."""
    app.logger.info("Starting notes export process.")
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for filename in os.listdir(NOTES_DIR):
            if filename.endswith(".txt"):
                filepath = os.path.join(NOTES_DIR, filename)
                try:
                    zf.write(filepath, os.path.basename(filepath))
                    app.logger.debug(f"Added {filename} to zip.")
                except Exception as e:
                    app.logger.warning(f"Could not add {filename} to zip during export: {e}")
    memory_file.seek(0)
    app.logger.info("Notes export completed.")
    return send_file(memory_file,
                     mimetype='application/zip',
                     as_attachment=True,
                     download_name='home_assistant_notes_export.zip')

@app.route('/import_notes', methods=['POST'])
def import_notes():
    """Handles importing notes from an uploaded zip file."""
    app.logger.info("Starting notes import process.")
    if 'zip_file' not in request.files:
        app.logger.warning("No file part in import request.")
        return redirect(url_for('list_notes'))

    zip_file = request.files['zip_file']
    if zip_file.filename == '':
        app.logger.warning("No selected file for import.")
        return redirect(url_for('list_notes'))

    if zip_file and zip_file.filename.endswith('.zip'):
        try:
            with zipfile.ZipFile(io.BytesIO(zip_file.read()), 'r') as zf:
                for member in zf.namelist():
                    # Only process .txt files and avoid directory entries or hidden files
                    if member.endswith(".txt") and not member.startswith('__MACOSX/') and not member.startswith('.'):
                        # Sanitize filename to prevent path traversal
                        filename = os.path.basename(member)
                        # If the original files had UUIDs, they will be preserved. If not, generate new ones.
                        if not re.match(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\.txt$', filename):
                            app.logger.warning(f"Imported file '{filename}' does not follow UUID naming. Generating new UUID.")
                            new_filename_id = str(uuid.uuid4())
                            new_filename = f"{new_filename_id}.txt"
                        else:
                            new_filename = filename # Keep existing UUID filename

                        target_path = os.path.join(NOTES_DIR, new_filename)

                        # Prevent accidental overwrite if a file with the same UUID exists
                        if os.path.exists(target_path):
                            app.logger.warning(f"Note with ID '{os.path.splitext(new_filename)[0]}' already exists. Generating new UUID for imported file '{filename}'.")
                            new_filename_id = str(uuid.uuid4())
                            new_filename = f"{new_filename_id}.txt"
                            target_path = os.path.join(NOTES_DIR, new_filename)


                        with open(target_path, 'wb') as outfile:
                            outfile.write(zf.read(member))
                        app.logger.info(f"Imported note: {new_filename}")
            app.logger.info("Notes import process completed.")
        except zipfile.BadZipFile:
            app.logger.error("Uploaded file is not a valid ZIP file.")
        except Exception as e:
            app.logger.error(f"Error during notes import: {e}")
    else:
        app.logger.warning("Uploaded file is not a zip file.")

    return redirect(url_for('list_notes'))


if __name__ == '__main__':
    # Home Assistant addons run on specific ports, usually 8099 for web UIs
    app.run(host='0.0.0.0', port=8099, debug=False) # debug=False for production

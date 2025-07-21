# Home Assistant Notes Addon

A simple Home Assistant addon to create, manage, and store free-form text notes directly within your Home Assistant interface. Notes are persistent across reboots and addon updates.

## Features

* **Create New Notes:** Easily add new notes from a dedicated UI.
* **Persistent Storage:** Notes are saved as individual text files in a user-definable directory within your Home Assistant's `/config` folder (defaulting to `/config/notes`). This ensures notes persist even if the addon is uninstalled and reinstalled, or if your Home Assistant instance is migrated.
* **Free-Form Text:** Each note is a simple text file. The **first line** of the file will be used as the note's **title** (truncated to 50 characters in the list view). You can include plain text, Markdown, or even raw HTML within your notes for rich content.
* **Edit & Delete:** Convenient icons allow you to edit or delete notes directly from the list.
* **Export/Import:** Easily export all your notes as a `.zip` file for backup, or import notes from a `.zip` file.
* **Simple UI:** A clean and straightforward interface consistent with Home Assistant's design.

## Installation

1.  **Add this Repository to Home Assistant:**
    * In Home Assistant, navigate to **Settings** -> **Add-ons**.
    * Click on the **Add-on Store** button in the bottom right corner.
    * Click on the **three dots menu** in the top right corner and select **Repositories**.
    * Paste the URL of this GitHub repository:
        `https://github.com/ianpleasance/home-assistant-notes-addon`
    * Click **Add** and then **Close**.

2.  **Install the Notes Addon:**
    * You should now see the "Notes Addon" listed in the **Add-on Store** (you may need to refresh the page).
    * Click on the "Notes Addon" tile.
    * Click **Install**.

3.  **Start and Configure the Addon:**
    * After installation, go to the "Notes Addon" page.
    * Navigate to the **Configuration** tab. Here you can optionally change the `homeassistant_config_notes_path`. By default, notes will be saved in a folder named `notes` inside your Home Assistant's `/config` directory. You can change this to another relative path, e.g., `my_custom_notes_folder`.
    * Go back to the **Info** tab.
    * Enable **Start on boot** (recommended for persistence).
    * Enable **Show in sidebar** (recommended for easy access).
    * Click **Start**.

4.  **Access the Addon:**
    * Once started, you can access the Notes Addon from the Home Assistant sidebar (if "Show in sidebar" is enabled).

## Usage

* **View Notes:** Open the "Notes" sidebar panel. You'll see a list of your notes by their titles.
* **Create New Note:** Click the "Create New Note" button. Type your note content. The **first line** you type will be automatically used as the note's title in the list view.
* **Edit Note:** Click the pencil icon next to a note's title to edit its content.
* **Delete Note:** Click the trash can icon next to a note's title to delete it. You will be asked for confirmation.
* **Export Notes:** Click "Export All Notes" to download a zip file containing all your notes.
* **Import Notes:** Click "Import Notes" and select a zip file containing `.txt` note files. Notes will be added, generating new unique IDs if necessary to prevent overwrites.

## Development

If you want to contribute or modify this addon:

1.  Clone this repository: `git clone https://github.com/YOUR_GITHUB_USERNAME/your-notes-addon-repo.git`
2.  The addon's application logic is in `notes_addon/rootfs/app/main.py`.
3.  Templates for the UI are in `notes_addon/rootfs/app/templates/`.
4.  Styling is in `notes_addon/rootfs/app/static/`.
5.  Refer to the [Home Assistant Add-on Documentation](https://developers.home-assistant.io/docs/add-ons/) for more details on addon development.

## License

This project is licensed under the Apache 2.0 License - see the LICENSE file for details.

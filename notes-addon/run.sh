#!/usr/bin/with-contenv bashio

# Get the configured path for notes within the Home Assistant config directory
# Default to 'notes' if not set by the user
CONFIG_NOTES_PATH=$(bashio::config 'homeassistant_config_notes_path')
if [ -z "${CONFIG_NOTES_PATH}" ]; then
    CONFIG_NOTES_PATH="notes"
    bashio::log.warning "homeassistant_config_notes_path not set, defaulting to 'notes'."
fi

# The /config directory inside the addon container is mapped to Home Assistant's /config
# So, construct the full path for notes.
NOTES_DATA_DIR="/config/${CONFIG_NOTES_PATH}"

# Ensure the notes data directory exists
mkdir -p "${NOTES_DATA_DIR}" || bashio::exit.fatal "Failed to create notes data directory at ${NOTES_DATA_DIR}."

bashio::log.info "Notes will be stored in: ${NOTES_DATA_DIR}"

# Set an environment variable for the Flask app to use
export NOTES_DIR="${NOTES_DATA_DIR}"

# Run the Flask application
bashio::log.info "Starting Notes Addon..."
exec python3 /app/main.py

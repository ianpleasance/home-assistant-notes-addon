#!/bin/bash

# Temporarily comment out bashio calls to isolate Flask error
# CONFIG_NOTES_PATH=$(bashio::config 'homeassistant_config_notes_path')
# if [ -z "${CONFIG_NOTES_PATH}" ]; then
#     CONFIG_NOTES_PATH="notes"
#     bashio::log.warning "homeassistant_config_notes_path not set, defaulting to 'notes'."
# fi

# For now, hardcode NOTES_DATA_DIR for testing Flask
NOTES_DATA_DIR="/config/notes" # Default value

mkdir -p "${NOTES_DATA_DIR}" || exit 1 # Simplified error handling for test

echo "Notes will be stored in: ${NOTES_DATA_DIR}" # Use echo instead of bashio::log

export NOTES_DIR="${NOTES_DATA_DIR}"

echo "Starting Notes Addon..." # Use echo instead of bashio::log
exec python3 /app/main.py

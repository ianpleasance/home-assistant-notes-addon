#!/bin/bash

CONFIG_NOTES_PATH=$(bashio::config 'homeassistant_config_notes_path')
if [ -z "${CONFIG_NOTES_PATH}" ]; then
    CONFIG_NOTES_PATH="notes"
    bashio::log.warning "homeassistant_config_notes_path not set, defaulting to 'notes'."
fi

NOTES_DATA_DIR="/config/${CONFIG_NOTES_PATH}"

mkdir -p "${NOTES_DATA_DIR}" || exit 1
bashio::log.info "Notes will be stored in: ${NOTES_DATA_DIR}"

export NOTES_DIR="${NOTES_DATA_DIR}"

bashio::log.info "Starting Notes Addon..."
exec gunicorn --workers 2 --bind 0.0.0.0:8099 --chdir /app main:app

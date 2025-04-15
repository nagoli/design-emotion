#!/bin/bash

# Design Emotion Extension Build Script
# This script builds both Chrome and Firefox extensions with proper versioning

set -e  # Exit on error

# Configuration
SOURCE_DIR="./browser"
BUILD_DIR="./browser-build"
COMMON_MANIFEST="${SOURCE_DIR}/manifest.json"
CHROME_SPECIFIC="${SOURCE_DIR}/manifest-chrome-specific.json"
FIREFOX_SPECIFIC="${SOURCE_DIR}/manifest-firefox-specific.json"

# Create build directory
mkdir -p "${BUILD_DIR}"

# Extract version from common manifest
VERSION=$(grep -o '"version": "[^"]*"' "${COMMON_MANIFEST}" | cut -d '"' -f 4)
echo "Building extensions version ${VERSION}..."

# Define zip filenames
CHROME_ZIP="${BUILD_DIR}/d-e_v${VERSION}_chrome.zip"
FIREFOX_ZIP="${BUILD_DIR}/d-e_v${VERSION}_firefox.zip"

# Build Chrome extension
echo "Building Chrome extension..."
CHROME_BUILD_DIR="${BUILD_DIR}/d-e_v${VERSION}_chrome"
mkdir -p "${CHROME_BUILD_DIR}"

# Copy all required files for Chrome
cp -r "${SOURCE_DIR}"/*.js "${CHROME_BUILD_DIR}/"
cp -r "${SOURCE_DIR}"/*.html "${CHROME_BUILD_DIR}/"
cp -r "${SOURCE_DIR}"/*.svg "${CHROME_BUILD_DIR}/"
cp -r "${SOURCE_DIR}"/*.png "${CHROME_BUILD_DIR}/"
cp -r "${SOURCE_DIR}/_locales" "${CHROME_BUILD_DIR}/"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
  echo "Error: jq is required but not installed. Please install jq first."
  echo "On macOS: brew install jq"
  echo "On Ubuntu/Debian: apt-get install jq"
  exit 1
fi

# Merge common manifest with Chrome-specific parts
jq -s '.[0] * .[1]' "${COMMON_MANIFEST}" "${CHROME_SPECIFIC}" > "${CHROME_BUILD_DIR}/manifest.json"

# Create Chrome zip
cd "${CHROME_BUILD_DIR}"
zip -r "../${CHROME_ZIP##*/}" .
cd - > /dev/null

# Build Firefox extension
echo "Building Firefox extension..."
FIREFOX_BUILD_DIR="${BUILD_DIR}/firefox_build"
mkdir -p "${FIREFOX_BUILD_DIR}"

# Copy all required files for Firefox
cp -r "${SOURCE_DIR}"/*.js "${FIREFOX_BUILD_DIR}/"
cp -r "${SOURCE_DIR}"/*.html "${FIREFOX_BUILD_DIR}/"
cp -r "${SOURCE_DIR}"/*.svg "${FIREFOX_BUILD_DIR}/"
cp -r "${SOURCE_DIR}"/*.png "${FIREFOX_BUILD_DIR}/"
cp -r "${SOURCE_DIR}/_locales" "${FIREFOX_BUILD_DIR}/"

# Merge common manifest with Firefox-specific parts
jq -s '.[0] * .[1]' "${COMMON_MANIFEST}" "${FIREFOX_SPECIFIC}" > "${FIREFOX_BUILD_DIR}/manifest.json"

# Create Firefox zip
cd "${FIREFOX_BUILD_DIR}"
zip -r "../${FIREFOX_ZIP##*/}" .
cd - > /dev/null

# Clean up build directories
#rm -rf "${CHROME_BUILD_DIR}"
rm -rf "${FIREFOX_BUILD_DIR}"

echo "✅ Build complete!"
echo "Chrome extension: ${CHROME_ZIP}"
echo "Firefox extension: ${FIREFOX_ZIP}"

# Make script executable
chmod +x "$0"

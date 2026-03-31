# TidyPaper

TidyPaper is a minimal Chrome extension that routes recognized academic paper PDFs into `Downloads/Papers`.

## What It Does

- Intercepts downloads with `chrome.downloads.onDeterminingFilename`
- Detects likely paper PDFs from a conservative academic-domain allowlist
- Rewrites the target path to `Downloads/Papers/<filename>.pdf`
- Leaves every non-paper download untouched

## Current MVP Boundary

- The extension can only suggest a path relative to Chrome's default `Downloads` directory.
- It cannot force the system save dialog to open at an arbitrary absolute path like `D:\Papers`.
- If Chrome has `Ask where to save each file before downloading` enabled, the save dialog will open with `Downloads/Papers` preselected for recognized papers.
- If that Chrome setting is disabled, recognized papers will be saved directly into `Downloads/Papers`.

## Supported Sources

The MVP uses a fixed allowlist and only reroutes PDF-like downloads from:

- `arxiv.org`
- `openreview.net`
- `aclanthology.org`
- `proceedings.mlr.press`
- `papers.nips.cc`
- `proceedings.neurips.cc`
- `dl.acm.org`
- `ieeexplore.ieee.org`
- `link.springer.com`
- `sciencedirect.com`
- `nature.com`

## Install

1. Open Chrome and go to `chrome://extensions`.
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select this repository folder.

## Recommended Chrome Setting

To get the confirmation flow from the system save dialog:

1. Open Chrome settings.
2. Go to `Downloads`.
3. Enable `Ask where to save each file before downloading`.

## Manual Test

1. With the Chrome downloads prompt enabled, download a PDF from arXiv.
2. Confirm the save dialog defaults to `Downloads/Papers`.
3. Download a non-paper file such as a ZIP or PNG.
4. Confirm the extension does not rewrite that path.

## Notes

- If another installed extension also overrides download filenames, Chrome applies the suggestion from the last-installed extension that responds.
- The extension does not use any remote API, popup UI, options page, or local database.

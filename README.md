# TidyPaper

TidyPaper is a Chrome extension that routes recognized academic paper PDFs into categorized folders under `Downloads/Papers`.

## What It Does

- Intercepts downloads with `chrome.downloads.onDeterminingFilename`
- Detects likely paper PDFs from a conservative academic-domain allowlist plus paper-like filename patterns
- Lets you define routing rules by source domain and/or keywords
- Writes matched papers to `Downloads/Papers/<Category>/<Year>/<filename>.pdf`
- Falls back to `Downloads/Papers/Unsorted/<filename>.pdf` when a rule matches but no year can be extracted
- Leaves non-paper downloads untouched

## Current Boundary

- The extension can only suggest a path relative to Chrome's default `Downloads` directory.
- It cannot force the system save dialog to open at an arbitrary absolute path like `D:\Papers`.
- If Chrome has `Ask where to save each file before downloading` enabled, the save dialog opens with the routed folder preselected.
- If that Chrome setting is disabled, recognized papers are saved directly into the routed folder.

## Supported Paper Detection

The built-in paper detector recognizes PDF-like downloads from:

- `arxiv.org`
- `openreview.net`
- `aclanthology.org`
- `proceedings.mlr.press`
- `papers.nips.cc`
- `proceedings.neurips.cc`
- `dl.acm.org`
- `ieeexplore.ieee.org`
- `link.springer.com`
- `springer.com`
- `springernature.com`
- `sciencedirect.com`
- `nature.com`

It also keeps a small filename-pattern fallback for common paper filenames such as arXiv IDs and Springer article PDFs.

## Install

1. Open Chrome and go to `chrome://extensions`.
2. Enable `Developer mode`.
3. Click `Load unpacked`.
4. Select this repository folder.

## Configure Rules

1. Open the extension details page in `chrome://extensions`.
2. Click `Extension options`.
3. Add a rule with:
   - `Category`, such as `Radiology`
   - `Domains`, such as `link.springer.com`
   - `Keywords`, such as `radiology, imaging`
4. Reorder rules if needed. The first matching rule wins.

Rules are stored locally in `chrome.storage.local`.

## Recommended Chrome Setting

To keep the save dialog confirmation flow:

1. Open Chrome settings.
2. Go to `Downloads`.
3. Enable `Ask where to save each file before downloading`.

## Manual Test

1. Create a rule for `link.springer.com` with category `Radiology`.
2. With the Chrome downloads prompt enabled, download a Springer PDF whose URL or filename contains a year.
3. Confirm the save dialog defaults to `Downloads/Papers/Radiology/<year>/`.
4. Try a paper that matches the rule but has no detectable year and confirm it falls back to `Downloads/Papers/Unsorted/`.
5. Download a non-paper file such as a ZIP or PNG and confirm the extension does not rewrite that path.

## Notes

- If another installed extension also overrides download filenames, Chrome applies the suggestion from the last-installed extension that returns a filename override.
- TidyPaper does not use any remote API or backend service.

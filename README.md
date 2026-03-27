# TidyPaper

A minimalist academic paper PDF organizer for researchers.

TidyPaper automatically identifies paper metadata and organizes your messy PDF downloads into a clean, structured file system.

## Features (v0.1 MVP)

- **Scan & Parse** — Batch scan directories for PDF papers
- **Metadata Extraction** — Extract title, authors, DOI, arXiv ID from PDFs
- **External Lookup** — Query Crossref, arXiv, OpenAlex for accurate metadata
- **Auto Rename** — Generate standardized filenames (e.g. `2025 - ICLR - Paper Title.pdf`)
- **Auto Archive** — Organize into `Papers/{year}/{venue}/` structure
- **Preview & Confirm** — Review changes before applying
- **Undo** — Revert the last batch operation
- **Duplicate Detection** — Detect duplicates via hash, DOI, arXiv ID, or title similarity

## Quick Start

```bash
pip install -e ".[dev]"
tidypaper scan ./my-papers
tidypaper apply
tidypaper undo
```

## Requirements

- Python 3.10+
- `pip`

## Installation

```bash
git clone https://github.com/salory-go/TidyPaper.git
cd TidyPaper
python -m venv .venv
```

Activate the virtual environment:

```bash
# PowerShell
.venv\Scripts\Activate.ps1

# bash / zsh
source .venv/bin/activate
```

Install the project in editable mode:

```bash
pip install -e ".[dev]"
```

## Run Locally

Show the CLI entrypoint and available commands:

```bash
tidypaper --help
```

Typical workflow:

```bash
# Preview how PDFs will be renamed and organized
tidypaper scan ./my-papers

# Apply the staged plan
tidypaper apply

# Undo the latest successful batch
tidypaper undo
```

Useful options:

```bash
tidypaper scan ./my-papers --archive-root ./Papers
tidypaper scan ./my-papers --no-recursive
tidypaper apply --min-confidence 0.85
tidypaper apply --include-duplicates
tidypaper config
```

By default, staging data and the SQLite database are stored under `~/.tidypaper/`. You can override the database location with `--db-path`.

## License

MIT

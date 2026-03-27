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

## License

MIT

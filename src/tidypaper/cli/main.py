"""TidyPaper CLI — main entry point."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import click

from tidypaper.core.duplicate import check_duplicate
from tidypaper.core.executor import move_file, plan_organize
from tidypaper.core.merger import merge_metadata
from tidypaper.core.naming import generate_filename
from tidypaper.core.organizer import generate_archive_path
from tidypaper.core.parser import parse_pdf
from tidypaper.core.resolver import extract_arxiv_id, extract_doi, extract_venue_hints
from tidypaper.core.scanner import scan_directory
from tidypaper.core.undo import undo_latest_batch
from tidypaper.db.database import Database
from tidypaper.models.config import AppConfig
from tidypaper.models.operation import BatchRecord, OperationRecord
from tidypaper.providers.arxiv_lookup import ArxivLookupProvider
from tidypaper.providers.base import MetadataResult
from tidypaper.providers.doi_lookup import DoiLookupProvider
from tidypaper.providers.openalex import OpenAlexProvider

# ── Logging setup ───────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Shared state ────────────────────────────────────────────

_db: Database | None = None
_config = AppConfig()

# Staging area for previewed papers
_staged_papers: list[dict] = []


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        _db.connect()
    return _db


def _get_staging_path() -> Path:
    return Path.home() / ".tidypaper" / "staging.json"


# ── CLI Group ───────────────────────────────────────────────

@click.group()
@click.option("--db-path", default=None, help="Path to SQLite database file")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def cli(db_path: str | None, verbose: bool) -> None:
    """TidyPaper — A minimalist academic paper PDF organizer."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    if db_path:
        global _db
        _db = Database(db_path)
        _db.connect()


# ── Scan Command ────────────────────────────────────────────

@cli.command()
@click.argument("directory", type=click.Path(exists=True))
@click.option("--archive-root", "-o", default=None, help="Archive root directory")
@click.option("--template", "-t", default=None, help="Filename template")
@click.option("--no-recursive", is_flag=True, help="Don't scan subdirectories")
def scan(directory: str, archive_root: str | None, template: str | None, no_recursive: bool) -> None:
    """Scan a directory for PDFs and preview organization plan."""
    global _staged_papers

    config = _config
    if archive_root:
        config.archive_root = archive_root
    if template:
        config.filename_template = template

    pdfs = scan_directory(directory, recursive=not no_recursive)
    if not pdfs:
        click.echo("No PDF files found.")
        return

    click.echo(f"\n📄 Found {len(pdfs)} PDF files. Analyzing...\n")

    staged = asyncio.run(_analyze_pdfs(pdfs, config))
    _staged_papers = staged

    # Display preview
    _display_preview(staged)

    # Save staging info
    staging_path = _get_staging_path()
    staging_path.parent.mkdir(parents=True, exist_ok=True)
    staging_path.write_text(json.dumps(staged, ensure_ascii=False, indent=2), encoding="utf-8")

    click.echo(f"\n💾 Staging saved. Run 'tidypaper apply' to execute.")


async def _analyze_pdfs(pdfs: list[Path], config: AppConfig) -> list[dict]:
    """Parse, query, and fuse metadata for a list of PDFs."""
    db = _get_db()
    providers = [DoiLookupProvider(), ArxivLookupProvider(), OpenAlexProvider()]
    staged: list[dict] = []

    for i, pdf_path in enumerate(pdfs, 1):
        click.echo(f"  [{i}/{len(pdfs)}] {pdf_path.name}...", nl=False)

        try:
            # Parse PDF
            pdf_result = parse_pdf(pdf_path)

            # Extract identifiers from text
            raw_text = pdf_result.raw_text_first_pages
            filename = pdf_path.name
            pdf_result.doi = pdf_result.doi or extract_doi(raw_text)
            pdf_result.arxiv_id = pdf_result.arxiv_id or extract_arxiv_id(raw_text, filename)
            pdf_result.venue_hints = extract_venue_hints(raw_text)

            # Query providers
            hints = {
                "doi": pdf_result.doi,
                "arxiv_id": pdf_result.arxiv_id,
                "title": pdf_result.best_title,
            }
            provider_results: list[MetadataResult] = []
            for provider in providers:
                try:
                    result = await provider.query(**hints)
                    if result:
                        provider_results.append(result)
                except Exception as exc:
                    logger.debug("Provider %s failed: %s", provider.name, exc)

            # Merge
            paper = merge_metadata(pdf_result, provider_results)

            # Check duplicate
            dup = check_duplicate(paper, db)
            db.upsert_preview_paper(paper)

            # Generate names
            new_filename = generate_filename(paper, config.filename_template)
            target_dir = generate_archive_path(
                paper, config.archive_root, config.folder_template,
                config.unsorted_folder_name,
            )

            entry = {
                "source_path": str(pdf_path),
                "paper_id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "venue": paper.venue,
                "doi": paper.doi,
                "arxiv_id": paper.arxiv_id,
                "confidence": paper.confidence,
                "new_filename": new_filename,
                "target_dir": str(target_dir),
                "is_duplicate": dup.is_duplicate,
                "duplicate_type": dup.match_type,
                "duplicate_title": dup.existing_title,
                "file_hash": paper.file_hash,
                "evidence": paper.evidence,
            }
            staged.append(entry)


            status = "✓" if paper.confidence >= 0.60 else "?"
            if dup.is_duplicate:
                status = "⚠ DUP"
            click.echo(f" {status} [{paper.confidence:.2f}]")

        except Exception as exc:
            click.echo(f" ✗ Error: {exc}")
            logger.exception("Failed to process %s", pdf_path)

    return staged


def _display_preview(staged: list[dict]) -> None:
    """Display the organization preview table."""
    click.echo("\n" + "=" * 80)
    click.echo("  ORGANIZATION PREVIEW")
    click.echo("=" * 80)

    for i, entry in enumerate(staged, 1):
        conf = entry["confidence"]
        indicator = "🟢" if conf >= 0.85 else ("🟡" if conf >= 0.60 else "🔴")
        dup_tag = " ⚠️DUP" if entry["is_duplicate"] else ""

        click.echo(f"\n  [{i}] {indicator} Confidence: {conf:.2f}{dup_tag}")
        click.echo(f"      Source:  {Path(entry['source_path']).name}")
        click.echo(f"      → Name:  {entry['new_filename']}")
        click.echo(f"      → Path:  {entry['target_dir']}")
        if entry["title"]:
            click.echo(f"      Title:   {entry['title'][:70]}")
        if entry["venue"]:
            click.echo(f"      Venue:   {entry['venue']}")
        if entry["is_duplicate"]:
            click.echo(f"      ⚠ Duplicate ({entry['duplicate_type']}): {entry['duplicate_title'][:50]}")

    click.echo("\n" + "=" * 80)

    high = sum(1 for e in staged if e["confidence"] >= 0.85)
    mid = sum(1 for e in staged if 0.60 <= e["confidence"] < 0.85)
    low = sum(1 for e in staged if e["confidence"] < 0.60)
    dups = sum(1 for e in staged if e["is_duplicate"])

    click.echo(f"  Summary: 🟢 {high} high | 🟡 {mid} medium | 🔴 {low} low | ⚠️ {dups} duplicates")


# ── Apply Command ───────────────────────────────────────────

def _apply_entry(
    entry: dict,
    db: Database,
    batch: BatchRecord | None,
) -> tuple[BatchRecord | None, bool, str]:
    """Apply a single staged entry with filesystem rollback on DB failure."""
    paper = db.get_paper_by_id(entry["paper_id"])
    if paper is None:
        raise LookupError(
            "Paper metadata not found in the current database. Re-run 'tidypaper scan' "
            "with the same --db-path before applying."
        )

    src, dest = plan_organize(
        source_path=entry["source_path"],
        new_filename=entry["new_filename"],
        target_dir=Path(entry["target_dir"]),
    )

    next_batch = batch or BatchRecord()
    moved = False

    try:
        move_file(src, dest)
        moved = True

        paper.current_path = str(dest)
        paper.status = "organized"

        op = OperationRecord(
            batch_id=next_batch.batch_id,
            paper_id=paper.id,
            old_path=str(src),
            new_path=str(dest),
        )
        db.persist_applied_operation(op, paper, batch=next_batch if batch is None else None)

        if batch is not None:
            next_batch.operation_count += 1

        return next_batch, True, ""
    except Exception as exc:
        if moved:
            try:
                move_file(dest, src)
            except Exception as rollback_exc:
                logger.exception("Failed to roll back move for %s", src)
                return batch, False, f"{exc}; rollback failed: {rollback_exc}"
        return batch, False, str(exc)


@cli.command()
@click.option("--min-confidence", "-c", default=0.60, help="Minimum confidence to apply")
@click.option("--include-duplicates", is_flag=True, help="Also organize duplicate files")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def apply(min_confidence: float, include_duplicates: bool, yes: bool) -> None:
    """Execute the organization plan from the last scan."""
    staging_path = _get_staging_path()
    if not staging_path.exists():
        click.echo("❌ No staging data found. Run 'tidypaper scan <dir>' first.")
        sys.exit(1)

    staged = json.loads(staging_path.read_text(encoding="utf-8"))
    if not staged:
        click.echo("❌ Staging is empty.")
        return

    # Filter
    to_apply = [
        e for e in staged
        if e["confidence"] >= min_confidence
        and (include_duplicates or not e["is_duplicate"])
    ]

    if not to_apply:
        click.echo("No papers meet the criteria for organization.")
        return

    click.echo(f"\n📋 {len(to_apply)} papers will be organized:")
    for e in to_apply:
        click.echo(f"  • {Path(e['source_path']).name} → {e['new_filename']}")

    if not yes:
        if not click.confirm("\nProceed?"):
            click.echo("Cancelled.")
            return

    # Execute
    db = _get_db()
    batch: BatchRecord | None = None

    success_count = 0
    for entry in to_apply:
        try:
            batch, success, error = _apply_entry(entry, db, batch)
            if success:
                success_count += 1
            else:
                click.echo(f"  鉁?{Path(entry['source_path']).name}: {error}")
                continue
            click.echo(f"  ✓ {Path(entry['source_path']).name}")
        except Exception as exc:
            click.echo(f"  ✗ {Path(entry['source_path']).name}: {exc}")

    if batch is None or success_count == 0:
        click.echo(f"\n鉁?Organized 0/{len(to_apply)} papers.")
        click.echo("   No undo batch was created.")
        return
    click.echo(f"\n✅ Organized {success_count}/{len(to_apply)} papers (batch: {batch.batch_id[:8]}...)")
    click.echo("   Run 'tidypaper undo' to revert.")


# ── Undo Command ────────────────────────────────────────────

@cli.command()
def undo() -> None:
    """Undo the most recent organization batch."""
    db = _get_db()
    results = undo_latest_batch(db)

    if not results:
        click.echo("❌ No batch to undo.")
        return

    for r in results:
        status = "✓" if r.success else f"✗ {r.error}"
        click.echo(f"  {status} {Path(r.new_path).name} → {Path(r.old_path).name}")

    successes = sum(1 for r in results if r.success)
    click.echo(f"\n✅ Reverted {successes}/{len(results)} operations.")


# ── Config Command ──────────────────────────────────────────

@cli.command()
def config() -> None:
    """Display current configuration."""
    click.echo("\n📋 TidyPaper Configuration:")
    click.echo(f"  Archive root:      {_config.archive_root}")
    click.echo(f"  Filename template: {_config.filename_template}")
    click.echo(f"  Folder template:   {_config.folder_template}")
    click.echo(f"  Auto-apply ≥:      {_config.auto_apply_threshold}")
    click.echo(f"  Unsorted folder:   {_config.unsorted_folder_name}")
    click.echo(f"  Providers:         {', '.join(_config.metadata_provider_order)}")

    db = _get_db()
    click.echo(f"  Database:          {db.db_path}")


# ── Entry point ─────────────────────────────────────────────

if __name__ == "__main__":
    cli()

"""Top-level changelog runner.

This module is the entry point for the changelog pipeline:

    1. Read state (last_indexed_sha)
    2. Get new commits since last indexed
    3. For each commit: upsert_commit to store
    4. Enrich pending commits (LLM-based semantic metadata)
    5. Render daily/weekly digest
    6. Send via configured channels
    7. Update state

Usage:
    python -m src.temporal.run_changelog [--day YYYY-MM-DD] [--days N] [--dry-run]

Or called from watch.py:
    from src.temporal.run_changelog import run_changelog_pipeline
    run_changelog_pipeline(cfg, llm_client)
"""

import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


def run_changelog_pipeline(
    config: Dict[str, Any],
    llm_client: Any,
    *,
    day: Optional[date] = None,
    graph_store: Any = None,
    dry_run: bool = False,
) -> int:
    """Run the full changelog pipeline.

    Args:
        config: Application config dict.
        llm_client: OpenAI-compatible chat client.
        day: Optional specific date to render digest for.
            If None, uses today.
        graph_store: Optional graph store for hub-module detection.
        dry_run: If True, render but don't deliver.

    Returns:
        Number of commits processed.
    """
    from src.temporal.store import TemporalStore, DEFAULT_DB_PATH
    from src.temporal.enricher import enrich_pending
    from src.temporal.digest import render_daily
    from src.temporal.channels import load_channels
    from src.temporal.sources import resolve_source
    from src.temporal.sources._adapter import upsert_changeset

    # Load config
    temporal_cfg = config.get("temporal", {})
    if not temporal_cfg.get("enabled", True):
        logger.info("[Changelog] Temporal module disabled.")
        return 0

    bootstrap_count = temporal_cfg.get("bootstrap_commits", 100)
    max_diff_lines = temporal_cfg.get("enrichment", {}).get("max_diff_lines", 2000)
    auto_pull = temporal_cfg.get("auto_pull", False)
    workspace = Path(config.get("_defaults", {}).get("workspace_path", "workspace")).resolve()

    # Resolve change source (git or fs_diff, auto-detected)
    source = resolve_source(config, workspace)
    logger.info(f"[Changelog] Using change source: {source.name}")

    # Auto-pull only meaningful for git
    if auto_pull and source.name == "git":
        logger.info("[Changelog] Auto-pull enabled, fetching latest...")
        import subprocess
        result = subprocess.run(
            ["git", "fetch", "origin"],
            capture_output=True, text=True, timeout=60,
        )
        if result.returncode == 0:
            pull = subprocess.run(
                ["git", "pull", "origin"],
                capture_output=True, text=True, timeout=120,
            )
            if pull.returncode == 0:
                logger.info("[Changelog] Pulled latest changes.")
            else:
                logger.warning(f"[Changelog] Pull failed: {pull.stderr.strip()}")
        else:
            logger.warning(f"[Changelog] Fetch failed: {result.stderr.strip()}")

    # Initialize store
    db_path = DEFAULT_DB_PATH
    store = TemporalStore(db_path)

    # Detect changes via the abstracted source
    changesets = source.detect_changes(max_items=bootstrap_count)

    if not changesets:
        logger.info("[Changelog] No new changes detected.")
        return 0

    logger.info(f"[Changelog] Found {len(changesets)} new change(s).")

    # Upsert new changesets through the adapter
    for cs in changesets:
        try:
            upsert_changeset(store, cs)
        except Exception as e:
            logger.warning(f"[Changelog] Failed to upsert {cs.id[:12]}: {e}")

    # Enrich pending commits
    logger.info("[Changelog] Enriching commits...")
    enriched = enrich_pending(
        store,
        llm_client=llm_client,
        config=config,
        graph_store=graph_store,
        max_diff_lines=max_diff_lines,
    )
    logger.info(f"[Changelog] Enriched {enriched} commit(s).")

    # Render daily digest
    target_day = day or date.today()
    logger.info(f"[Changelog] Rendering digest for {target_day}...")

    if dry_run:
        # Just render, don't deliver
        digest = render_daily(store, target_day, fmt="markdown")
        logger.info(f"[Changelog] Dry run — rendered digest:\n{digest[:500]}...")
    else:
        # Load channels and deliver
        channels = load_channels(config)
        if channels:
            meta = {"date": target_day.isoformat()}
            for channel in channels:
                try:
                    digest = render_daily(store, target_day, fmt=channel.name)
                    channel.send(digest, fmt="markdown", meta=meta)
                    logger.info(f"[Changelog] Delivered via {channel.name}")
                except Exception as e:
                    logger.error(f"[Changelog] Channel {channel.name} failed: {e}")
        else:
            logger.info("[Changelog] No delivery channels configured.")
            # Still write to default file location
            digest = render_daily(store, target_day, fmt="markdown")
            from src.temporal.channels import FileChannel
            fc = FileChannel(path="context/changelog/{date}.md")
            fc.send(digest, meta={"date": target_day.isoformat()})
            logger.info(f"[Changelog] Written to context/changelog/{target_day}.md")

    # Update state via the source
    if changesets:
        source.mark_processed(changesets[-1])
        logger.info(f"[Changelog] State updated. Last processed: {changesets[-1].id[:12]}.")

    return len(changesets)


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run the changelog pipeline (enrich + digest + deliver)."
    )
    parser.add_argument(
        "--day",
        type=str,
        help="Specific date to render (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back (for module digests).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render digest but don't deliver.",
    )
    parser.add_argument(
        "--config",
        "-c",
        default="config.yaml",
        help="Configuration file.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Verbose logging.",
    )
    args = parser.parse_args()

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    from src.config import load_config
    config = load_config(args.config)

    from src.client import ResilientClient
    defaults = config.get("_defaults", {})
    client = ResilientClient(
        api_key=defaults["api_key"],
        base_url=defaults["api_base_url"],
        max_retries=cfg["retry"]["max_attempts"],
        base_delay=cfg["retry"]["base_delay_s"],
        max_delay=cfg["retry"]["max_delay_s"],
    )

    day = None
    if args.day:
        try:
            day = datetime.strptime(args.day, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"Invalid date format: {args.day}. Use YYYY-MM-DD.")
            sys.exit(1)

    graph_store = None
    if config.get("graph", {}).get("enabled"):
        try:
            from src.graph.store import GraphStore
            graph_cfg = config.get("graph", {})
            graph_store = GraphStore(persist_dir=graph_cfg.get("persist_dir", ".graphdb"))
        except Exception as e:
            logger.warning(f"Could not load graph store: {e}")

    count = run_changelog_pipeline(
        config,
        client,
        day=day,
        graph_store=graph_store,
        dry_run=args.dry_run,
    )

    logger.info(f"[Changelog] Pipeline complete. Processed {count} commit(s).")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
FastIntercom Sync Daemon - Maintains data freshness for MCP server.

This daemon runs independently of the MCP server to maintain fresh data.
It respects MCP's stateless principle by managing sync state separately.

Usage:
    python scripts/fastintercom-sync-daemon.py [--interval MINUTES]
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.logger import get_logger

logger = get_logger("fastintercom_sync_daemon")


class SyncDaemon:
    """Daemon that keeps FastIntercom data fresh."""

    def __init__(self, interval_minutes: int = 15):
        self.interval = timedelta(minutes=interval_minutes)
        self.db_path = Path.home() / ".fastintercom" / "data.db"
        self.running = False

    async def sync_once(self) -> bool:
        """Run a single sync operation."""
        try:
            logger.info("Starting FastIntercom sync...")

            # Use subprocess to run FastIntercom CLI
            # This keeps the sync logic separate from the MCP server
            import subprocess

            env = os.environ.copy()
            # Ensure token is available
            if "INTERCOM_ACCESS_TOKEN" not in env:
                logger.error("INTERCOM_ACCESS_TOKEN not set")
                return False

            # Run sync with appropriate timeframe
            # Sync last 7 days to ensure good coverage
            result = subprocess.run(
                ["python", "-m", "fast_intercom_mcp.cli", "sync", "--days", "7"],
                capture_output=True,
                text=True,
                env=env,
                timeout=300,  # 5 minute timeout
            )

            if result.returncode == 0:
                logger.info("Sync completed successfully")
                logger.debug(f"Sync output: {result.stdout}")

                # Write sync metadata (in real implementation, this would go in SQLite)
                metadata_path = self.db_path.parent / "sync_metadata.json"
                import json

                metadata = {
                    "last_sync": datetime.now().isoformat(),
                    "sync_success": True,
                    "coverage_days": 7,
                    "sync_duration_seconds": 0,  # Would measure actual duration
                }
                metadata_path.write_text(json.dumps(metadata, indent=2))

                return True
            else:
                logger.error(f"Sync failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            logger.error("Sync timed out after 5 minutes")
            return False
        except Exception as e:
            logger.error(f"Sync error: {e}")
            return False

    async def run(self):
        """Run the daemon continuously."""
        self.running = True
        logger.info(
            f"Starting sync daemon with {self.interval.total_seconds() / 60:.0f} minute interval"
        )

        # Initial sync
        await self.sync_once()

        while self.running:
            try:
                # Wait for next sync interval
                logger.info(
                    f"Next sync in {self.interval.total_seconds() / 60:.0f} minutes"
                )
                await asyncio.sleep(self.interval.total_seconds())

                # Run sync
                success = await self.sync_once()

                if not success:
                    # On failure, retry sooner
                    logger.warning("Sync failed, retrying in 5 minutes")
                    await asyncio.sleep(300)  # 5 minutes

            except asyncio.CancelledError:
                logger.info("Daemon shutdown requested")
                break
            except Exception as e:
                logger.error(f"Daemon error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

        logger.info("Sync daemon stopped")

    def stop(self):
        """Stop the daemon."""
        self.running = False


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="FastIntercom sync daemon - maintains fresh data for MCP server"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=15,
        help="Sync interval in minutes (default: 15)",
    )
    parser.add_argument("--once", action="store_true", help="Run sync once and exit")

    args = parser.parse_args()

    # Check for required environment variables
    if not os.getenv("INTERCOM_ACCESS_TOKEN"):
        logger.error("INTERCOM_ACCESS_TOKEN environment variable not set")
        sys.exit(1)

    daemon = SyncDaemon(interval_minutes=args.interval)

    if args.once:
        # Run once and exit
        success = await daemon.sync_once()
        sys.exit(0 if success else 1)
    else:
        # Run continuously
        try:
            await daemon.run()
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())

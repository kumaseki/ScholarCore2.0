import argparse
import logging
import sys
from src.core.logger import configure_logging
from src.services.daily_flow import DailyFlow

# 1. 配置日志 (必须是第一步)
configure_logging(level=logging.INFO)
logger = logging.getLogger("main")

def main():
    parser = argparse.ArgumentParser(description="ScholarCore 2.0 CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: daily
    daily_parser = subparsers.add_parser("daily", help="Run daily paper fetch & review")
    daily_parser.add_argument("--days", type=int, default=1, help="Fetch papers from last N days")
    daily_parser.add_argument("--force-email", action="store_true", help="Send email even if no high scores")
    daily_parser.add_argument("--limit", type=int, default=None, help="Limit number of papers (for testing)")

    args = parser.parse_args()

    if args.command == "daily":
        logger.info("🚀 Starting Daily Flow...")
        try:
            flow = DailyFlow()
            flow.run(days_back=args.days, force_email=args.force_email, max_limit=args.limit)
            logger.info("🎉 Daily Flow Completed Successfully.")
        except KeyboardInterrupt:
            logger.warning("⚠️ User interrupted process.")
        except Exception as e:
            logger.critical(f"🔥 System Crash: {e}", exc_info=True)
            sys.exit(1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
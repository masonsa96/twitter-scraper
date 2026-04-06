#!/usr/bin/env python3
"""CLI entry point for Twitter/X feed scraper and analyzer."""

import argparse
import json
import logging
import os
import sys

from config import DEFAULT_OUTPUT_DIR, MAX_PAGES
from models import Tweet, UserProfile
from scraper import NitterScraper
from analyzer import TweetAnalyzer
from reporter import print_report, save_report


def parse_args():
    parser = argparse.ArgumentParser(
        description="Scrape and analyze a Twitter/X user's feed via Nitter.",
        epilog="Example: python main.py elonmusk --max-pages 3",
    )
    parser.add_argument("username", help="Twitter/X username to scrape (without @)")
    parser.add_argument("--instance", help="Specific Nitter instance URL to use")
    parser.add_argument("--max-pages", type=int, default=MAX_PAGES, help=f"Max pages to scrape (default: {MAX_PAGES})")
    parser.add_argument("--output-dir", default=DEFAULT_OUTPUT_DIR, help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--no-analysis", action="store_true", help="Only scrape, skip analysis")
    parser.add_argument("--load-json", metavar="FILE", help="Load previously scraped JSON instead of scraping")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    return parser.parse_args()


def main():
    args = parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    username = args.username.lstrip("@")
    os.makedirs(args.output_dir, exist_ok=True)

    profile = None
    tweets = []

    if args.load_json:
        # Load from existing JSON
        logging.info(f"Loading tweets from {args.load_json}")
        with open(args.load_json) as f:
            data = json.load(f)
        if "profile" in data:
            profile = UserProfile.from_dict(data["profile"])
        tweets = [Tweet.from_dict(t) for t in data.get("tweets", [])]
        logging.info(f"Loaded {len(tweets)} tweets.")
    else:
        # Scrape from Nitter
        print(f"Scraping @{username}'s feed...")
        scraper = NitterScraper(username, instance=args.instance, max_pages=args.max_pages)

        try:
            profile = scraper.scrape_profile()
            if profile.display_name:
                print(f"Found profile: {profile.display_name} (@{username})")
                print(f"  Followers: {profile.followers:,} | Following: {profile.following:,}")
        except Exception as e:
            logging.warning(f"Could not scrape profile: {e}")

        try:
            tweets = scraper.scrape_tweets()
            print(f"Scraped {len(tweets)} tweets.")
        except ConnectionError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        if tweets:
            # Save raw data
            out_file = os.path.join(args.output_dir, f"{username}_tweets.json")
            data = {
                "username": username,
                "profile": profile.to_dict() if profile else None,
                "tweets": [t.to_dict() for t in tweets],
            }
            with open(out_file, "w") as f:
                json.dump(data, f, indent=2, default=str)
            print(f"Saved tweet data to {out_file}")

    if not tweets:
        print("No tweets found. Try a different username or Nitter instance.")
        sys.exit(0)

    if args.no_analysis:
        print("Scraping complete (analysis skipped).")
        sys.exit(0)

    # Run analysis
    print("\nAnalyzing tweets...")
    analyzer = TweetAnalyzer(tweets, username)
    analysis = analyzer.full_analysis()

    # Print report
    print_report(analysis, profile)

    # Save JSON report
    report_file = os.path.join(args.output_dir, f"{username}_report.json")
    save_report(analysis, report_file, profile)
    print(f"Full report saved to {report_file}")


if __name__ == "__main__":
    main()

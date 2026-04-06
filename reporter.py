"""Report formatting and output."""

import json


def print_report(analysis: dict, profile=None):
    """Print a formatted analysis report to stdout."""
    username = profile.username if profile else "unknown"
    sep = "=" * 60

    print(f"\n{sep}")
    print(f"  Twitter/X Analysis Report: @{username}")
    print(sep)

    # Profile overview
    if profile and profile.display_name:
        print(f"\n--- Profile Overview ---")
        print(f"  Name:       {profile.display_name}")
        if profile.bio:
            print(f"  Bio:        {profile.bio[:100]}")
        print(f"  Followers:  {profile.followers:,}")
        print(f"  Following:  {profile.following:,}")
        print(f"  Tweets:     {profile.tweet_count:,}")
        if profile.joined:
            print(f"  Joined:     {profile.joined}")

    # Posting frequency
    freq = analysis.get("posting_frequency", {})
    if freq:
        print(f"\n--- Posting Frequency ---")
        print(f"  Total tweets scraped: {freq.get('total_tweets', 'N/A')}")
        if "date_range" in freq:
            print(f"  Date range:           {freq['date_range']}")
            print(f"  Tweets per day:       {freq['tweets_per_day']}")
            print(f"  Tweets per week:      {freq['tweets_per_week']}")
            if freq.get("most_active_days"):
                print(f"  Most active days:     {', '.join(freq['most_active_days'])}")
            if freq.get("peak_hours_utc"):
                hours = ", ".join(f"{h}:00" for h in freq["peak_hours_utc"])
                print(f"  Peak hours (UTC):     {hours}")

    # Engagement
    eng = analysis.get("engagement", {})
    if eng:
        print(f"\n--- Engagement Analysis ---")
        print(f"  Avg likes:        {eng.get('avg_likes', 0)}")
        print(f"  Avg retweets:     {eng.get('avg_retweets', 0)}")
        print(f"  Avg replies:      {eng.get('avg_replies', 0)}")
        print(f"  Total engagement: {eng.get('total_engagement', 0):,}")
        if eng.get("media_engagement_lift") != "N/A":
            print(f"  Media lift:       {eng.get('media_engagement_lift', 'N/A')}")
        if eng.get("top_tweets"):
            print(f"\n  Top Performing Tweets:")
            for i, tw in enumerate(eng["top_tweets"][:3], 1):
                print(f"    {i}. [{tw['total']} eng] \"{tw['text'][:80]}...\"")

    # Best posting times
    times = analysis.get("best_posting_times", {})
    if times and times.get("best_hour_utc") is not None:
        print(f"\n--- Best Posting Times ---")
        print(f"  Best hour (UTC):  {times['best_hour_utc']}:00")
        print(f"  Best day:         {times['best_day']}")
        if times.get("top_3_hours"):
            hours = ", ".join(f"{h}:00" for h in times["top_3_hours"])
            print(f"  Top 3 hours:      {hours}")
        if times.get("top_3_days"):
            print(f"  Top 3 days:       {', '.join(times['top_3_days'])}")

    # Topics
    topics = analysis.get("topics", {})
    if topics:
        print(f"\n--- Topics & Keywords ---")
        if topics.get("top_hashtags"):
            ht = ", ".join(f"#{h} ({c})" for h, c in topics["top_hashtags"][:10])
            print(f"  Top hashtags:  {ht}")
        if topics.get("top_keywords"):
            kw = ", ".join(f"{w} ({c})" for w, c in topics["top_keywords"][:10])
            print(f"  Top keywords:  {kw}")
        if topics.get("top_mentions"):
            mn = ", ".join(f"@{m} ({c})" for m, c in topics["top_mentions"][:10])
            print(f"  Top mentions:  {mn}")

    # Content themes
    themes = analysis.get("content_themes", {})
    if themes:
        print(f"\n--- Content Themes ---")
        print(f"  Original:    {themes.get('pct_original', 0)}%")
        print(f"  Retweets:    {themes.get('pct_retweets', 0)}%")
        print(f"  Replies:     {themes.get('pct_replies', 0)}%")
        print(f"  With media:  {themes.get('pct_with_media', 0)}%")
        print(f"  Avg length:  {themes.get('avg_tweet_length', 0)} chars")

    # Sentiment
    sentiment = analysis.get("sentiment", {})
    if sentiment and "pct_positive" in sentiment:
        print(f"\n--- Sentiment Analysis ---")
        print(f"  Positive: {sentiment['pct_positive']}%  |  Neutral: {sentiment['pct_neutral']}%  |  Negative: {sentiment['pct_negative']}%")
        print(f"  Avg polarity:     {sentiment['avg_polarity']} (-1 negative to +1 positive)")
        print(f"  Avg subjectivity: {sentiment['avg_subjectivity']} (0 objective to 1 subjective)")

    # Business insights
    insights = analysis.get("insights", [])
    if insights:
        print(f"\n{'=' * 60}")
        print(f"  KEY BUSINESS INSIGHTS")
        print(f"{'=' * 60}")
        for i, insight in enumerate(insights, 1):
            print(f"  {i}. {insight}")

    print(f"\n{sep}\n")


def save_report(analysis: dict, filepath: str, profile=None):
    """Save the analysis as a JSON report."""
    output = {"analysis": analysis}
    if profile:
        output["profile"] = profile.to_dict()

    with open(filepath, "w") as f:
        json.dump(output, f, indent=2, default=str)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
TEMPORARY STUB for GitHub Actions
Keeps workflow alive if site parsing is broken or disabled.
"""

import os
from datetime import datetime, timezone
from feedgen.feed import FeedGenerator

# === CONFIG ===
OUT = os.path.join(os.path.dirname(__file__), "..", os.path.basename(__file__).replace(".py", ".xml"))
FEED_TITLE = "Temporary Empty Feed"
DESCRIPTION = "This is a stub feed to keep GitHub Actions workflow running."

print(f"⚠️  Skipping parsing: {os.path.basename(__file__)} (site temporarily unavailable)")

# === create minimal XML ===
fg = FeedGenerator()
fg.id("stub-feed")
fg.title(FEED_TITLE)
fg.link(href="https://example.com", rel="alternate")
fg.description(DESCRIPTION)
fg.language("en")

# add dummy entry just for structure
fe = fg.add_entry()
fe.id("stub-entry")
fe.title("Feed temporarily disabled")
fe.link(href="https://example.com")
fe.pubDate(datetime.now(timezone.utc))
fe.description("No data — site unavailable or parser disabled.")

fg.rss_file(OUT, encoding="utf-8")
print(f"✅ Stub RSS written: {OUT}")

#!/usr/bin/env python3
"""Check subscribed RSS feeds for new posts and add them to feed.json"""

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

FEED_JSON = Path(__file__).parent / "feed.json"

def fetch_rss(url):
    """Fetch and parse an RSS feed"""
    try:
        req = Request(url, headers={"User-Agent": "TES-Feed/1.0"})
        with urlopen(req, timeout=15) as resp:
            return ET.fromstring(resp.read())
    except Exception as e:
        print(f"  Error fetching {url}: {e}")
        return None

def parse_rss_items(root, source_name):
    """Extract items from RSS XML"""
    items = []
    ns = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}
    
    # Handle both RSS 2.0 and Atom
    for item in root.iter("item"):
        title = item.findtext("title", "")
        link = item.findtext("link", "")
        desc = item.findtext("description", "")
        date = item.findtext("pubDate", "")
        
        if not date:
            date = item.findtext("dc:date", "", ns)
        
        # Clean description (strip HTML tags roughly)
        import re
        clean_desc = re.sub(r'<[^>]+>', '', desc)[:500] if desc else ""
        
        if link:
            items.append({
                "title": title.strip(),
                "url": link.strip(),
                "summary": clean_desc.strip(),
                "date": date.strip(),
                "source": source_name,
                "auto": True
            })
    
    # Atom feeds
    for entry in root.iter("{http://www.w3.org/2005/Atom}entry"):
        title = entry.findtext("{http://www.w3.org/2005/Atom}title", "")
        link_el = entry.find("{http://www.w3.org/2005/Atom}link[@rel='alternate']")
        if link_el is None:
            link_el = entry.find("{http://www.w3.org/2005/Atom}link")
        link = link_el.get("href", "") if link_el is not None else ""
        
        summary = entry.findtext("{http://www.w3.org/2005/Atom}summary", "")
        if not summary:
            summary = entry.findtext("{http://www.w3.org/2005/Atom}content", "")
        
        date = entry.findtext("{http://www.w3.org/2005/Atom}published", "")
        if not date:
            date = entry.findtext("{http://www.w3.org/2005/Atom}updated", "")
        
        import re
        clean_summary = re.sub(r'<[^>]+>', '', summary)[:500] if summary else ""
        
        if link:
            items.append({
                "title": title.strip(),
                "url": link.strip(),
                "summary": clean_summary.strip(),
                "date": date.strip(),
                "source": source_name,
                "auto": True
            })
    
    return items

def sync():
    data = json.loads(FEED_JSON.read_text())
    existing_urls = {item["url"] for item in data["items"]}
    new_count = 0
    
    for sub in data.get("subscriptions", []):
        print(f"Checking: {sub['name']} ({sub['url']})")
        root = fetch_rss(sub["url"])
        if root is None:
            continue
        
        items = parse_rss_items(root, sub["name"])
        for item in items:
            if item["url"] not in existing_urls:
                data["items"].append(item)
                existing_urls.add(item["url"])
                new_count += 1
                print(f"  + {item['title'][:60]}")
    
    if new_count > 0:
        FEED_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\nAdded {new_count} new items")
    else:
        print("\nNo new items")
    
    return new_count

if __name__ == "__main__":
    sync()

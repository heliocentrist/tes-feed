#!/usr/bin/env python3
"""Scan foam-notes ingested sources and add them to feed.json"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

FEED_JSON = Path(__file__).parent / "feed.json"
FOAM_NOTES_SOURCES = Path("/home/claude/foam-notes/sources/ingested")


def parse_yaml_frontmatter(text):
    """Extract YAML frontmatter from markdown text"""
    if not text.startswith("---"):
        return None
    
    end = text.find("---", 3)
    if end == -1:
        return None
    
    yaml_text = text[3:end].strip()
    data = {}
    
    for line in yaml_text.split("\n"):
        line = line.rstrip()
        if not line or line.startswith("#"):
            continue
        
        # Simple key: value parsing (handles quoted strings, basic scalars)
        match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$', line)
        if match:
            key, val = match.group(1), match.group(2).strip()
            
            # Strip quotes
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            
            data[key] = val
    
    return data


def extract_description(text):
    """Extract first paragraph after frontmatter as description"""
    # Remove frontmatter
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            text = text[end + 3:]
    
    # Get first non-empty line
    for line in text.strip().split("\n"):
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith("-"):
            # Strip markdown links, bold, etc for plain text summary
            plain = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', line)  # [text](url) -> text
            plain = re.sub(r'\*\*([^\*]+)\*\*', r'\1', plain)  # **bold** -> bold
            plain = re.sub(r'\*([^\*]+)\*', r'\1', plain)  # *italic* -> italic
            plain = re.sub(r'`([^`]+)`', r'\1', plain)  # `code` -> code
            return plain[:500]
    
    return ""


def parse_created_date(date_str):
    """Parse date from frontmatter, return datetime or None"""
    if not date_str:
        return None
    
    # Handle YYYY-MM-DD format
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    
    # Handle ISO format with time
    try:
        if "T" in date_str:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            return dt
    except ValueError:
        pass
    
    return None


def scan_foam_notes():
    """Scan foam-notes ingested sources and return feed items"""
    items = []
    
    if not FOAM_NOTES_SOURCES.exists():
        print(f"Foam notes sources directory not found: {FOAM_NOTES_SOURCES}")
        return items
    
    for md_file in FOAM_NOTES_SOURCES.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        fm = parse_yaml_frontmatter(text)
        
        if not fm:
            continue
        
        url = fm.get("source", "").strip()
        if not url or not url.startswith(("http://", "https://")):
            continue  # Skip files without a valid source URL
        
        title = fm.get("title", "").strip()
        if not title:
            # Use filename as fallback
            title = md_file.stem
        
        # Parse date
        date_str = fm.get("created", "")
        dt = parse_created_date(date_str)
        
        # Use file modification time as fallback
        if not dt:
            mtime = md_file.stat().st_mtime
            dt = datetime.fromtimestamp(mtime, tz=timezone.utc)
        
        # Format as RFC 2822 date string
        date_rfc = dt.strftime("%a, %d %b %Y %H:%M:%S +0000")
        
        # Get description from frontmatter or extract from content
        description = fm.get("description", "").strip()
        if not description or description == title:
            description = extract_description(text)
        
        items.append({
            "title": title,
            "url": url,
            "summary": description[:500],
            "date": date_rfc,
            "source": "Foam Notes",
            "auto": False
        })
    
    return items


def sync():
    data = json.loads(FEED_JSON.read_text())
    existing_urls = {item["url"] for item in data["items"]}
    new_count = 0
    
    foam_items = scan_foam_notes()
    print(f"Scanned foam-notes: found {len(foam_items)} sources with valid URLs")
    
    for item in foam_items:
        if item["url"] not in existing_urls:
            data["items"].append(item)
            existing_urls.add(item["url"])
            new_count += 1
            print(f"  + {item['title'][:60]}")
    
    if new_count > 0:
        FEED_JSON.write_text(json.dumps(data, indent=2, ensure_ascii=False))
        print(f"\nAdded {new_count} new items from foam-notes")
    else:
        print("\nNo new items from foam-notes")
    
    return new_count


if __name__ == "__main__":
    sync()

#!/usr/bin/env python3
"""
yt2claude.py — Fetch a YouTube video's transcript and save it as a clean
text file ready to paste into a Claude chat.

Usage:
    python3 yt2claude.py <youtube_url> [--timestamps] [--lang en]

Requires:
    pip install youtube-transcript-api requests

Notes on what this does and doesn't do:
- This only captures spoken/captioned words. It has no idea what's on
  screen (slides, demos, on-screen text). Fine for podcasts/interviews,
  not a substitute for actually watching anything visual.
- It prefers a manually-created (human) transcript over YouTube's
  auto-generated one when both exist, because auto-captions are lower
  quality (no punctuation logic, more misheard words/names).
- If the video has captions disabled or none exist, this will fail
  loudly and tell you why, rather than silently giving you nothing.
- This uses an unofficial method (the same caption endpoint the YouTube
  player uses), not the official YouTube Data API. It can break if
  YouTube changes something server-side. If it stops working, that's
  the first thing to suspect.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import requests
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    TranscriptsDisabled,
    NoTranscriptFound,
    VideoUnavailable,
)


def _is_egress_policy_block(exc: Exception) -> bool:
    """
    True when a request was rejected by a policy-enforcing egress proxy
    rather than by YouTube. In sandboxed environments (e.g. Claude Code on
    the web) outbound HTTPS goes through a proxy that answers 403/407 to
    CONNECT for hosts that aren't on the environment's allowlist. That looks
    nothing like a YouTube-side failure, so we detect it explicitly to avoid
    sending people chasing the wrong problem.
    """
    text = str(exc)
    if "Tunnel connection failed" in text:
        return True
    proxy_denied = ("403 Forbidden" in text) or ("407" in text)
    return isinstance(exc, requests.exceptions.ProxyError) and proxy_denied


_EGRESS_BLOCK_MESSAGE = (
    "Network policy blocked the request before it reached YouTube.\n"
    "This environment's egress proxy denied the connection to youtube.com "
    "(a 403/407 on the proxy tunnel), so this is NOT a YouTube outage, a "
    "captions-disabled video, or a bug in this script.\n"
    "Fixes:\n"
    "  - Run this script locally, where there's no egress restriction, or\n"
    "  - Have an admin add youtube.com to this environment's network "
    "allowlist.\n"
    "Do not try to route around the proxy — that's the org's security policy."
)


def extract_video_id(url: str) -> str:
    """Handle youtube.com/watch?v=, youtu.be/, /shorts/, /embed/ formats."""
    patterns = [
        r"(?:v=|/shorts/|/embed/|youtu\.be/)([A-Za-z0-9_-]{11})",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    # Last resort: maybe they just pasted the bare ID
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url.strip()):
        return url.strip()
    raise ValueError(f"Couldn't find a video ID in: {url}")


def get_metadata(video_id: str) -> dict:
    """Title/author via YouTube's public oEmbed endpoint. No API key needed."""
    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
    try:
        resp = requests.get(oembed_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        return {"title": data.get("title", "Unknown title"),
                "author": data.get("author_name", "Unknown channel")}
    except Exception:
        return {"title": "Unknown title", "author": "Unknown channel"}


def get_transcript(video_id: str, lang: str = "en"):
    """
    Prefer manually-created transcript > auto-generated > translated fallback.
    Returns (FetchedTranscript, source_description) or raises with a clear message.
    """
    api = YouTubeTranscriptApi()
    try:
        transcript_list = api.list(video_id)
    except TranscriptsDisabled:
        raise RuntimeError(
            "This video has captions/transcripts disabled by the uploader. "
            "There is no transcript to fetch — no workaround for this."
        )
    except VideoUnavailable:
        raise RuntimeError(
            "Video unavailable (private, deleted, or region-locked)."
        )
    except requests.exceptions.RequestException as e:
        if _is_egress_policy_block(e):
            raise RuntimeError(_EGRESS_BLOCK_MESSAGE)
        raise RuntimeError(f"Network error fetching transcript list: {e}")

    # 1. Try manually-created in requested language
    try:
        t = transcript_list.find_manually_created_transcript([lang])
        return t.fetch(), f"manually-created ({lang})"
    except NoTranscriptFound:
        pass

    # 2. Try auto-generated in requested language
    try:
        t = transcript_list.find_generated_transcript([lang])
        return t.fetch(), f"auto-generated ({lang})"
    except NoTranscriptFound:
        pass

    # 3. Fall back to whatever exists and translate it, if translation is available
    available = list(transcript_list)
    if not available:
        raise RuntimeError("No transcripts of any kind found for this video.")

    first = available[0]
    if first.is_translatable:
        translated = first.translate(lang)
        return translated.fetch(), f"translated from {first.language} -> {lang}"

    # 4. Last resort: just use whatever language is available, untranslated
    return first.fetch(), f"{first.language} (no {lang} version available)"


def format_transcript(fetched, include_timestamps: bool) -> str:
    lines = []
    for snippet in fetched:
        text = snippet.text.replace("\n", " ").strip()
        if not text:
            continue
        if include_timestamps:
            m, s = divmod(int(snippet.start), 60)
            h, m = divmod(m, 60)
            ts = f"[{h:02d}:{m:02d}:{s:02d}]" if h else f"[{m:02d}:{s:02d}]"
            lines.append(f"{ts} {text}")
        else:
            lines.append(text)
    return ("\n" if include_timestamps else " ").join(lines)


def main():
    parser = argparse.ArgumentParser(description="Fetch a YouTube transcript, formatted for pasting into Claude.")
    parser.add_argument("url", help="YouTube video URL or bare video ID")
    parser.add_argument("--timestamps", action="store_true", help="Keep timestamps on each line")
    parser.add_argument("--lang", default="en", help="Preferred language code (default: en)")
    parser.add_argument("--outdir", default=".", help="Where to save the output .txt file")
    args = parser.parse_args()

    try:
        video_id = extract_video_id(args.url)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    meta = get_metadata(video_id)

    try:
        fetched, source = get_transcript(video_id, lang=args.lang)
    except RuntimeError as e:
        sys.exit(f"Error: {e}")

    body = format_transcript(fetched, args.timestamps)
    word_count = len(body.split())
    approx_tokens = int(word_count * 1.3)  # rough rule of thumb

    header = (
        f"VIDEO: {meta['title']}\n"
        f"CHANNEL: {meta['author']}\n"
        f"URL: https://www.youtube.com/watch?v={video_id}\n"
        f"TRANSCRIPT SOURCE: {source}\n"
        f"---\n\n"
    )
    output = header + body

    safe_title = re.sub(r"[^A-Za-z0-9_-]+", "_", meta["title"])[:60].strip("_") or video_id
    outpath = Path(args.outdir) / f"{safe_title}_{video_id}.txt"
    outpath.write_text(output, encoding="utf-8")

    print(f"Saved: {outpath}")
    print(f"Source: {source}")
    print(f"~{word_count} words / ~{approx_tokens} tokens")
    if approx_tokens > 15000:
        print("This is long. Consider asking Claude to summarize it in sections, "
              "or splitting it, rather than dumping the whole thing in one message.")
    if "no en version available" in source or "no " + args.lang + " version" in source:
        print("Note: this wasn't available in your requested language and no translation existed; "
              "check the transcript quality before trusting it.")


if __name__ == "__main__":
    main()

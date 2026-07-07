#!/usr/bin/env python3
"""
chat_about_video.py — Fetch a YouTube video's transcript and open an
interactive chat with Claude about it, all locally.

This is the "talk to Claude about a video" front end. It reuses the
transcript-fetching logic from yt2claude.py, loads the transcript into
Claude as context (cached, so follow-up questions are cheap), and drops
you into a REPL where you can ask questions about what was said.

Run this on your OWN machine, not in a sandboxed web session — that's
what avoids the YouTube egress block, and it keeps your API key off any
remote environment.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python3 chat_about_video.py "<youtube_url>" [--lang en] [--model claude-opus-4-8]

Requires:
    pip install youtube-transcript-api requests anthropic
"""

import argparse
import os
import sys
from pathlib import Path

import anthropic

# Reuse the transcript pipeline that already exists in this repo.
from yt2claude import (
    extract_video_id,
    format_transcript,
    get_metadata,
    get_transcript,
)


def load_env_file(env_file: str) -> bool:
    """
    Load KEY=VALUE pairs from a .env file into the environment so the script
    can pull ANTHROPIC_API_KEY straight from the file instead of relying on a
    shell `export`. No third-party dependency — this parses the file itself.

    Looks for the file relative to the current directory first, then next to
    this script. Values found in the file take precedence for this run.
    Returns True if a file was found and read.
    """
    candidates = [Path(env_file), Path(__file__).resolve().parent / env_file]
    path = next((p for p in candidates if p.is_file()), None)
    if path is None:
        return False

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        # Allow an optional leading `export ` (common in .env files).
        if key.startswith("export "):
            key = key[len("export "):].strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ[key] = value
    return True


def build_system_prompt(meta: dict, transcript_text: str, source: str) -> list:
    """
    System prompt = instructions + the full transcript, as two blocks.

    The transcript block carries cache_control so Claude caches it after
    the first turn; every later question reuses that cached prefix at a
    fraction of the input cost instead of re-sending the whole transcript.
    """
    instructions = (
        "You are helping the user understand a YouTube video. You have the "
        "video's transcript below. Answer questions using only what the "
        "transcript supports.\n"
        f"This transcript came from: {source}. If it's auto-generated or "
        "translated, be a little cautious about exact names and technical "
        "terms.\n"
        "You only have the spoken words — you cannot see anything visual "
        "(slides, on-screen text, demos). If the user asks about something "
        "the transcript can't answer, say so plainly instead of guessing.\n"
        "Quote or point to specific parts of the transcript when it helps."
    )
    header = (
        f"VIDEO: {meta['title']}\n"
        f"CHANNEL: {meta['author']}\n"
        "--- TRANSCRIPT ---\n"
    )
    return [
        {"type": "text", "text": instructions},
        {
            "type": "text",
            "text": header + transcript_text,
            "cache_control": {"type": "ephemeral"},
        },
    ]


def main():
    parser = argparse.ArgumentParser(
        description="Chat with Claude about a YouTube video, locally."
    )
    parser.add_argument("url", help="YouTube video URL or bare video ID")
    parser.add_argument("--lang", default="en", help="Preferred caption language (default: en)")
    parser.add_argument("--model", default="claude-opus-4-8", help="Claude model ID")
    parser.add_argument("--env-file", default=".env", help="File to load env vars from (default: .env)")
    args = parser.parse_args()

    # Pull ANTHROPIC_API_KEY (and anything else) straight from the .env file.
    load_env_file(args.env_file)
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit(
            f"Error: ANTHROPIC_API_KEY not found. Put it in {args.env_file} as:\n"
            "  ANTHROPIC_API_KEY=sk-ant-...\n"
            f"(looked in the current directory and next to this script), or export it\n"
            "in your shell. Get a key at console.anthropic.com."
        )

    try:
        video_id = extract_video_id(args.url)
    except ValueError as e:
        sys.exit(f"Error: {e}")

    meta = get_metadata(video_id)

    try:
        fetched, source = get_transcript(video_id, lang=args.lang)
    except RuntimeError as e:
        # get_transcript already produces the egress-policy-aware message.
        sys.exit(f"Error: {e}")

    transcript_text = format_transcript(fetched, include_timestamps=False)
    word_count = len(transcript_text.split())

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment
    system = build_system_prompt(meta, transcript_text, source)
    messages = []

    print(f"\nLoaded: {meta['title']} — {meta['author']}")
    print(f"Transcript source: {source} (~{word_count} words)")
    print("Ask questions about the video. Ctrl-C or an empty line to quit.\n")

    while True:
        try:
            question = input("you > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            break

        messages.append({"role": "user", "content": question})

        print("claude > ", end="", flush=True)
        try:
            with client.messages.stream(
                model=args.model,
                max_tokens=4096,
                system=system,
                messages=messages,
            ) as stream:
                for text in stream.text_stream:
                    print(text, end="", flush=True)
                final = stream.get_final_message()
        except anthropic.AuthenticationError:
            # A bad key won't fix itself by retrying — stop with a clear message.
            sys.exit(
                "\nError: your ANTHROPIC_API_KEY was rejected (401 invalid x-api-key).\n"
                "Check that it's set in this terminal and pasted in full:\n"
                '  echo "${ANTHROPIC_API_KEY:0:14}"   # should start with sk-ant-\n'
                "Get or regenerate a key at console.anthropic.com (API keys), and make\n"
                "sure that workspace has API billing set up. Note: a Claude.ai Pro/Max\n"
                "subscription is separate from API access and does not include a key."
            )
        except anthropic.APIError as e:
            # Transient/other API errors: drop the unanswered turn and let them retry.
            print(f"\n[API error: {e}. Try again.]\n")
            messages.pop()
            continue
        print("\n")

        reply = "".join(b.text for b in final.content if b.type == "text")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()

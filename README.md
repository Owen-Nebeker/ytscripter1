---
name: yt-transcript
description: Use when the user pastes a YouTube URL (youtube.com/watch, youtu.be, /shorts/) and wants to discuss, summarize, or ask questions about that video. Fetches the video's transcript so Claude can answer as if it had watched/listened to it.
---

# YouTube Transcript Fetch

## What this does

Given a YouTube URL, fetches the video's caption transcript (preferring
human-made captions over auto-generated ones) and its title/channel, so
you can discuss the video's spoken content without the user having to
manually pull and paste a transcript.

## Limitation to keep in mind
This is transcript-only. It has no idea what's visually on screen (slides,
demos, on-screen text, who's speaking when). Treat it as strong for
podcasts/interviews/talking-head content, and weaker for anything where
the visuals carry meaning. If the user asks something the transcript
can't answer (e.g. "what did the slide say"), say so plainly rather than
guessing.

Keep in mind also that this requires a CLAUDE API KEY WHICH IS GENERALLY NOT FREE! Tokens can be purchased from [console.anthropic.com](console.anthropic.com).

Throw your API key into a .env file local to wherever you're running the script.

## Steps
1. Install the dependency if not already present:
   `pip install youtube-transcript-api requests --break-system-packages -q`
2. Run the script on the user's URL:
   `python3 yt2claude.py "<url>" --outdir /tmp`
3. If it exits with an error, report the error message to the user
   directly — don't retry silently or invent a workaround. Common causes:
   - Captions disabled by the uploader (no fix).
   - Network policy block: in sandboxed environments (e.g. Claude Code on
     the web) the egress proxy returns a 403/407 for youtube.com because it
     isn't on the environment's allowlist. The script now detects this and
     says so explicitly. This is NOT a YouTube problem and there is no code
     workaround — do not try to route around the proxy. Tell the user to run
     the script locally, or to have an admin allowlist youtube.com.
4. If it succeeds, read the resulting `.txt` file and use its contents to
   answer the user's questions about the video.
5. If the script reports the transcript is very long (its own output will
   say so), don't dump the whole raw transcript back into chat — summarize
   proactively and pull specific quotes only when the user asks about that
   part.
6. Note the "TRANSCRIPT SOURCE" line from the file: if it says
   "auto-generated" or "translated," mention that to the user once,
   since accuracy on names/technical terms is lower for those.

## Chatting with Claude about a video (local, via the Claude API)
`chat_about_video.py` is a standalone local front end: it fetches the
transcript (reusing the logic above) and opens an interactive Q&A loop
backed by the Claude API, so you can talk to Claude about the video
without pasting anything.

- Meant to run on your own machine, where YouTube is reachable and your
  API key stays off any remote environment.
- Setup: `pip install youtube-transcript-api requests anthropic`
- API key: put it in a `.env` file next to the script (or in the
  directory you run from):
  `ANTHROPIC_API_KEY=sk-ant-...`
  The script loads `.env` automatically — no `export` needed. (`.env` is
  git-ignored so the key never gets committed.) A shell `export` also
  still works, and `--env-file` points at a differently-named file.
- Run: `python3 chat_about_video.py "<url>"`
- The transcript is loaded into Claude's system prompt with prompt
  caching enabled, so follow-up questions reuse it cheaply instead of
  re-sending it each turn. Defaults to `claude-opus-4-8`; override with
  `--model`.

---
##name: yt-transcript

I love watching education, podcast-style YouTube videos, however these sorts of videos fall victim all too often to unbacked claims, logical fallacies, sneaky biases, etc.

This program automates a process I have already been doing naturally and from which I have great benefited, that is, copying a URL, using a 3rd party website to download the transcript, and then uploading the transcipt to Claude to help me think more critically about the topics. I beyond specific follow up questions, I like to ask Claude to analyze for logical fallacies, innacuracies, biases -- a broad fact check, if you will.
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
   captions disabled by uploader (no fix), or a network/access failure
   (tell the user this environment may not have access to fetch it, and
   they should try running the script locally instead).
4. If it succeeds, read the resulting `.txt` file and use its contents to
   answer the user's questions about the video.
5. If the script reports the transcript is very long (its own output will
   say so), don't dump the whole raw transcript back into chat — summarize
   proactively and pull specific quotes only when the user asks about that
   part.
6. Note the "TRANSCRIPT SOURCE" line from the file: if it says
   "auto-generated" or "translated," mention that to the user once,
   since accuracy on names/technical terms is lower for those.

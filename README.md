This program automates a process I have already been doing naturally and from which I have greatly benefited, that is, copying a URL, using a 3rd party website to download the transcript, and then uploading the transcript to Claude to help me think more critically about the topics. Beyond specific follow up questions, I like to ask Claude to analyze for logical fallacies, inaccuracies, biases -- a broad fact check, if you will.
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
2. Obtain an Anthropic API key from the link above, add credit to it. Format it in your .env as:
   `ANTHROPIC_API_KEY=xxxxxxxxxxxxx...`
3. Run the script on the user's URL:
   `python3 yt2claude.py "<url>"`
4. If it exits with an error, report the error message to the user
   directly — don't retry silently or invent a workaround. Common causes:
   captions disabled by uploader (no fix), or a network/access failure
   (tell the user this environment may not have access to fetch it, and
   they should try running the script locally instead).
5. If it succeeds, read the resulting `.txt` file and use its contents to
   answer the user's questions about the video.
6. If the script reports the transcript is very long (its own output will
   say so), don't dump the whole raw transcript back into chat — summarize
   proactively and pull specific quotes only when the user asks about that
   part.
7. Note the "TRANSCRIPT SOURCE" line from the file: if it says
   "auto-generated" or "translated," mention that to the user once,
   since accuracy on names/technical terms is lower for those.

GENERAL NOTES:

- ensure your .env is in the same folder as wherever you're running your script from.
- run the script in the terminal. make sure to navigate to the folder your using within the terminal before running the script.

## Optional: chat with Claude about a video
`chat_about_video.py` fetches the transcript and opens an interactive
Q&A loop with Claude in your terminal. It reads your key from the `.env`
file automatically. Run it locally:
`python3 chat_about_video.py "<url>"`

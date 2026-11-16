---
name: reel-diagnosis
description: Diagnose why an Instagram reel performed the way it did, and what to do differently next time. Works on winners and flops, on your own reels or anyone else's, from just a link. Use when the user shares a reel link, a video file or reel numbers and asks why it worked, why it flopped, what went wrong, what to learn from it, to analyse it, to break it down, to tear it down, or to diagnose it.
---

# Reel diagnosis

Anyone can watch a reel and say what is in it. This skill says why it performed the way it did, and what to do differently next time. Every reel gets the same treatment, whether it won or flopped.

The diagnosis has three parts, always in this order:

1. **Verdict.** Did it win or lose, against the account's own normal? Raw numbers mean nothing alone.
2. **Cause.** Which moments in the video caused that result, through which signal?
3. **Lesson.** What carries over to the next reel, what does not, and one test to run.

## The flow

A link is all the user should need to send. Do the work yourself and only ask when something truly cannot be got.

1. **Pull the evidence.** Run the script on the link (or on the file, if the user sent one). It downloads the reel with its sound, and reads likes, comments, date, caption and the latest comments from the post. Then it pulls the frames, cuts, pauses and the spoken transcript. Read `summary.md`, then look at `hook.jpg` and every `overview_N.jpg`.
2. **Get the plays and the baseline.** Read `references/inputs.md`. In short: open the account's Reels tab in a browser if you have one and read the play counts, then run the script with `--baseline` to get likes, comments and the medians. If you have no browser, ask for one screenshot of that tab. That is the only question in a normal run.
3. **Diagnose.** Read `references/method.md` and follow it step by step. Read `references/signals.md` for what each number means. Take single frames with `--at` wherever the numbers point (the reveal, the first product shot, a change of scene).
4. **Write the report.** Use `references/report.md` exactly. Nothing before it. After it, one line only: the offer to go deeper from `references/inputs.md`.

While you work, a one line update now and then is enough.

## Running the script

```bash
python3 <skill folder>/scripts/extract.py "<reel link or video file>"
python3 <skill folder>/scripts/extract.py "<reel link or video file>" --at 4.5,12   # extra single frames
```

Run it from a temporary working folder: it writes a `reel_<code>/` folder (or `<video>_reel/`) where it runs. A second run on the same link reuses the download.

The diagnosis always works from the downloaded file, with its sound. Never diagnose from a reel playing in a browser or from its cover image.

If the download fails (a private or removed reel, or Instagram refusing), ask the user for the video file: the exported file for their own reel, or a screen recording trimmed to the reel.

## Setup, first run only

The script needs ffmpeg, plus two free tools: yt-dlp to download the reel and faster-whisper to hear the voice. If the script stops with `SETUP NEEDED`, or `summary.md` says faster-whisper is not installed, ask once:

> First time setup: to download reels and hear their voice I need two free tools (about 1 GB on disk). Shall I install them?

On yes:

```bash
python3 -m venv ~/.reel-diagnosis && ~/.reel-diagnosis/bin/pip install yt-dlp faster-whisper
```

The script finds them on its own from then on. If ffmpeg is missing, offer `brew install ffmpeg` on a Mac (or the system's package manager) the same way. Never install anything without a yes.

On no: without yt-dlp, ask for the video file. Without faster-whisper, read the words from the burned-in captions and say in the report that the voice was not transcribed.

If code cannot run at all (for example in the Claude app), say the diagnosis will have no sound and estimated pacing, and on the user's OK work from their screenshots of the key moments. Say both limits in the report.

The transcript covers speech only. For the rest of the sound, use the audio name shown on the reel (original audio or a named track, and whether it is trending), the silence list in `summary.md`, and what the frames show.

## Rules

- **Judge against the account, not the internet.** A reel is a win or a loss relative to the same account's other reels. Never use generic engagement benchmarks.
- **Same format only.** Compare reels with reels. Carousels and photos are a different game.
- **Tie every cause to a moment.** A timestamp, what is on screen, and the signal it moved. A cause outside the video (distribution, timing, a change on the account) is tied to dates in the baseline instead. No timestamp or date, no claim.
- **Separate seeing from reading.** What is on screen is fact. Why it worked is your read, and carries a confidence: high, medium or low. Every cause, the leak and the lever all carry one. Say what data would confirm it.
- **No claim about what you did not see or hear.** If part of the reel was not checked, it cannot be a cause, the leak or the lever. Name it under "What would sharpen this" instead.
- **Paid reach is not earned reach.** Branded and paid partnership reels may have been boosted. Flag it whenever plays look out of line with likes and comments.
- **Trust captions over the transcript.** Whisper mishears. Where words are burned in on screen, quote those.
- **Never describe what the user can see for themselves** unless it explains a number.
- **Plain, short sentences.** No hype, no marketing lines, no em dashes, no hyphens joining clauses.

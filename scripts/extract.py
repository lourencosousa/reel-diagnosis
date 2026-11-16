#!/usr/bin/env python3
"""Pull the evidence out of one reel so Claude can diagnose it.

Needs ffmpeg and ffprobe. Downloading from a link needs yt-dlp, and the spoken
transcript needs faster-whisper, either in this Python or in ~/.reel-diagnosis
(the script switches to it on its own).

    python3 extract.py "https://www.instagram.com/reel/..."   # download, then full pass
    python3 extract.py reel.mp4                 # full pass on a file
    python3 extract.py reel.mp4 --at 4.5,12     # extra single frames at those seconds
    python3 extract.py reel.mp4 --no-transcript

Writes a folder next to the video (or --out) holding:
    summary.md        everything below in one readable page
    hook.jpg          first 3 seconds, 4 frames per second
    overview_N.jpg    the whole reel, 1 frame per second
    frame_<s>.jpg     single frames asked for with --at
"""

import argparse
import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path

COLS = 6
SHEET_ROWS = 6          # 36 seconds per overview sheet
TILE_W = 180
CUT_THRESHOLD = 0.25    # scene change score that counts as a cut
SILENCE_DB = -35
SILENCE_MIN = 0.4


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def need(tool):
    if not shutil.which(tool):
        sys.exit(f"{tool} is not installed. Install ffmpeg (it includes ffprobe) and run again.")


def probe(video):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "format=duration:stream=codec_type,width,height,r_frame_rate",
               "-of", "json", str(video)])
    data = json.loads(out.stdout or "{}")
    info = {"duration": float(data.get("format", {}).get("duration", 0)), "audio": False}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            num, _, den = s.get("r_frame_rate", "0/1").partition("/")
            info.update(width=s.get("width"), height=s.get("height"),
                        fps=round(float(num) / float(den or 1), 2) if float(den or 1) else None)
        if s.get("codec_type") == "audio":
            info["audio"] = True
    return info


def cuts(video):
    out = run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
               f"select='gt(scene,{CUT_THRESHOLD})',showinfo", "-f", "null", "-"])
    times = [float(t) for t in re.findall(r"pts_time:([0-9.]+)", out.stderr)]
    merged = []
    for t in times:                      # two hits within 0.2s are one cut
        if not merged or t - merged[-1] > 0.2:
            merged.append(round(t, 2))
    return merged


def silences(video):
    out = run(["ffmpeg", "-hide_banner", "-i", str(video), "-af",
               f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN}", "-f", "null", "-"])
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", out.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", out.stderr)]
    return [(round(s, 2), round(e, 2)) for s, e in zip(starts, ends)]


def sheet(video, path, start, length, fps, rows):
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(start), "-t", str(length), "-i", str(video),
         "-vf", f"fps={fps},scale={TILE_W}:-2,tile={COLS}x{rows}:padding=4:color=white",
         "-frames:v", "1", "-q:v", "3", str(path)])
    return path.exists()


def frame(video, path, t):
    run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(video),
         "-frames:v", "1", "-q:v", "2", str(path)])
    return path.exists()


def transcript(video, model_name):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None, "faster-whisper is not installed, so there is no spoken transcript (see Setup in SKILL.md)"
    model = WhisperModel(model_name, compute_type="int8")
    # vad_filter stays off: with music at voice level it can drop the whole voiceover.
    segments, info = model.transcribe(str(video), vad_filter=False, beam_size=5)
    # Over music alone Whisper invents short words ("You", "Thank you"): drop what it doubts.
    lines = [(round(s.start, 2), round(s.end, 2), s.text.strip()) for s in segments
             if s.text.strip() and s.no_speech_prob < 0.5 and s.avg_logprob > -1.0]
    return lines, f"faster-whisper {model_name}, language {info.language}"


def fmt(t):
    return f"{int(t // 60)}:{t % 60:05.2f}"


TOOLS_ENV = Path.home() / ".reel-diagnosis" / "bin" / "python"


def has(module):
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def use_tools_env():
    """If this Python lacks the tools but the skill's own environment exists, rerun inside it."""
    if has("faster_whisper") and has("yt_dlp"):
        return
    if TOOLS_ENV.exists() and Path(sys.executable).resolve() != TOOLS_ENV.resolve():
        os.execv(str(TOOLS_ENV), [str(TOOLS_ENV), str(Path(__file__).resolve()), *sys.argv[1:]])


def download(url, out):
    """Download a public reel with its sound, and keep what the post shows."""
    if not has("yt_dlp"):
        sys.exit("SETUP NEEDED: yt-dlp is not installed, so the reel cannot be downloaded (see Setup in SKILL.md).")
    import yt_dlp
    opts = {"outtmpl": str(out / "reel.%(ext)s"), "merge_output_format": "mp4",
            "format": "bv*+ba/b", "quiet": True, "no_warnings": True, "noprogress": True,
            "getcomments": True}
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:  # private reel, removed reel, rate limit
        sys.exit(f"DOWNLOAD FAILED: {str(e).strip()[:300]}")
    post = {k: info.get(k) for k in ("uploader", "channel", "upload_date", "timestamp", "like_count",
                                     "comment_count", "view_count", "description", "webpage_url")}
    post["comments"] = [{"text": (c.get("text") or "").strip(), "likes": c.get("like_count") or 0}
                        for c in (info.get("comments") or [])][:50]
    (out / "post.json").write_text(json.dumps(post, indent=2, ensure_ascii=False))
    return out / "reel.mp4", post


def plays_number(s):
    s = s.strip().lower().replace(",", "")
    mult = {"k": 1e3, "m": 1e6, "b": 1e9}.get(s[-1:], 1)
    return float(s[:-1] if s[-1:] in "kmb" else s) * mult


def baseline(pairs, this_code, out):
    """Likes and comments for the account's other reels, matched with the plays read off the Reels tab."""
    if not has("yt_dlp"):
        sys.exit("SETUP NEEDED: yt-dlp is not installed (see Setup in SKILL.md).")
    import yt_dlp
    rows = []
    with yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True, "skip_download": True}) as ydl:
        for pair in pairs.split(","):
            if "=" not in pair:
                continue
            code, plays = pair.split("=", 1)
            code = code.strip()
            row = {"code": code, "plays": plays_number(plays), "plays_shown": plays.strip()}
            try:
                i = ydl.extract_info(f"https://www.instagram.com/reel/{code}/", download=False)
                row.update(likes=i.get("like_count"), comments=i.get("comment_count"), date=i.get("upload_date"))
            except Exception:
                row.update(likes=None, comments=None, date=None)
            rows.append(row)

    def rate(r, k):
        return r[k] / r["plays"] if r.get(k) is not None and r[k] >= 0 and r["plays"] else None

    others = [r for r in rows if r["code"] != this_code]
    med_plays = statistics.median([r["plays"] for r in others]) if others else None
    lpp = [x for x in (rate(r, "likes") for r in others) if x is not None]
    cpp = [x for x in (rate(r, "comments") for r in others) if x is not None]
    med_l = statistics.median(lpp) if lpp else None
    med_c = statistics.median(cpp) if cpp else None

    md = ["# Baseline", "", "| Reel | Posted | Plays | Likes | Comments | Likes per play | Comments per play |",
          "|---|---|---|---|---|---|---|"]
    for r in rows:
        d = r.get("date") or ""
        l, c = rate(r, "likes"), rate(r, "comments")
        mark = " (this reel)" if r["code"] == this_code else ""
        md.append(f"| {r['code']}{mark} | {d[:4]}-{d[4:6]}-{d[6:]} | {r['plays_shown']} | {r.get('likes')} | "
                  f"{r.get('comments')} | {f'{l:.2%}' if l is not None else '?'} | {f'{c:.3%}' if c is not None else '?'} |")
    md += ["", f"Medians of the other {len(others)} reels: plays {med_plays:,.0f}" if med_plays else "No other reels given.",
           f"likes per play {med_l:.2%} ({len(lpp)} reels)" if med_l else "likes per play unknown",
           f"comments per play {med_c:.3%} ({len(cpp)} reels)" if med_c else "comments per play unknown"]
    me = next((r for r in rows if r["code"] == this_code), None)
    if me and med_plays:
        md += ["", "## This reel against the median",
               f"- Plays: {me['plays'] / med_plays:.1f}x"]
        if rate(me, "likes") is not None and med_l:
            md.append(f"- Likes per play: {rate(me, 'likes') / med_l:.1f}x")
        if rate(me, "comments") is not None and med_c:
            md.append(f"- Comments per play: {rate(me, 'comments') / med_c:.1f}x")
    md += ["", "Likes of -1 or None mean hidden or not available. Check the dates: leave out reels younger than 3 days."]
    (out / "baseline.md").write_text("\n".join(md) + "\n")
    print(out / "baseline.md")


def main():
    if "--no-transcript" not in sys.argv or any(x.startswith("http") for x in sys.argv):
        use_tools_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", help="a video file, or the reel's Instagram link")
    ap.add_argument("--out")
    ap.add_argument("--at", help="comma separated seconds for extra single frames")
    ap.add_argument("--model", default="small", help="whisper model: base, small, medium, large-v3")
    ap.add_argument("--no-transcript", action="store_true")
    ap.add_argument("--baseline", help="the account's reels as code=plays pairs read off the Reels tab, "
                                       "for example DeorJJENC7H=95.2k,DebzpEkqnLg=1.4m (include this reel)")
    a = ap.parse_args()

    need("ffmpeg"), need("ffprobe")
    post = None
    if a.video.startswith("http"):
        code = re.search(r"/(?:reel|reels|p)/([A-Za-z0-9_-]+)", a.video)
        out = Path(a.out).expanduser() if a.out else Path.cwd() / f"reel_{code.group(1) if code else 'download'}"
        out.mkdir(parents=True, exist_ok=True)
        if a.baseline:
            baseline(a.baseline, code.group(1) if code else "", out)
            return
        video = out / "reel.mp4"
        if video.exists() and (out / "post.json").exists():
            post = json.loads((out / "post.json").read_text())
        else:
            print("Downloading...", file=sys.stderr)
            video, post = download(a.video, out)
    else:
        video = Path(a.video).expanduser().resolve()
        if not video.exists():
            sys.exit(f"Video not found: {video}")
        out = Path(a.out).expanduser() if a.out else video.with_name(video.stem + "_reel")
        out.mkdir(parents=True, exist_ok=True)
        if a.baseline:
            baseline(a.baseline, "", out)
            return

    if a.at:
        for t in [float(x) for x in a.at.split(",") if x.strip()]:
            p = out / f"frame_{t:06.2f}.jpg"
            frame(video, p, t)
            print(p)
        return

    info = probe(video)
    dur = info["duration"]
    print(f"{video.name}: {dur:.1f}s, {info.get('width')}x{info.get('height')}", file=sys.stderr)

    cut_list = cuts(video)
    bounds = [0.0] + cut_list + [round(dur, 2)]
    shots = [round(b - a_, 2) for a_, b in zip(bounds, bounds[1:]) if b - a_ > 0.05]
    longest = max(range(len(shots)), key=lambda i: shots[i]) if shots else None

    sil = silences(video) if info["audio"] else []

    sheet(video, out / "hook.jpg", 0, 3, 4, 2)
    per_sheet = COLS * SHEET_ROWS
    sheets, start = [], 0
    while start < dur:
        n = len(sheets) + 1
        length = min(per_sheet, dur - start)
        rows = max(1, -(-int(length + 0.999) // COLS))
        p = out / f"overview_{n}.jpg"
        if sheet(video, p, start, length, 1, rows):
            sheets.append((p.name, start, start + length))
        start += per_sheet

    lines, note = (None, "skipped (--no-transcript)")
    if not a.no_transcript and info["audio"]:
        print("Transcribing...", file=sys.stderr)
        lines, note = transcript(video, a.model)
    elif not info["audio"]:
        note = "the video has no audio track"

    md = [f"# Evidence: {video.name}", "",
          "## Basics",
          f"- Length: {dur:.1f}s",
          f"- Size: {info.get('width')}x{info.get('height')}, {info.get('fps')} fps",
          f"- Audio track: {'yes' if info['audio'] else 'no'}", ""]
    if post:
        d = post.get("upload_date") or ""
        md += ["## The post (from the link)",
               f"- Account: {post.get('channel') or post.get('uploader')}",
               f"- Posted: {d[:4]}-{d[4:6]}-{d[6:]}" if d else "- Posted: unknown",
               f"- Likes: {post.get('like_count') if post.get('like_count') is not None else 'hidden or unknown'}",
               f"- Comments: {post.get('comment_count')}",
               f"- Plays: {post.get('view_count') or 'not available from the link: read them from the account Reels tab'}",
               f"- Caption: {(post.get('description') or '').strip()}", ""]
        com = post.get("comments") or []
        if com:
            tags = sum(1 for c in com if "@" in c["text"])
            only_emoji = sum(1 for c in com if c["text"] and not re.search(r"[A-Za-z0-9À-ɏ]", c["text"]))
            md += [f"## Comments ({len(com)} read, of {post.get('comment_count')})",
                   f"- Tagging a friend: {tags}. Emoji only: {only_emoji}.",
                   *(f"- {c['text'][:200]}" + (f" ({c['likes']} likes)" if c["likes"] else "") for c in com), ""]
    md += [
          "## Cuts and pacing",
          f"- Cuts: {len(cut_list)} (scene change above {CUT_THRESHOLD}). Hard cuts are reliable; slow dissolves and whip pans can be missed, so check the sheets.",
          f"- Cut times (s): {', '.join(str(c) for c in cut_list) or 'none'}",
          f"- Shots: {len(shots)}, average {statistics.mean(shots):.2f}s, median {statistics.median(shots):.2f}s" if shots else "- Shots: one continuous shot",
          f"- Cuts in the first 3s: {sum(1 for c in cut_list if c < 3)}"]
    if longest is not None:
        md.append(f"- Longest shot: {shots[longest]:.2f}s, from {bounds[longest]:.2f}s to {bounds[longest + 1]:.2f}s")
    windows = []
    for w in range(0, int(dur) + 1, 5):
        windows.append(f"{w}-{w + 5}s: {sum(1 for c in cut_list if w <= c < w + 5)}")
    md += [f"- Cuts per 5s: {' | '.join(windows)}", "",
           "## Silence (below " f"{SILENCE_DB} dB for {SILENCE_MIN}s or more)",
           *(f"- {fmt(s)} to {fmt(e)} ({e - s:.1f}s)" for s, e in sil)]
    if not sil:
        md.append("- none" if info["audio"] else "- no audio track")
    md += ["", "## Spoken transcript", f"Source: {note}. Whisper mishears names and odd words: where captions are burned in, trust the captions.", ""]
    if lines:
        md += [f"- [{fmt(s)} to {fmt(e)}] {t}" for s, e, t in lines]
        gaps = [(e1, s2) for (_, e1, _), (s2, _, _) in zip(lines, lines[1:]) if s2 - e1 >= 1.5]
        if lines[0][0] >= 1.5:
            gaps.insert(0, (0.0, lines[0][0]))
        md += ["", "Pauses in the voice of 1.5s or more (music may still play):"]
        md += [f"- {fmt(s)} to {fmt(e)} ({e - s:.1f}s)" for s, e in gaps] or ["- none"]
    else:
        md.append("- none")
    md += ["", "## Images",
           "- `hook.jpg`: the first 3 seconds, 4 frames per second. Read left to right, top to bottom: tile 1 is 0.00s, each tile adds 0.25s (row 2 starts at 1.50s).",
           *(f"- `{n}`: {s:.0f}s to {e:.0f}s, 1 frame per second, {COLS} per row. Tile k (counting from 0) is second {s:.0f} + k; row r starts at second {s:.0f} + {COLS}r."
             for n, s, e in sheets),
           "- For a closer look at any moment, run again with `--at <seconds>`."]
    (out / "summary.md").write_text("\n".join(md) + "\n")
    print(out / "summary.md")


if __name__ == "__main__":
    main()

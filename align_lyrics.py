#!/usr/bin/env python3
"""
Align this exact song's lyrics to the MP3 and write lyrics-data.js for the website.

Run on Windows by double-clicking ALIGN_LYRICS.bat. The first run downloads the
Whisper model; later runs reuse it.
"""

from __future__ import annotations

import json
import math
import re
import shutil
import sys
from pathlib import Path
from typing import Any

try:
    import torch
    import stable_whisper
except ImportError:
    print("Missing package. Run ALIGN_LYRICS.bat, not this file directly.")
    raise SystemExit(1)

ROOT = Path(__file__).resolve().parent
AUDIO_FILE = ROOT / "assets" / "Tabz Loverman.mp3"
SOURCE_FILE = ROOT / "lyrics-source.json"
OUTPUT_JS = ROOT / "lyrics-data.js"
OUTPUT_JSON = ROOT / "lyrics-alignment.json"
RAW_ALIGNMENT_JSON = ROOT / "raw-stable-ts-alignment.json"

# turbo is a good fit for a 4060 Ti. Change to "medium" if a lyric needs a retry.
MODEL_NAME = "turbo"
LANGUAGE = "en"


def read_field(item: Any, name: str, default: Any = None) -> Any:
    """Read a stable-ts value whether it is a dict or an object."""
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def clean_word(word: str) -> str:
    """Normalise punctuation only for matching, not for the displayed lyric."""
    word = word.replace("’", "'").replace("‘", "'").lower()
    return re.sub(r"[^a-z0-9']+", "", word)


def source_words(text: str) -> list[str]:
    return re.findall(r"\S+", text)


def finite_number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else fallback
    except (TypeError, ValueError):
        return fallback


def make_words_for_line(
    lyric_text: str,
    aligned_words: list[Any],
    segment_start: float,
    segment_end: float,
) -> list[dict[str, float | str]]:
    """Keep the user's exact lyric spelling while borrowing timings from stable-ts."""
    expected = source_words(lyric_text)
    available: list[dict[str, Any]] = []

    for word in aligned_words:
        raw_text = str(
            read_field(word, "word", read_field(word, "text", ""))
        ).strip()
        if not raw_text:
            continue
        start = finite_number(read_field(word, "start"), segment_start)
        end = finite_number(read_field(word, "end"), start + 0.12)
        available.append({"text": raw_text, "start": start, "end": max(end, start + 0.02)})

    if not available:
        # Safe fallback only when the aligner returns no individual words.
        duration = max(0.2, segment_end - segment_start)
        step = duration / max(1, len(expected))
        return [
            {"text": word, "start": round(segment_start + index * step, 3),
             "end": round(segment_start + (index + 1) * step, 3)}
            for index, word in enumerate(expected)
        ]

    output: list[dict[str, float | str]] = []
    cursor = 0
    last_end = segment_start

    for index, expected_word in enumerate(expected):
        wanted = clean_word(expected_word)
        match_index = None

        # Search a short distance ahead: the aligner may split/merge punctuation.
        for candidate_index in range(cursor, min(len(available), cursor + 7)):
            if clean_word(available[candidate_index]["text"]) == wanted:
                match_index = candidate_index
                break

        if match_index is None:
            match_index = min(cursor, len(available) - 1)

        timing = available[match_index]
        start = max(last_end, float(timing["start"]))
        end = max(start + 0.02, float(timing["end"]))
        output.append({"text": expected_word, "start": round(start, 3), "end": round(end, 3)})
        last_end = end
        cursor = min(match_index + 1, len(available))

    return output


def main() -> None:
    if not AUDIO_FILE.exists():
        print(f"Missing MP3: {AUDIO_FILE}")
        raise SystemExit(1)
    if not SOURCE_FILE.exists():
        print(f"Missing lyric source: {SOURCE_FILE}")
        raise SystemExit(1)
    if not shutil.which("ffmpeg"):
        print("FFmpeg is not installed or is not in PATH.")
        print("Install it, then run this file again. Windows command:")
        print("winget install --id Gyan.FFmpeg -e")
        raise SystemExit(1)

    source = json.loads(SOURCE_FILE.read_text(encoding="utf-8"))
    if not isinstance(source, list) or not source:
        print("lyrics-source.json is empty or invalid.")
        raise SystemExit(1)

    # A line break is intentional: original_split=True keeps every lyric line separate.
    transcript = "\n".join(str(item["text"]).strip() for item in source)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    load_options: dict[str, Any] = {"device": device}
    if device == "cpu":
        load_options["dq"] = True

    print(f"Using {device.upper()} with the {MODEL_NAME} model.")
    print("Aligning the actual MP3 to the supplied lyrics…")

    model = stable_whisper.load_model(MODEL_NAME, **load_options)
    result = model.align(
        str(AUDIO_FILE),
        transcript,
        language=LANGUAGE,
        original_split=True,
        fast_mode=True,
        token_step=442,
        max_word_dur=2.5,
        verbose=True,
    )

    # Keep the raw result for checking/fixing any stubborn sung word later.
    result.save_as_json(str(RAW_ALIGNMENT_JSON))
    segments = list(result.segments)

    if len(segments) != len(source):
        print(
            f"Warning: received {len(segments)} aligned lines for {len(source)} lyric lines. "
            "The script will still make a best-effort timing map."
        )

    cues: list[dict[str, Any]] = []
    last_end = 0.0

    for index, item in enumerate(source):
        segment = segments[index] if index < len(segments) else None
        segment_start = finite_number(read_field(segment, "start"), last_end)
        segment_end = finite_number(read_field(segment, "end"), segment_start + 1.0)
        aligned_words = list(read_field(segment, "words", []) or [])
        words = make_words_for_line(item["text"], aligned_words, segment_start, segment_end)

        start = float(words[0]["start"]) if words else segment_start
        end = float(words[-1]["end"]) if words else segment_end
        cues.append(
            {
                "section": item.get("section", "LYRICS"),
                "text": item["text"],
                "start": round(start, 3),
                "end": round(end, 3),
                "words": words,
            }
        )
        last_end = max(last_end, end)

    OUTPUT_JSON.write_text(json.dumps(cues, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUTPUT_JS.write_text(
        "/* Generated from Tabz Loverman.mp3 by align_lyrics.py. */\n"
        "window.LYRIC_CUES = "
        + json.dumps(cues, ensure_ascii=False, indent=2)
        + ";\n",
        encoding="utf-8",
    )

    first_start = cues[0]["start"] if cues else "?"
    print(f"Done. First lyric begins at {first_start}s.")
    print("Created lyrics-data.js — refresh the website and commit that file to GitHub.")


if __name__ == "__main__":
    main()

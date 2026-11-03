"""WebVTT captions for the walkthrough, timed from the audio itself.

Spoken lines are split at the pauses in each take (the pause nearest each sentence's share of
the speech becomes its boundary), then placed at the video time the take is heard. Background sound gets a [cue].
"""
import re

import numpy as np
import soundfile as sf


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.?!])\s+(?=[A-Z])", text.strip()) if s.strip()]


def speech_spans(path, count, floor_db=-42.0, frame=0.02, weights=None):
    """(start, end) seconds of `count` spoken sentences in a take. With `weights` (sentence
    lengths), each boundary is the pause (>= 0.12 s) nearest where that share of the speech ends,
    so a dramatic pause inside a sentence ("A voice... an answer...") is not taken for its end."""
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = audio.mean(axis=1)
    hop = int(rate * frame)
    rms = np.array([np.sqrt(np.mean(mono[i:i + hop] ** 2) + 1e-12) for i in range(0, len(mono), hop)])
    loud = 20 * np.log10(rms) > floor_db
    idx = np.flatnonzero(loud)
    if not len(idx):
        return []
    first, last = idx[0], idx[-1]
    gaps, run = [], None
    for i in range(first, last + 1):
        if not loud[i]:
            run = i if run is None else run
        elif run is not None:
            gaps.append((i - run, run, i))
            run = None
    if weights and count > 1:
        pauses = [g for g in gaps if g[0] * frame >= 0.12] or gaps
        total, cuts, acc = sum(weights), [], 0
        for weight in weights[:-1]:
            acc += weight
            target = first + (last - first) * acc / total
            free = [g for g in pauses if g not in cuts and (not cuts or g[1] > cuts[-1][1])]
            if free:
                cuts.append(min(free, key=lambda g: abs((g[1] + g[2]) / 2 - target)))
    else:
        cuts = sorted(sorted(gaps, reverse=True)[: max(0, count - 1)], key=lambda g: g[1])
    bounds, start = [], first
    for _length, gap_start, gap_end in cuts:
        bounds.append((start * frame, gap_start * frame))
        start = gap_end
    bounds.append((start * frame, (last + 1) * frame))
    return bounds


def stamp(seconds):
    h, rem = divmod(max(0.0, seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}"


def build(cues, path):
    cues = sorted(cues)
    # No two cues on screen at once: each ends just before the next begins.
    cues = [(start, min(end, cues[i + 1][0] - 0.04) if i + 1 < len(cues) else end, text)
            for i, (start, end, text) in enumerate(cues)]
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("WEBVTT\n\n")
        for number, (start, end, text) in enumerate(cues, 1):
            handle.write(f"{number}\n{stamp(start)} --> {stamp(end)}\n{text}\n\n")
    return cues


def spoken_cues(take_path, text, heard_at, heard_from, heard_for):
    """Cues for the part of a take heard from `heard_from` (s into the take) for `heard_for` s,
    starting at video time `heard_at`."""
    parts = sentences(text)
    spans = speech_spans(take_path, len(parts), weights=[len(p) for p in parts])
    cues = []
    for sentence, (a, b) in zip(parts, spans):
        a2, b2 = max(a, heard_from), min(b, heard_from + heard_for)
        if b2 - a2 < 0.4:              # not (or barely) heard in the cut
            continue
        cues.append((round(heard_at + a2 - heard_from, 3), round(heard_at + b2 - heard_from + 0.25, 3), sentence))
    return cues

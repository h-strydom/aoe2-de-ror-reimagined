"""AoE DE's voice-over for the mission intros and victory outros.

AoE DE narrates every mission's instructions (intro) and its victory and defeat texts: one MP3 per string id,
`aoe1de/data/Content/Voice Over/en/<id>.mp3` (copied by `setup`), the ids being the mission's text_ids. RoR plays a
mod's own sound by name from an intro's or outro's "Sound" when it's a .wem (aoe-agent-editor's aoe2ed.audio;
verified in game 2026-11-07), so each line becomes a mono 16-bit PCM .wem named `rorri_<campaign>_<n>_<kind>`.
The defeat lines aren't used: a campaign's intro file has no sequence for a lost mission.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import layout

VOICE_OVER = layout.AOE1DE / "data" / "Content" / "Voice Over" / "en"
KINDS = {"intro": "instructions", "victory": "victory"}       # sound kind -> the mission text it reads
RATE = 22050                                                   # Hz, mono: speech, about 2.6 MB a minute
PREFIX = "rorri"


@dataclass(frozen=True)
class Voice:
    sound: str           # the sound's name in the mod (its .wem file without the extension)
    source: Path         # AoE DE's MP3
    seconds: float


def sound_name(slug: str, number: int, kind: str) -> str:
    return f"{PREFIX}_{slug}_{number}_{kind}"


def seconds(path: Path) -> float:
    import soundfile
    info = soundfile.info(str(path))
    return round(info.frames / info.samplerate, 1)


def voice(slug: str, number: int, spec: dict, kind: str) -> Voice | None:
    """Mission `number`'s AoE DE voice line of `kind` (intro, victory), or None (no line, or not set up)."""
    sid = (spec.get("text_ids") or {}).get(KINDS[kind])
    path = VOICE_OVER / f"{sid}.mp3"
    if sid is None or not path.is_file():
        return None
    return Voice(sound_name(slug, number, kind), path, seconds(path))


def mission_voices(slug: str, specs: list[dict]) -> list[dict[str, Voice]]:
    """Per mission: kind -> its voice line, for the kinds it has."""
    return [{k: v for k in KINDS if (v := voice(slug, n, spec, k))} for n, spec in enumerate(specs, start=1)]


def wem(path: Path) -> bytes:
    """AoE DE's MP3 as a mono 16-bit PCM .wem at RATE."""
    import numpy as np
    import soundfile
    from aoe2ed.audio import pcm_wem
    data, rate = soundfile.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1)
    if rate != RATE:
        if rate == 2 * RATE:                                   # 44.1 kHz: average each pair (a gentle low-pass)
            mono = mono[: len(mono) // 2 * 2].reshape(-1, 2).mean(axis=1)
        else:
            t = np.arange(round(len(mono) * RATE / rate)) * rate / RATE
            mono = np.interp(t, np.arange(len(mono)), mono)
    pcm = (np.clip(mono, -1.0, 1.0) * 32767).astype("<i2").tobytes()
    return pcm_wem(pcm, RATE)


def sound_files(voices: list[dict[str, Voice]], cache: Path) -> dict[str, Path]:
    """Sound name -> its .wem, converted once into `cache` (redone when the MP3 is newer)."""
    out = {}
    cache.mkdir(parents=True, exist_ok=True)
    for mission in voices:
        for v in mission.values():
            dest = cache / f"{v.sound}.wem"
            if not dest.is_file() or dest.stat().st_mtime < v.source.stat().st_mtime:
                dest.write_bytes(wem(v.source))
            out[v.sound] = dest
    return out

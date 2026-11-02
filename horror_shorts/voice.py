"""2단계: 나레이션 TTS (edge-tts, 무료). 장면마다 mp3 + 문장 타이밍 json."""
from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
from pathlib import Path


def _patch_ca() -> None:
    # 사내 프록시 등 커스텀 CA 환경에서 edge-tts가 certifi만 보는 문제 우회
    ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
    if not ca and Path("/root/.ccr/ca-bundle.crt").exists():
        ca = "/root/.ccr/ca-bundle.crt"
    if ca:
        import certifi

        certifi.where = lambda: ca  # type: ignore[assignment]


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


SENT_RE = re.compile(r"[^.!?…]+[.!?…]*[\"'’”]?\s*")
TRIM = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.04,areverse,"
        "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.06,areverse")


def split_sentences(text: str) -> list[str]:
    parts = [p.strip() for p in SENT_RE.findall(text) if p.strip()]
    return parts or [text.strip()]


async def _tts(text: str, out_mp3: Path, voice: str, rate: str, pitch: str) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice, rate=rate, pitch=pitch).save(str(out_mp3))


def _ff(args: list[str]) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True)


def synth_scene(text: str, out_wav: Path, vcfg: dict, log=print) -> list[dict]:
    """문장마다 따로 TTS → 앞뒤 무음 제거 → 일정 간격으로 이어붙임. 문장 타이밍을 정확히 알 수 있다."""
    gap = vcfg.get("sentence_gap", 0.25)
    tmp = out_wav.parent / f"_{out_wav.stem}"
    tmp.mkdir(exist_ok=True)
    pieces, sentences, cur = [], [], 0.0
    for j, sent in enumerate(split_sentences(text)):
        mp3, wav = tmp / f"{j}.mp3", tmp / f"{j}.wav"
        for attempt in range(3):
            try:
                asyncio.run(_tts(sent.replace("*", ""), mp3, vcfg["voice"], vcfg["rate"], vcfg["pitch"]))
                break
            except Exception as e:  # 네트워크 일시 오류 재시도
                if attempt == 2:
                    raise
                log(f"  TTS 재시도 ({e})")
        _ff(["-i", str(mp3), "-af", TRIM, "-ar", "44100", "-ac", "2", str(wav)])
        d = probe_duration(wav)
        if pieces:
            cur += gap
        sentences.append({"start": round(cur, 3), "end": round(cur + d, 3), "text": sent})
        pieces.append(wav)
        cur += d
    lead = 0.08
    inputs = []
    for w in pieces:
        inputs += ["-i", str(w)]
    chain = "".join(
        f"[{i}:a]adelay={int((lead + s['start']) * 1000)}|{int((lead + s['start']) * 1000)}[d{i}];" for i, s in enumerate(sentences))
    mix = "".join(f"[d{i}]" for i in range(len(pieces)))
    _ff([*inputs, "-filter_complex", f"{chain}{mix}amix=inputs={len(pieces)}:normalize=0[a]", "-map", "[a]",
         "-t", f"{lead + cur + 0.05:.3f}", str(out_wav)])
    for s in sentences:
        s["start"] += lead
        s["end"] += lead
    for f in tmp.iterdir():
        f.unlink()
    tmp.rmdir()
    return sentences


def run(job: Path, script: dict, cfg: dict, log=print) -> list[dict]:
    _patch_ca()
    vcfg = cfg["voice"]
    vdir = job / "voice"
    vdir.mkdir(exist_ok=True)
    timing_path = vdir / "timing.json"
    if timing_path.exists():
        timing = json.loads(timing_path.read_text(encoding="utf-8"))
        if len(timing) == len(script["scenes"]) and all((vdir / t["file"]).exists() for t in timing):
            return timing

    timing = []
    for i, scene in enumerate(script["scenes"]):
        wav = vdir / f"scene_{i:02d}.wav"
        sents = synth_scene(scene["narration"], wav, vcfg, log)
        dur = probe_duration(wav)
        timing.append({"file": wav.name, "duration": dur, "sentences": sents})
        log(f"  {i + 1}/{len(script['scenes'])} [{scene['stage']}] {dur:.1f}초")
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=2), encoding="utf-8")
    return timing

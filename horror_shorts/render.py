"""4단계: 렌더 — 장면 클립(느린 줌·깜빡임·노이즈·오버레이) → 이어붙이기 → 사운드 믹스 → 자막."""
from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from . import audio_fx, overlays
from .config import FONTS_DIR
from .fonts import FAMILY, ensure_fonts
from .voice import probe_duration


def _ff(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", *args], check=True, cwd=cwd)


# ---------- 장면 길이 ----------
def scene_durations(script: dict, timing: list[dict], cfg: dict) -> list[float]:
    pad = cfg["voice"]["pad_seconds"]
    durs = []
    for i, (s, t) in enumerate(zip(script["scenes"], timing)):
        d = t["duration"] + pad
        if s["stage"] == "수칙발견":
            d += 0.6  # 종이를 볼 시간
        if s["stage"] == "규칙위반":
            d += 0.4
        if i == len(script["scenes"]) - 1:
            d += 1.2  # 여운
        durs.append(round(d, 3))
    return durs


# ---------- 카메라 움직임 ----------
def _zoompan(motion: str, frames: int, W: int, H: int, fps: int) -> str:
    N = max(frames - 1, 1)
    p = f"(on/{N})"
    cx = "(iw/2-(iw/zoom/2))"
    cy = "(ih/2-(ih/zoom/2))"
    if motion == "zoom_in":
        z, x, y = f"1.0+0.16*{p}", cx, cy
    elif motion == "zoom_out":
        z, x, y = f"1.18-0.16*{p}", cx, cy
    elif motion == "pan_left":
        z, x, y = "1.14", f"(iw-iw/zoom)*(1-{p})", cy
    elif motion == "pan_right":
        z, x, y = "1.14", f"(iw-iw/zoom)*{p}", cy
    elif motion == "shake":
        z = f"1.12+0.03*{p}"
        x = f"{cx}+iw*0.008*sin(on*2.3)+iw*0.004*sin(on*5.1)"
        y = f"{cy}+ih*0.006*sin(on*1.7+1)+ih*0.003*sin(on*4.3)"
    else:  # static (아주 느린 드리프트)
        z, x, y = f"1.04+0.02*{p}", cx, cy
    return f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={fps}"


def _scene_filter(scene: dict, dur: float, frames: int, W: int, H: int, fps: int, first: bool, last: bool,
                  loop_ending: bool, has_overlay: bool, clip_dur: float | None = None) -> str:
    stage = scene["stage"]
    if clip_dur:
        # Kling 영상: 장면 길이에 맞게 최대 1.6배까지 느리게, 그래도 모자라면 마지막 프레임 유지
        k = min(max(dur / clip_dur, 1.0), 1.6)
        vf = [f"setpts={k:.4f}*PTS", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos",
              f"crop={W}:{H}", f"fps={fps}", f"tpad=stop_mode=clone:stop_duration={dur:.2f}"]
        if scene["motion"] == "shake" or stage == "규칙위반":
            vf.append(f"crop={W - 40}:{H - 70}:20+16*sin(n*2.3):35+14*sin(n*1.7+1),scale={W}:{H}")
    else:
        vf = [f"scale={int(W * 1.5)}:{int(H * 1.5)}:flags=lanczos", _zoompan(scene["motion"], frames, W, H, fps)]
    # 형광등 깜빡임: 가끔 확 어두워지고, 미세하게 떨림
    drop = 0.08 if stage == "규칙위반" else 0.025
    vf.append(f"eq=brightness='if(lt(random(1),{drop}),-0.22,0)+0.015*sin(t*11)':contrast=1.08:saturation=0.75:eval=frame")
    if stage == "규칙위반":
        vf.append("rgbashift=rh=9:bh=-9:gv=3")
        vf.append("noise=alls=34:allf=t+u")
    else:
        vf.append("noise=alls=20:allf=t+u")
    vf.append("vignette=angle=PI/4.2")
    if first:
        vf.append("fade=t=in:st=0:d=0.5")
    if last and not loop_ending:
        vf.append(f"fade=t=out:st={max(0.0, dur - 0.9):.2f}:d=0.9")
    chain = ",".join(vf)
    if has_overlay:
        return (f"[0:v]{chain}[bg];[1:v]format=rgba,fade=t=in:st=0.12:d=0.35:alpha=1[ov];"
                f"[bg][ov]overlay=0:0:format=auto,format=yuv420p[v]")
    return f"[0:v]{chain},format=yuv420p[v]"


def build_overlays(job: Path, script: dict, meta: dict, size: tuple[int, int]) -> dict[int, Path]:
    odir = job / "overlays"
    odir.mkdir(exist_ok=True)
    rules = {r["number"]: r for r in script["rules"]}
    out = {}
    for i, s in enumerate(script["scenes"]):
        img = None
        if s["stage"] == "수칙발견":
            hand = script.get("handwritten_rule") or (script["rules"][-1]["number"] if meta.get("ending") == "twist" else None)
            img = overlays.rulebook(size, script["rulebook_title"], script["rules"], meta["world"], handwritten=hand)
        elif s["stage"] in ("수칙연출", "규칙위반") and s.get("rule_number") in rules:
            n = s["rule_number"]
            img = overlays.rule_card(size, n, rules[n]["text"], violated=s["stage"] == "규칙위반")
        if img is not None:
            p = odir / f"scene_{i:02d}.png"
            img.save(p)
            out[i] = p
    return out


def render_clips(job: Path, script: dict, meta: dict, durs: list[float], cfg: dict, log=print) -> list[Path]:
    rc = cfg["render"]
    W, H, fps = rc["width"], rc["height"], rc["fps"]
    cdir = job / "clips"
    cdir.mkdir(exist_ok=True)
    ovs = build_overlays(job, script, meta, (W, H))
    n = len(script["scenes"])
    loop_ending = meta.get("ending") == "loop"

    def one(i: int) -> Path:
        s, dur = script["scenes"][i], durs[i]
        frames = int(round(dur * fps))
        out = cdir / f"scene_{i:02d}.mp4"
        vid = job / "videos" / f"scene_{i:02d}.mp4"
        clip_dur = None
        if vid.exists():
            clip_dur = probe_duration(vid)
            args = ["-an", "-i", str(vid)]
        else:
            args = ["-i", str(job / "images" / f"scene_{i:02d}.png")]
        if i in ovs:
            args += ["-loop", "1", "-t", f"{dur:.3f}", "-i", str(ovs[i])]
        fc = _scene_filter(s, dur, frames, W, H, fps, i == 0, i == n - 1, loop_ending, i in ovs, clip_dur)
        args += ["-filter_complex", fc, "-map", "[v]", "-frames:v", str(frames), "-r", str(fps),
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", str(rc["crf"]), "-pix_fmt", "yuv420p", str(out)]
        _ff(args)
        return out

    with ThreadPoolExecutor(max_workers=3) as ex:
        clips = list(ex.map(one, range(n)))
    nv = sum((job / "videos" / f"scene_{i:02d}.mp4").exists() for i in range(n))
    log(f"  장면 클립 {n}개 완료 (Kling 영상 {nv}개 · 정지 이미지 {n - nv}개)")
    return clips


# ---------- 사운드 ----------
def mix_audio(job: Path, script: dict, timing: list[dict], durs: list[float], cfg: dict) -> Path:
    rc = cfg["render"]
    adir = job / "audio"
    adir.mkdir(exist_ok=True)
    total = sum(durs)
    drone = audio_fx.make_drone(adir / "drone.wav", total)

    inputs: list[str] = []
    filters: list[str] = []
    labels: list[str] = []
    # 나레이션: 장면마다 길이에 맞게 무음 패딩 후 이어붙이기
    for i, (t, d) in enumerate(zip(timing, durs)):
        inputs += ["-i", str(job / "voice" / t["file"])]
        filters.append(f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,apad=whole_dur={d:.3f}[n{i}]")
    nar = "".join(f"[n{i}]" for i in range(len(timing)))
    filters.append(f"{nar}concat=n={len(timing)}:v=0:a=1[nar]")
    labels.append("[nar]")
    k = len(timing)
    inputs += ["-i", str(drone)]
    filters.append(f"[{k}:a]volume={rc['bgm_volume']},atrim=0:{total:.3f}[bgm]")
    labels.append("[bgm]")
    k += 1
    start = 0.0
    for i, (s, d) in enumerate(zip(script["scenes"], durs)):
        if s["sfx"] != "none":
            p = audio_fx.make_sfx(s["sfx"], adir / f"sfx_{s['sfx']}.wav")
            inputs += ["-i", str(p)]
            ms = int(start * 1000) + (150 if s["stage"] == "규칙위반" else 0)
            filters.append(f"[{k}:a]volume={rc['sfx_volume']},adelay={ms}|{ms}[s{i}]")
            labels.append(f"[s{i}]")
            k += 1
        start += d
    filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=first,"
                   f"loudnorm=I={rc['loudness']}:TP=-1.5:LRA=11,aresample=44100[mix]")
    out = adir / "mix.wav"
    _ff([*inputs, "-filter_complex", ";".join(filters), "-map", "[mix]", "-t", f"{total:.3f}", str(out)])
    return out


# ---------- 자막 ----------
def _ass_time(t: float) -> str:
    cs = int(round(t * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _srt_time(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _chunks(text: str, max_chars: int = 15) -> list[str]:
    """자막 한 화면 = 최대 2줄. 긴 문장은 어절 단위로 쪼갠다."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len((cur + " " + w).strip()) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return ["\\N".join(lines[i:i + 2]) for i in range(0, len(lines), 2)]


def subtitle_events(script: dict, timing: list[dict], durs: list[float]) -> list[tuple[float, float, str]]:
    events = []
    offset = 0.0
    for s, t, d in zip(script["scenes"], timing, durs):
        for sent in t["sentences"]:
            parts = _chunks(sent["text"])
            span = max(sent["end"] - sent["start"], 0.3)
            weights = [max(len(p.replace("\\N", "")), 1) for p in parts]
            cur = sent["start"]
            for p, w in zip(parts, weights):
                dt = span * w / sum(weights)
                events.append((offset + cur, offset + cur + dt, p))
                cur += dt
        offset += d
    # 다음 자막과 겹치지 않게 정리
    fixed = []
    for i, (a, b, txt) in enumerate(events):
        if i + 1 < len(events):
            b = min(b + 0.15, events[i + 1][0] - 0.02)
        fixed.append((a, max(b, a + 0.2), txt))
    return fixed


def write_subtitles(job: Path, script: dict, timing: list[dict], durs: list[float], cfg: dict) -> Path:
    rc = cfg["render"]
    W, H = rc["width"], rc["height"]
    ev = subtitle_events(script, timing, durs)
    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,{FAMILY['gothic']},66,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,5,2,2,70,70,560,1
Style: Cap,{FAMILY['myeongjo']},96,&H002A2AE0,&H002A2AE0,&H00000000,&H00000000,0,0,0,0,100,100,2,0,1,5,0,8,60,60,290,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [head]
    for a, b, txt in ev:
        lines.append(f"Dialogue: 0,{_ass_time(a)},{_ass_time(b)},Sub,,0,0,0,,{txt}\n")
    # 강조 문구: 수칙 카드/종이가 없는 장면에만 (기상·상황파악·끝)
    offset = 0.0
    for s, d in zip(script["scenes"], durs):
        cap = (s.get("caption") or "").strip()
        if cap and s["stage"] in ("기상", "상황파악", "끝"):
            lines.append(f"Dialogue: 1,{_ass_time(offset + 0.1)},{_ass_time(offset + min(d, 2.6))},Cap,,0,0,0,"
                         f",{{\\fad(200,300)}}{cap}\n")
        offset += d
    ass = job / "subtitles.ass"
    ass.write_text("".join(lines), encoding="utf-8")
    srt = job / "subtitles.srt"
    srt.write_text("".join(f"{i}\n{_srt_time(a)} --> {_srt_time(b)}\n{t.replace(chr(92) + 'N', chr(10))}\n\n"
                           for i, (a, b, t) in enumerate(ev, 1)), encoding="utf-8")
    return ass


def run(job: Path, script: dict, meta: dict, timing: list[dict], cfg: dict, log=print) -> Path:
    ensure_fonts()
    rc = cfg["render"]
    durs = scene_durations(script, timing, cfg)
    (job / "durations.json").write_text(json.dumps(durs), encoding="utf-8")
    clips = render_clips(job, script, meta, durs, cfg, log)
    lst = job / "clips" / "list.txt"
    lst.write_text("".join(f"file '{c.name}'\n" for c in clips), encoding="utf-8")
    _ff(["-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy", "../video_raw.mp4"], cwd=job / "clips")
    log("  사운드 믹스")
    mix = mix_audio(job, script, timing, durs, cfg)
    write_subtitles(job, script, timing, durs, cfg)
    log("  자막 입히고 최종 인코딩")
    _ff(["-i", "video_raw.mp4", "-i", str(mix.relative_to(job)),
         "-vf", f"ass=subtitles.ass:fontsdir={FONTS_DIR}",
         "-c:v", "libx264", "-preset", "medium", "-crf", str(rc["final_crf"]),
         "-maxrate", rc["max_bitrate"], "-bufsize", str(int(rc["max_bitrate"].rstrip("M")) * 2) + "M", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", "final.mp4"], cwd=job)
    total = sum(durs)
    log(f"  최종 영상 {total:.1f}초 → final.mp4")
    return job / "final.mp4"

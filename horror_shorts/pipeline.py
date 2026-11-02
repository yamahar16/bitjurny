"""단계 실행기. 각 단계는 결과물이 있으면 건너뛰므로 중간에 멈춰도 이어서 돌릴 수 있다."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

from . import images, publish, render, script as script_mod, videos, voice
from .config import JOBS_DIR

STEPS = ["script", "voice", "images", "videos", "render", "seo", "thumbnail", "upload"]


def new_job(meta: dict) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    job = JOBS_DIR / f"{stamp}-{meta['place']}"
    job.mkdir(parents=True, exist_ok=False)
    (job / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return job


def _clear(job: Path, step: str) -> None:
    """--force 로 특정 단계부터 다시 만들 때 이전 결과 삭제."""
    targets = {
        "script": ["script.json"],
        "voice": ["voice"],
        "images": ["images"],
        "videos": ["videos"],
        "render": ["clips", "overlays", "audio", "video_raw.mp4", "final.mp4"],
        "thumbnail": ["thumbnail.jpg"],
    }.get(step, [])
    import shutil

    for t in targets:
        p = job / t
        if p.is_dir():
            shutil.rmtree(p)
        elif p.exists():
            p.unlink()


def run(job: Path, cfg: dict, upload: bool = False, force: str | None = None, log=print) -> Path:
    meta = json.loads((job / "meta.json").read_text(encoding="utf-8"))
    if force:
        # 다시 만들 단계 + 그 결과에 의존하는 단계만 지운다 (voice를 다시 해도 이미지는 유지)
        downstream = {"script": STEPS, "voice": ["voice", "render", "thumbnail"],
                      "images": ["images", "videos", "render", "thumbnail"],
                      "videos": ["videos", "render"], "render": ["render", "thumbnail"]}
        for s in downstream.get(force, [force]):
            _clear(job, s)

    def step(name: str):
        log(f"▶ {name}")
        return time.time()

    t = step("script")
    sc = script_mod.run(job, meta, cfg)
    est = script_mod.estimate_seconds(sc)
    log(f"  「{sc['title']}」 장면 {len(sc['scenes'])}개 · 예상 {est:.0f}초 ({time.time() - t:.0f}초)")

    t = step("voice")
    timing = voice.run(job, sc, cfg, log)
    log(f"  나레이션 합계 {sum(x['duration'] for x in timing):.1f}초 ({time.time() - t:.0f}초)")

    t = step("images")
    images.run(job, sc, meta, cfg, log)
    log(f"  ({time.time() - t:.0f}초)")

    t = step("videos")
    durs = render.scene_durations(sc, timing, cfg)
    videos.run(job, sc, durs, meta, cfg, log)
    log(f"  ({time.time() - t:.0f}초)")

    t = step("render")
    if not (job / "final.mp4").exists():
        render.run(job, sc, meta, timing, cfg, log)
    else:
        log("  final.mp4 있음 — 건너뜀")
    log(f"  ({time.time() - t:.0f}초)")

    step("seo")
    data = publish.seo(job, sc, meta)
    log(f"  제목: {data['title']}")

    step("thumbnail")
    publish.thumbnail(job, sc, cfg)
    log("  thumbnail.jpg")

    if upload:
        step("upload")
        url = publish.upload(job, cfg, log)
        log(f"  ✅ 업로드 완료 ({cfg['upload']['privacy']}): {url}")
    return job / "final.mp4"

"""3.5단계: 장면 영상 (Kling image-to-video). 기본은 '모든 장면을 영상으로'.

provider
  kling   : Kling 공식 API (KLING_ACCESS_KEY / KLING_SECRET_KEY)
  manual  : videos/scene_XX.mp4 를 직접 넣기 — Claude Code 세션이 Kling 커넥터(MCP)로 만들어 넣는 방식.
            requests.json 에 장면별 첫 프레임 이미지·프롬프트·길이를 적어 둔다.
  none    : 영상 없이 정지 이미지 + 카메라 효과만

영상이 없는 장면은 자동으로 정지 이미지 연출로 대체되므로, 일부만 영상이어도 렌더된다.
"""
from __future__ import annotations

import base64
import json
import math
import os
import time
from pathlib import Path


class NeedsVideos(RuntimeError):
    pass


def clip_seconds(scene_dur: float, options: list[int]) -> int:
    """장면 길이를 덮는 가장 짧은 Kling 길이. 없으면 가장 긴 것 (렌더에서 최대 1.6배까지 느리게 늘린다)."""
    for o in sorted(options):
        if o >= scene_dur:
            return o
    return max(options)


def requests_for(script: dict, durs: list[float], vcfg: dict) -> list[dict]:
    pick = vcfg.get("scenes", "all")
    out = []
    for i, (s, d) in enumerate(zip(script["scenes"], durs)):
        if pick != "all" and s["stage"] not in pick:
            continue
        prompt = s.get("video_prompt") or f"slow subtle camera push in, light flickers, eerie stillness, {s['image_prompt'][:300]}"
        out.append({
            "file": f"scene_{i:02d}.mp4",
            "first_frame": f"images/scene_{i:02d}.png",
            "prompt": prompt,
            "duration": clip_seconds(d, vcfg["durations"]),
            "scene_seconds": round(d, 2),
            "stage": s["stage"],
        })
    return out


# ---------------- Kling API ----------------
def _kling_i2v(req: dict, job: Path, kcfg: dict, out: Path) -> None:
    import requests

    from .images import _kling_token

    base = kcfg["base_url"].rstrip("/")
    img_b64 = base64.b64encode((job / req["first_frame"]).read_bytes()).decode()
    body = {"model_name": kcfg["video_model"], "mode": kcfg.get("mode", "std"), "image": img_b64,
            "prompt": req["prompt"][:2500], "duration": str(req["duration"]),
            "negative_prompt": "text, watermark, subtitles, cartoon, bright cheerful"}
    r = requests.post(f"{base}/v1/videos/image2video", json=body, timeout=120,
                      headers={"Authorization": f"Bearer {_kling_token()}", "Content-Type": "application/json"})
    r.raise_for_status()
    data = r.json()
    if data.get("code") not in (0, None):
        raise RuntimeError(f"Kling 오류: {data}")
    task_id = data["data"]["task_id"]
    for _ in range(240):
        time.sleep(8)
        q = requests.get(f"{base}/v1/videos/image2video/{task_id}", timeout=60,
                         headers={"Authorization": f"Bearer {_kling_token()}"}).json()
        st = q["data"]["task_status"]
        if st == "succeed":
            out.write_bytes(requests.get(q["data"]["task_result"]["videos"][0]["url"], timeout=300).content)
            return
        if st == "failed":
            raise RuntimeError(f"Kling 영상 실패: {q['data'].get('task_status_msg')}")
    raise TimeoutError(f"Kling 영상 시간 초과: {task_id}")


def run(job: Path, script: dict, durs: list[float], meta: dict, cfg: dict, log=print) -> int:
    vcfg = cfg["videos"]
    provider = meta.get("videos") or vcfg["provider"]
    vdir = job / "videos"
    vdir.mkdir(exist_ok=True)
    reqs = requests_for(script, durs, vcfg)
    (vdir / "requests.json").write_text(json.dumps(reqs, ensure_ascii=False, indent=2), encoding="utf-8")
    missing = [r for r in reqs if not (vdir / r["file"]).exists()]
    have = len(reqs) - len(missing)
    if provider == "none" or not missing:
        log(f"  영상 {have}/{len(script['scenes'])}개 장면")
        return have

    if provider == "kling" and os.environ.get("KLING_ACCESS_KEY") and os.environ.get("KLING_SECRET_KEY"):
        from concurrent.futures import ThreadPoolExecutor

        def one(r):
            _kling_i2v(r, job, cfg["images"]["kling"], vdir / r["file"])
            log(f"  Kling 영상: {r['file']} ({r['duration']}초)")

        with ThreadPoolExecutor(max_workers=vcfg.get("parallel", 4)) as ex:
            list(ex.map(one, missing))
        return len(reqs)

    total = sum(r["duration"] for r in missing)
    msg = (f"영상 {len(missing)}개가 필요합니다 (합계 {total}초). videos/requests.json 대로 Kling image-to-video를 만들어 "
           f"videos/scene_XX.mp4 로 넣은 뒤 다시 run 하세요. 영상 없이 진행하려면 --videos none")
    if vcfg.get("require", True):
        raise NeedsVideos(msg)
    log("  ⚠ " + msg)
    return have

"""3단계: 장면 이미지.

provider
  procedural : 무료 자체 생성 (테스트·초안용)
  kling      : Kling 공식 API (KLING_ACCESS_KEY / KLING_SECRET_KEY 환경변수)
  manual     : images/scene_XX.png 를 직접 넣기 (Claude Code의 Kling/Higgsfield MCP로 생성 등)
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from PIL import Image

from . import procedural
from .presets import PLACES


class NeedsImages(RuntimeError):
    pass


def _cover(img: Image.Image, W: int, H: int) -> Image.Image:
    r = max(W / img.width, H / img.height)
    img = img.resize((round(img.width * r), round(img.height * r)), Image.LANCZOS)
    x, y = (img.width - W) // 2, (img.height - H) // 2
    return img.crop((x, y, x + W, y + H))


def targets(script: dict) -> list[tuple[str, str]]:
    """(파일명, 프롬프트) 목록. 장면별 + 썸네일."""
    items = [(f"scene_{i:02d}.png", s["image_prompt"]) for i, s in enumerate(script["scenes"])]
    items.append(("thumbnail_bg.png", script["thumbnail_prompt"]))
    return items


# ---------------- Kling API ----------------
def _kling_token() -> str:
    import jwt

    ak, sk = os.environ["KLING_ACCESS_KEY"], os.environ["KLING_SECRET_KEY"]
    now = int(time.time())
    return jwt.encode({"iss": ak, "exp": now + 1800, "nbf": now - 5}, sk, algorithm="HS256",
                      headers={"alg": "HS256", "typ": "JWT"})


def _kling_generate(prompt: str, kcfg: dict, out: Path, log) -> None:
    import requests

    base = kcfg["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {_kling_token()}", "Content-Type": "application/json"}
    body = {"model_name": kcfg["model"], "prompt": prompt[:2500], "aspect_ratio": kcfg["aspect_ratio"], "n": 1}
    r = requests.post(f"{base}/v1/images/generations", headers=headers, json=body, timeout=60)
    r.raise_for_status()
    data = r.json()
    if data.get("code") not in (0, None):
        raise RuntimeError(f"Kling 오류: {data}")
    task_id = data["data"]["task_id"]
    for _ in range(120):
        time.sleep(5)
        headers["Authorization"] = f"Bearer {_kling_token()}"
        q = requests.get(f"{base}/v1/images/generations/{task_id}", headers=headers, timeout=60).json()
        st = q["data"]["task_status"]
        if st == "succeed":
            url = q["data"]["task_result"]["images"][0]["url"]
            out.write_bytes(requests.get(url, timeout=120).content)
            return
        if st == "failed":
            raise RuntimeError(f"Kling 생성 실패: {q['data'].get('task_status_msg')}")
    raise TimeoutError(f"Kling 작업 시간 초과: {task_id}")


def run(job: Path, script: dict, meta: dict, cfg: dict, log=print) -> None:
    rc = cfg["render"]
    W, H = rc["width"], rc["height"]
    idir = job / "images"
    idir.mkdir(exist_ok=True)
    provider = meta.get("images") or cfg["images"]["provider"]
    items = targets(script)
    (idir / "prompts.json").write_text(
        json.dumps([{"file": f, "prompt": p} for f, p in items], ensure_ascii=False, indent=2), encoding="utf-8")

    missing = [(f, p) for f, p in items if not (idir / f).exists()]
    if not missing:
        log("  이미지 모두 있음")

    place = PLACES.get(meta["place"], {"layout": "corridor", "tint": (160, 180, 170)})
    if not missing:
        pass
    elif provider == "procedural":
        for f, p in missing:
            idx = int(f[6:8]) if f.startswith("scene_") else len(script["scenes"]) - 2
            stage = script["scenes"][idx]["stage"] if f.startswith("scene_") else "규칙위반"
            img = procedural.render_scene(p, place["layout"], place["tint"], procedural.seed_for(p, idx), stage, (W, H))
            img.save(idir / f)
            log(f"  생성: {f}")
    elif provider == "kling":
        if not (os.environ.get("KLING_ACCESS_KEY") and os.environ.get("KLING_SECRET_KEY")):
            raise NeedsImages("KLING_ACCESS_KEY / KLING_SECRET_KEY 환경변수가 필요합니다.")
        for f, p in missing:
            raw = idir / f"raw_{f}"
            _kling_generate(p, cfg["images"]["kling"], raw, log)
            _cover(Image.open(raw).convert("RGB"), W, H).save(idir / f)
            log(f"  Kling: {f}")
    else:  # manual — 썸네일 배경은 없으면 규칙위반 장면으로 대체하므로 필수 아님
        missing = [(f, p) for f, p in missing if f != "thumbnail_bg.png"]
        if missing:
            names = "\n".join(f"  - {f}: {p[:90]}…" for f, p in missing)
            raise NeedsImages(f"images/ 폴더에 아래 이미지를 넣은 뒤 다시 run 하세요 (prompts.json 참고):\n{names}")

    # 크기 통일 (manual/kling 이미지가 다른 크기일 수 있음)
    for f, _ in items:
        p = idir / f
        if not p.exists():
            continue
        im = Image.open(p)
        if im.size != (W, H):
            _cover(im.convert("RGB"), W, H).save(p)

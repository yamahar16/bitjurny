"""한글 폰트 준비 (Google Fonts, SIL OFL 라이선스). 처음 실행 때 자동 다운로드."""
from __future__ import annotations

from pathlib import Path

import requests

from .config import FONTS_DIR

_BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl"
FONTS = {
    "gothic": ("NanumGothic-ExtraBold.ttf", f"{_BASE}/nanumgothic/NanumGothic-ExtraBold.ttf"),
    "myeongjo": ("NanumMyeongjo-ExtraBold.ttf", f"{_BASE}/nanummyeongjo/NanumMyeongjo-ExtraBold.ttf"),
    "pen": ("NanumPenScript-Regular.ttf", f"{_BASE}/nanumpenscript/NanumPenScript-Regular.ttf"),
}
# ASS 자막에서 쓰는 폰트 패밀리 이름
FAMILY = {"gothic": "NanumGothicExtraBold", "myeongjo": "NanumMyeongjoExtraBold", "pen": "Nanum Pen"}


def ensure_fonts() -> dict[str, Path]:
    FONTS_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for key, (name, url) in FONTS.items():
        p = FONTS_DIR / name
        if not p.exists() or p.stat().st_size < 10_000:
            r = requests.get(url, timeout=60)
            r.raise_for_status()
            p.write_bytes(r.content)
        paths[key] = p
    return paths


def font_path(key: str) -> Path:
    return ensure_fonts()[key]

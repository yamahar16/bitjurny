"""설정 로드 (config.yaml이 있으면 덮어쓴다)."""
from __future__ import annotations

import copy
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
PKG = Path(__file__).resolve().parent
ASSETS = PKG / "assets"
FONTS_DIR = ASSETS / "fonts"
JOBS_DIR = ROOT / "jobs"

DEFAULTS: dict = {
    "script": {
        "model": "claude-opus-5-5",
        "effort": "high",
        "rules": 4,
        "target_seconds": 55,
        "style": "ps1",          # ps1(레트로 공포 게임) | realistic(실사 파운드 푸티지)
    },
    "voice": {
        "engine": "edge",
        "voice": "ko-KR-InJoonNeural",  # 남성 저음. 여성: ko-KR-SunHiNeural
        "rate": "+12%",
        "pitch": "-6Hz",
        "pad_seconds": 0.35,
        "sentence_gap": 0.3,   # 문장 사이 쉼(초)
        # 괴이의 대사("...")는 다른 목소리로: 느리고 낮은 여성 목소리
        "dialogue": {"voice": "ko-KR-SunHiNeural", "rate": "-8%", "pitch": "-14Hz"},
    },
    "images": {
        "provider": "procedural",  # procedural | kling | manual
        "kling": {
            "base_url": "https://api-singapore.klingai.com",
            "model": "kling-v2-1",
            "aspect_ratio": "9:16",
            "video_model": "kling-v2-1",
            "mode": "std",  # std | pro
        },
    },
    "videos": {
        "provider": "manual",   # kling(API) | manual(Claude Code가 Kling 커넥터로 생성해 넣기) | none
        "scenes": "all",        # "all" 또는 ["기상", "규칙위반", "끝"] 처럼 단계 목록
        "durations": list(range(3, 16)),  # Kling 3.0 Turbo는 3~15초 자유. 구버전 모델이면 [5, 10]
        "model": "kling-video-v3_0_turbo",  # Kling 커넥터(MCP)로 만들 때 쓰는 모델
        "resolution": "720p",
        "require": True,        # 영상이 빠지면 멈출지 (False면 정지 이미지로 대체하고 진행)
        "parallel": 4,
    },
    "render": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "crf": 20,          # 중간 클립 화질
        "final_crf": 23,    # 최종 화질
        "max_bitrate": "10M",  # 노이즈 때문에 용량이 커지는 것 방지
        "bgm_volume": 0.22,
        "sfx_volume": 0.8,
        "loudness": -14,
        "subtitle_style": "clean",   # clean(참고 영상: 작은 흰 고딕, 대사는 빨강) | horror(명조·번짐·글리치)
        "rule_overlay": "panel",     # panel(반투명 쪽지, 해당 규칙 강조 후 사라짐) | card(종이 조각 상단 고정)
        "punch_cuts": True,          # 문장마다 구도를 바꿔 컷이 바뀐 느낌 (영상 장면만)
    },
    "upload": {
        "privacy": "private",
        "category_id": "24",
        "client_secret": "client_secret.json",
        "token": "youtube_token.json",
    },
}


def _merge(base: dict, over: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config(path: Path | None = None) -> dict:
    path = path or ROOT / "horror_config.yaml"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return _merge(DEFAULTS, yaml.safe_load(f) or {})
    return copy.deepcopy(DEFAULTS)

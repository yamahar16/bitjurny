"""API 없이 쓰는 자체 생성 배경 (리미널 스페이스 원근 복도/통로).

실제 업로드용으로는 Kling 등 이미지 생성기를 권장하지만,
이 모드만으로도 파이프라인 전체(렌더·자막·사운드)를 무료로 끝까지 돌려볼 수 있다.
"""
from __future__ import annotations

import hashlib
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

PERSON = re.compile(r"\b(man|woman|figure|silhouette|person|child|kid|doctor|teacher|conductor|customer|staff|clerk|passenger|someone|people|nurse|girl|boy|stranger)s?\b", re.I)

LAYOUTS = {
    # half-width, half-height, depth(끝 벽), 조명 간격
    "aisle": dict(a=0.55, b=0.75, depth=60.0, period=3.0),
    "corridor": dict(a=0.42, b=0.62, depth=45.0, period=4.0),
    "train": dict(a=0.50, b=0.55, depth=35.0, period=2.2),
    "room": dict(a=0.75, b=0.95, depth=3.2, period=1.4),
    "outdoor": dict(a=6.0, b=0.6, depth=80.0, period=9.0),
}


def _hash01(*arrs: np.ndarray) -> np.ndarray:
    h = np.zeros_like(arrs[0], dtype=np.float64)
    for i, a in enumerate(arrs):
        h = h + a * (12.9898 + 31.4 * i)
    return np.mod(np.sin(h) * 43758.5453, 1.0)


def render_scene(prompt: str, layout: str, tint: tuple[int, int, int], seed: int,
                 stage: str = "", size: tuple[int, int] = (1080, 1920)) -> Image.Image:
    W, H = size
    w, h = W // 2, H // 2  # 반해상도로 그리고 업스케일 (부드러운 질감)
    rng = np.random.default_rng(seed)
    L = LAYOUTS.get(layout, LAYOUTS["corridor"])
    a, b, depth, period = L["a"], L["b"], L["depth"], L["period"]

    cx = w * (0.5 + rng.uniform(-0.08, 0.08))
    cy = h * (0.46 + rng.uniform(-0.05, 0.05))
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float64)
    dx = (xs - cx) / w + 1e-6
    dy = (ys - cy) / h + 1e-6

    z_wall = a / np.abs(dx)
    z_fc = b / np.abs(dy)
    on_wall = z_wall < z_fc
    z = np.where(on_wall, z_wall, z_fc)
    back = z > depth
    z = np.minimum(z, depth)

    v = dy * z           # 벽 위 세로 위치 (-b..b)
    u = dx * z           # 바닥/천장 가로 위치 (-a..a)
    ceiling = (~on_wall) & (dy < 0) & ~back
    floor = (~on_wall) & (dy > 0) & ~back
    wall = on_wall & ~back

    base = np.full((h, w), 0.20)
    # 바닥 타일
    tile = (np.mod(u * 3.0, 1.0) < 0.04) | (np.mod(z * 1.0, 1.0) < 0.04)
    base = np.where(floor, 0.28 - 0.08 * tile, base)
    # 천장
    base = np.where(ceiling, 0.16, base)
    # 벽: 레이아웃별 패턴
    if layout == "aisle":
        shelf_edge = np.mod((v + b) * 5.0, 1.0) < 0.08
        prod = _hash01(np.floor(z * 2.5), np.floor((v + b) * 5.0), np.sign(dx))
        prod_col = 0.22 + 0.25 * prod
        base = np.where(wall, np.where(shelf_edge, 0.42, prod_col), base)
    elif layout == "train":
        win = (np.abs(v) < b * 0.35) & (np.mod(z / 2.2, 1.0) < 0.6) & (v < 0)
        base = np.where(wall, np.where(win, 0.04, 0.30), base)
    elif layout == "corridor":
        door = (np.mod(z / 6.0, 1.0) < 0.18) & (v > -b * 0.25)
        stripe = np.abs(v - b * 0.15) < 0.02
        base = np.where(wall, np.where(door, 0.12, np.where(stripe, 0.18, 0.32)), base)
    elif layout == "room":
        tiles = (np.mod((v + b) * 6, 1.0) < 0.05) | (np.mod(z * 6, 1.0) < 0.05)
        base = np.where(wall, 0.34 - 0.08 * tiles, base)
        base = np.where(back, 0.30, base)
    else:  # outdoor
        sky = dy < 0
        base = np.where(sky, 0.05, 0.12 + 0.04 * (np.mod(u * 0.5, 1.0) < 0.02))
        on_wall[:] = False

    # 천장 조명 (일부는 꺼짐 = 불안감)
    light_idx = np.floor(z / period)
    off = _hash01(light_idx, np.full_like(light_idx, seed % 97)) < 0.22
    lamp = ceiling & (np.abs(u) < a * 0.22) & (np.mod(z / period, 1.0) < 0.28) & ~off
    if layout == "outdoor":
        lamp = np.zeros_like(lamp)

    # 거리 감쇠 + 안개
    atten = 1.0 / (1.0 + z * 0.09)
    lum = base * (0.35 + 0.65 * atten)
    fog = 1.0 - np.exp(-z / (depth * 0.55 + 1))
    lum = lum * (1 - fog) + 0.10 * fog
    lum = np.where(back, lum * 0.55, lum)

    img = np.stack([lum] * 3, axis=-1)
    tint_v = np.array(tint, dtype=np.float64) / 255.0
    img = img * tint_v * 1.25

    emissive = np.where(lamp, 1.0, 0.0)
    pil_e = Image.fromarray((emissive * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(6))
    glow = np.asarray(pil_e, dtype=np.float64)[..., None] / 255.0
    img = img + glow * np.array([0.85, 0.95, 0.85]) * 0.9 + emissive[..., None] * 0.6

    # 바닥 반사
    refl = np.flipud(glow[: int(cy)])
    pad = h - int(cy) - refl.shape[0]
    if pad >= 0:
        refl = np.concatenate([refl, np.zeros((pad, w, 1))], axis=0)[: h - int(cy)]
        img[int(cy):] += refl[: h - int(cy)] * 0.18

    # 단계별 색 연출
    if stage == "규칙위반":
        img = img * np.array([1.35, 0.55, 0.55])
    elif stage == "끝":
        img = img * 0.6
    elif stage == "기상":
        img = img * 0.85

    out = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))

    # 실루엣 (프롬프트에 사람이 있으면)
    if PERSON.search(prompt or ""):
        d = ImageDraw.Draw(out)
        zf = rng.uniform(5, 14) if layout != "room" else rng.uniform(1.6, 2.6)
        scale_px = h / zf * 0.62
        lateral = rng.uniform(-a * 0.5, a * 0.5)
        px = cx + lateral / zf * w
        foot = cy + b / zf * h
        body_h = scale_px * 1.0
        bw = body_h * 0.26
        top = foot - body_h
        d.rounded_rectangle([px - bw / 2, top + body_h * 0.16, px + bw / 2, foot], radius=bw * 0.35, fill=(4, 4, 5))
        hr = body_h * 0.085
        d.ellipse([px - hr, top, px + hr, top + hr * 2.2], fill=(4, 4, 5))
        out = out.filter(ImageFilter.GaussianBlur(0.8))

    # 비네팅
    vig = Image.new("L", (w, h), 0)
    ImageDraw.Draw(vig).ellipse([-w * 0.25, -h * 0.12, w * 1.25, h * 1.12], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(w // 5))
    out = Image.composite(out, Image.new("RGB", (w, h), (0, 0, 0)), vig)

    out = out.resize((W, H), Image.LANCZOS)
    noise = np.random.default_rng(seed + 1).normal(0, 7, (H, W, 1))
    arr = np.clip(np.asarray(out, dtype=np.float64) + noise, 0, 255).astype(np.uint8)
    return Image.fromarray(arr)


def seed_for(text: str, idx: int) -> int:
    return int(hashlib.md5(f"{idx}:{text}".encode()).hexdigest()[:8], 16)

"""화면 위에 얹는 그래픽: 수칙 종이, 수칙 카드, 위반 도장, 썸네일."""
from __future__ import annotations

import random

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .fonts import font_path

PAPER = (226, 219, 198)
INK = (28, 24, 22)
RED = (178, 22, 22)


def _font(key: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(font_path(key)), size)


def wrap(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
    """한글은 어절 단위, 너무 긴 어절은 글자 단위로 줄바꿈."""
    lines, cur = [], ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if font.getlength(trial) <= max_w:
            cur = trial
            continue
        if cur:
            lines.append(cur)
        cur = ""
        for ch in word:
            if font.getlength(cur + ch) > max_w and cur:
                lines.append(cur)
                cur = ""
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def _paper_texture(w: int, h: int, seed: int) -> Image.Image:
    rng = np.random.default_rng(seed)
    base = np.ones((h, w, 3)) * np.array(PAPER, dtype=np.float64)
    base += rng.normal(0, 6, (h, w, 1))
    # 가장자리 누렇게
    ys, xs = np.mgrid[0:h, 0:w]
    edge = np.minimum.reduce([xs, ys, w - xs, h - ys]).astype(np.float64)
    base -= np.clip(40 - edge, 0, 40)[..., None] * np.array([0.6, 0.9, 1.4])
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img, "RGBA")
    for _ in range(4):  # 얼룩
        r = rng.integers(30, 110)
        x, y = rng.integers(0, w), rng.integers(0, h)
        d.ellipse([x - r, y - r, x + r, y + r], fill=(120, 95, 50, int(rng.integers(10, 26))))
    return img.filter(ImageFilter.GaussianBlur(0.6))


def rulebook(size: tuple[int, int], title: str, rules: list[dict], world: str, seed: int = 7,
             handwritten: int | None = None) -> Image.Image:
    """수칙발견 장면용 — 테이프로 붙은 안내문 한 장. handwritten 번호의 수칙은 볼펜 손글씨로 (반전 결말용)."""
    W, H = size
    pw = int(W * 0.80)
    tf, rf, nf = _font("myeongjo", 50), _font("myeongjo", 37), _font("myeongjo", 37)
    pf = _font("pen", 50)
    inner = pw - 120
    body = []
    for r in rules:
        hand = r["number"] == handwritten
        body.append((f"{r['number']}.", wrap(r["text"], pf if hand else rf, inner - 60), hand))
    t_lines = wrap(title, tf, inner)
    ph = 90 + len(t_lines) * 64 + 40 + sum(len(b[1]) * 52 + 22 for b in body) + 90
    paper = _paper_texture(pw, ph, seed).convert("RGBA")
    d = ImageDraw.Draw(paper)
    y = 80
    for ln in t_lines:
        d.text(((pw - tf.getlength(ln)) / 2, y), ln, font=tf, fill=INK)
        y += 64
    d.line([60, y + 14, pw - 60, y + 14], fill=INK, width=3)
    y += 50
    rng = random.Random(seed)
    for num, lines, hand in body:
        if hand:  # 다른 줄과 달리 파란 볼펜, 살짝 삐뚤게
            d.text((56, y - 6), num, font=pf, fill=(28, 48, 140))
            for k, ln in enumerate(lines):
                d.text((118 + 3 * k, y - 8), ln, font=pf, fill=(28, 48, 140))
                y += 52
        else:
            d.text((60, y), num, font=nf, fill=RED)
            for ln in lines:
                d.text((120, y), ln, font=rf, fill=INK)
                y += 52
        y += 22
    if world in ("scp", "mixed"):
        # 검게 지운 줄 + 등급 도장
        for _ in range(2):
            bx = rng.randint(120, pw - 360)
            by = rng.randint(200, max(201, ph - 160))
            d.rectangle([bx, by, bx + rng.randint(140, 260), by + 34], fill=(12, 12, 12))
        stamp = Image.new("RGBA", (420, 120), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        sd.rectangle([4, 4, 416, 116], outline=RED + (210,), width=6)
        sf = _font("gothic", 40)
        txt = "격리 등급: 미분류"
        sd.text(((420 - sf.getlength(txt)) / 2, 36), txt, font=sf, fill=RED + (210,))
        stamp = stamp.rotate(14, expand=True, resample=Image.BICUBIC)
        paper.alpha_composite(stamp, (pw - stamp.width - 30, ph - stamp.height - 20))
    # 테이프
    tape = Image.new("RGBA", (190, 56), (230, 225, 200, 150))
    paper.alpha_composite(tape.rotate(-8, expand=True), (pw // 2 - 95, -6))
    paper = paper.rotate(-1.5, expand=True, resample=Image.BICUBIC)

    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    shadow = Image.new("RGBA", paper.size, (0, 0, 0, 0))
    shadow.paste((0, 0, 0, 150), mask=paper.split()[3])
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    max_h = int(H * 0.56)
    if paper.height > max_h:  # 수칙이 많으면 축소
        r = max_h / paper.height
        paper = paper.resize((int(paper.width * r), max_h), Image.LANCZOS)
        shadow = shadow.resize(paper.size, Image.LANCZOS)
    x = (W - paper.width) // 2
    y = int(H * 0.15)
    canvas.alpha_composite(shadow, (x + 14, y + 22))
    canvas.alpha_composite(paper, (x, y))
    return canvas


def rule_card(size: tuple[int, int], number: int, text: str, violated: bool = False) -> Image.Image:
    """수칙연출/규칙위반 장면 상단 카드."""
    W, H = size
    nf, tf = _font("gothic", 40), _font("myeongjo", 52)
    lines = wrap(text, tf, W - 220)
    ch = 60 + 56 + len(lines) * 70 + 40
    card = Image.new("RGBA", (W - 120, ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, card.width - 1, ch - 1], radius=18, fill=(8, 8, 10, 175), outline=(200, 200, 190, 60), width=2)
    d.text((50, 42), f"수칙 {number}", font=nf, fill=RED + (255,))
    y = 42 + 66
    for ln in lines:
        d.text((50, y), ln, font=tf, fill=(238, 232, 220, 255))
        y += 70
    if violated:
        stamp = Image.new("RGBA", (300, 130), (0, 0, 0, 0))
        sd = ImageDraw.Draw(stamp)
        sd.rectangle([5, 5, 295, 125], outline=RED + (235,), width=8)
        sf = _font("gothic", 78)
        sd.text(((300 - sf.getlength("위반")) / 2, 18), "위반", font=sf, fill=RED + (235,))
        stamp = stamp.rotate(-12, expand=True, resample=Image.BICUBIC)
        card.alpha_composite(stamp, (card.width - stamp.width - 20, max(0, ch - stamp.height + 10)))
        # 취소선
        d.line([40, 42 + 66 + 34, card.width - 60, 42 + 66 + 34 + (len(lines) - 1) * 70], fill=RED + (220,), width=6)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    canvas.alpha_composite(card, (60, int(H * 0.11)))
    return canvas


def thumbnail(bg: Image.Image, text: str, label: str, size: tuple[int, int]) -> Image.Image:
    W, H = size
    img = bg.convert("RGB").resize(size, Image.LANCZOS)
    arr = np.asarray(img, dtype=np.float64) * 0.55
    ys = np.linspace(0, 1, H)[:, None, None]
    arr = arr * (1 - 0.55 * np.clip((ys - 0.35) / 0.65, 0, 1))  # 아래쪽 어둡게
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)).convert("RGBA")
    d = ImageDraw.Draw(img)
    lf = _font("gothic", 54)
    d.rounded_rectangle([60, 120, 60 + lf.getlength(label) + 60, 210], radius=12, fill=RED + (230,))
    d.text((90, 132), label, font=lf, fill=(255, 255, 255))
    lines = [ln for ln in text.split("\n") if ln.strip()][:3]
    tf = _font("myeongjo", 150)
    y = int(H * 0.56)
    for i, ln in enumerate(lines):
        f = tf
        while f.getlength(ln) > W - 120 and f.size > 70:
            f = _font("myeongjo", f.size - 8)
        x = (W - f.getlength(ln)) / 2
        col = RED + (255,) if i == len(lines) - 1 else (245, 240, 230, 255)
        d.text((x, y), ln, font=f, fill=col, stroke_width=8, stroke_fill=(0, 0, 0))
        y += int(f.size * 1.22)
    return img.convert("RGB")

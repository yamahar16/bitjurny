"""장소 · 세계관 · 결말 프리셋.

SCP 문서나 특정 게시글을 옮기지 않고, 장르 문법(규칙 괴담, 리미널 스페이스, 기관 보고서 톤)만 차용한다.
"""
from __future__ import annotations

STAGES = ["기상", "상황파악", "수칙발견", "수칙연출", "규칙위반", "끝"]

# 이미지 프롬프트 공통 꼬리 — 모든 장면 톤 통일용
STYLES = {
    # 참고 영상(레트로 공포 게임) 스타일
    "ps1": ("dark gritty late-1990s PS1 survival horror game screenshot, low-poly 3D models, blurry low-resolution pixelated textures, "
            "heavy darkness, dim flickering fluorescent light, fog, muted desaturated colors, uncanny mannequin-like characters "
            "fully clothed in staff uniforms, VHS grain, eerie, vertical 9:16, no text, no letters, no UI, no watermark"),
    "realistic": None,  # 아래 STYLE_SUFFIX
}
STYLE_SUFFIX = (
    "vertical 9:16 composition, found footage still frame, dim flickering fluorescent light, "
    "heavy film grain, desaturated sickly green tint, liminal space, unsettling empty atmosphere, "
    "photorealistic, faces hidden in shadow or blurred, no text, no letters, no watermark"
)

PLACES: dict[str, dict] = {
    "mart": {
        "name": "무한마트",
        "rulebook": "무한마트 야간 고객 안내문",
        "visual": "endless supermarket aisles at night, identical shelves repeating into darkness",
        "layout": "aisle",
        "tint": (150, 190, 160),
    },
    "subway": {
        "name": "심야 지하철",
        "rulebook": "심야 열차 승객 안전 수칙",
        "visual": "empty subway car at night, harsh fluorescent light, black windows reflecting the interior",
        "layout": "train",
        "tint": (170, 185, 200),
    },
    "train": {
        "name": "끝나지 않는 열차",
        "rulebook": "제0호 열차 객실 이용 안내",
        "visual": "long old passenger train interior, rows of seats, dusk light through windows",
        "layout": "train",
        "tint": (200, 170, 130),
    },
    "elevator": {
        "name": "아파트 엘리베이터",
        "rulebook": "엘리베이터 이용 수칙 (관리사무소)",
        "visual": "old apartment elevator interior, mirror wall, button panel, dim yellow light",
        "layout": "room",
        "tint": (200, 180, 120),
    },
    "store": {
        "name": "야간 편의점",
        "rulebook": "야간 근무자 인수인계 메모",
        "visual": "24 hour convenience store at 3am, empty street outside, buzzing fluorescent lights",
        "layout": "aisle",
        "tint": (170, 200, 200),
    },
    "hospital": {
        "name": "폐병원 7병동",
        "rulebook": "7병동 야간 보호자 수칙",
        "visual": "abandoned hospital corridor at night, peeling green walls, flickering lights, empty wheelchair",
        "layout": "corridor",
        "tint": (140, 180, 150),
    },
    "school": {
        "name": "새벽 학교",
        "rulebook": "야간 자율학습실 이용 규칙",
        "visual": "dark empty school hallway and classroom at night, moonlight through windows",
        "layout": "corridor",
        "tint": (140, 160, 200),
    },
    "restarea": {
        "name": "고속도로 졸음쉼터",
        "rulebook": "졸음쉼터 이용 안내",
        "visual": "empty highway rest area at night, single glowing vending machine, thick fog",
        "layout": "outdoor",
        "tint": (160, 170, 190),
    },
    "pool": {
        "name": "폐장한 실내 수영장",
        "rulebook": "야간 수영장 관리 수칙",
        "visual": "empty indoor swimming pool at night, still water, tiled walls, humming lights",
        "layout": "room",
        "tint": (130, 190, 200),
    },
    "stairwell": {
        "name": "아파트 무한 비상계단",
        "rulebook": "비상계단 이용 안내 (관리사무소)",
        "visual": "Korean apartment emergency stairwell at night, concrete stairs spiraling down, green exit sign, motion-sensor light, steel fire doors",
        "layout": "corridor",
        "tint": (150, 175, 150),
    },
    "arcade": {
        "name": "지하상가 야간 경비",
        "rulebook": "야간 경비 인수인계 메모",
        "visual": "Korean underground shopping arcade at night, all shop shutters down, long tiled corridor, stopped escalator, small glass security booth",
        "layout": "aisle",
        "tint": (160, 170, 160),
    },
    "doorbell": {
        "name": "새벽 택배 방문자",
        "rulebook": "방문자 응대 수칙",
        "visual": "small Korean studio apartment at night, front door with peephole and video intercom screen, dim shoe entryway with motion-sensor light, cardboard delivery boxes",
        "layout": "corridor",
        "tint": (165, 160, 150),
    },
    "village": {
        "name": "시골 마을 규칙",
        "rulebook": "마을 밤 외출 수칙",
        "visual": "remote Korean countryside village at night, old tiled-roof houses, rice paddies, scarecrows, a loudspeaker on a wooden pole, stone well, dirt paths",
        "layout": "corridor",
        "tint": (160, 170, 150),
    },
    "parking": {
        "name": "지하 주차장 B∞층",
        "rulebook": "지하 주차장 이용 안내",
        "visual": "endless underground parking garage, concrete pillars, flickering tube lights",
        "layout": "corridor",
        "tint": (170, 175, 160),
    },
}

WORLDS: dict[str, dict] = {
    "napolitan": {
        "name": "나폴리탄식 규칙 괴담",
        "guide": "근무 수칙·안내문 형식. 이유를 설명하지 않는 금지 규칙. 서로 미묘하게 모순되는 수칙. 일상적인 공문체가 주는 기괴함.",
    },
    "scp": {
        "name": "SCP식 격리 기록",
        "guide": "가상의 격리 기관 보고서 톤. 격리 절차, 관찰 기록, 검게 지워진 문구, 등급 표기. 단 실제 SCP 번호·개체명·문서는 절대 사용하지 않는다.",
    },
    "mixed": {
        "name": "혼합",
        "guide": "평범한 안내문으로 시작하지만 문서 뒷면이나 도장에서 정체불명 기관의 흔적이 드러난다.",
    },
}

ENDINGS: dict[str, dict] = {
    "loop": {
        "name": "무한 루프",
        "guide": "마지막 장면이 첫 장면(눈을 뜨는 장면)으로 그대로 이어진다. 마지막 나레이션이 첫 나레이션과 연결되게 써서 쇼츠 반복 재생을 유도.",
    },
    "become": {
        "name": "그것이 된다",
        "guide": "주인공이 괴이의 일부가 된다. 새로 온 누군가에게 주인공이 '규칙 속 존재'가 되어 나타나는 암시.",
    },
    "vanish": {
        "name": "소멸",
        "guide": "주인공은 사라지고, 수칙 문서만 남는다. 문서에 새 수칙이 한 줄 늘어나 있다.",
    },
    "viewer": {
        "name": "시청자 지목",
        "guide": "마지막 문장이 화면 너머의 시청자를 직접 지목한다. ('지금 이 영상을 보는 당신…')",
    },
    "twist": {
        "name": "반전",
        "guide": "수칙 중 하나가 거짓이었다. 그 한 줄만 손글씨였고, 그 글씨는 주인공의 것이었다 같은 반전.",
    },
}

MOTIONS = ["zoom_in", "zoom_out", "pan_left", "pan_right", "shake", "static"]
SFX = ["none", "hit", "riser", "heartbeat", "static_burst", "chime"]

STYLES["realistic"] = STYLE_SUFFIX


def style_suffix(name: str | None) -> str:
    return STYLES.get(name or "ps1") or STYLE_SUFFIX

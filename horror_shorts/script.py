"""1단계: 대본 생성.

ANTHROPIC_API_KEY가 있으면 Claude API로 바로 생성하고,
없으면 job 폴더에 script_request.md(프롬프트)를 써두고 멈춘다(handoff).
그때는 Claude Code 세션에서 그 요청대로 script.json을 만들어 넣고 다시 run 하면 된다.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .presets import ENDINGS, MOTIONS, PLACES, SFX, STAGES, STYLE_SUFFIX, WORLDS


class NeedsScript(RuntimeError):
    """API 키가 없어 대본을 Claude Code가 직접 써야 할 때."""


SCRIPT_SCHEMA: dict = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "title", "title_options", "hook", "rulebook_title", "rules", "scenes",
        "violated_rule", "thumbnail_text", "thumbnail_prompt", "description", "hashtags",
    ],
    "properties": {
        "title": {"type": "string", "description": "쇼츠 제목 (40자 이내)"},
        "title_options": {"type": "array", "items": {"type": "string"}, "description": "대안 제목 3개"},
        "hook": {"type": "string", "description": "첫 2초 후킹 문장 (첫 장면 나레이션의 첫 문장)"},
        "rulebook_title": {"type": "string", "description": "수칙 문서 제목"},
        "rules": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["number", "text", "violation_result"],
                "properties": {
                    "number": {"type": "integer"},
                    "text": {"type": "string", "description": "공문체 수칙 문장 (45자 이내)"},
                    "violation_result": {"type": "string", "description": "어겼을 때 결과"},
                },
            },
        },
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["stage", "narration", "caption", "image_prompt", "video_prompt", "motion", "sfx", "rule_number"],
                "properties": {
                    "stage": {"type": "string", "enum": STAGES},
                    "narration": {"type": "string", "description": "TTS로 읽을 1인칭 나레이션 (1~3문장)"},
                    "caption": {"type": "string", "description": "화면 상단에 크게 띄울 강조 문구 (12자 이내, 없으면 빈 문자열)"},
                    "image_prompt": {"type": "string", "description": "첫 프레임 이미지 생성용 영어 프롬프트"},
                    "video_prompt": {"type": "string", "description": "그 이미지를 움직일 영상 프롬프트 (영어, 카메라·피사체 움직임)"},
                    "motion": {"type": "string", "enum": MOTIONS},
                    "sfx": {"type": "string", "enum": SFX},
                    "rule_number": {"type": "integer", "description": "이 장면이 다루는 수칙 번호, 없으면 0"},
                },
            },
        },
        "violated_rule": {"type": "integer"},
        "thumbnail_text": {"type": "string", "description": "썸네일 큰 글씨 (2줄, 줄당 8자 이내, 줄바꿈은 \\n)"},
        "thumbnail_prompt": {"type": "string", "description": "썸네일 배경 영어 프롬프트"},
        "description": {"type": "string", "description": "유튜브 설명란"},
        "hashtags": {"type": "array", "items": {"type": "string"}},
    },
}

SYSTEM_PROMPT = f"""당신은 유튜브 쇼츠용 '규칙 괴담' 전문 작가 겸 연출가입니다.
SCP 재단 세계관과 디시인사이드 나폴리탄 갤러리식 규칙 괴담의 장르 문법을 깊이 이해하지만, 언제나 오리지널 이야기를 씁니다.

## 저작권 원칙
- 실제 SCP 문서·번호·고유 개체명, 특정 게시글이나 웹소설(괴담출근, 괴담동아리 등)의 문장·고유 설정을 그대로 쓰지 않습니다.
- 차용하는 것은 장르 형식뿐입니다: 안내문/근무 수칙 형식, 이유를 설명하지 않는 금지, 리미널 스페이스, 기관 보고서 톤, 모순된 수칙.

## 고정 구조 (stage 값, 반드시 이 순서)
1. 기상 (1장면): 첫 문장부터 후킹. 이미 괴담에 휘말린 기괴한 상황, 또는 낯선 장소에서 눈을 뜬다. 인사·소개·설명 금지.
2. 상황파악 (1장면): 무엇이 이상한지 '한 가지'를 구체적인 이미지로.
3. 수칙발견 (1장면): 안내문·메모·인수인계서 발견. 나레이션은 발견한 순간만, 수칙 내용은 다음 장면들에서.
4. 수칙연출 (수칙 개수만큼): 수칙 하나당 한 장면. 나레이션은 "수칙 N번." 으로 시작해 수칙을 짧게 읽고, 그 수칙이 시험받는 순간을 보여준다. 마지막 수칙연출 장면에서 위반할 수칙의 유혹이 시작된다.
5. 규칙위반 (1장면): 주인공이 그 수칙을 어긴다(실수·유혹·착각). 그 수칙의 violation_result가 실제로 일어난다.
6. 끝 (1장면): 결과와 여운. 지정된 결말 유형을 따른다. 설명하지 말고 이미지로 끝낸다.

## 수칙 쓰는 법
- 이상할 만큼 구체적으로: 시간(새벽 3시 33분), 숫자(세 번), 색, 소리.
- 이유는 절대 설명하지 않는다. 공문체("~하지 마십시오", "~하십시오").
- 하나쯤은 다른 수칙과 미묘하게 모순되거나 거짓일 수 있다는 낌새.

## 쇼츠 분량·연출
- 1인칭 나레이션, 짧은 문장. 한 장면 1~3문장.
- 한국어 TTS는 장면·문장 사이 쉼까지 포함해 초당 약 4.8음절로 읽힌다. 전체 나레이션의 공백 제외 글자 수 ≈ 목표 초 × 4.8 (55초면 약 260자). 넘치면 문장을 줄인다.
- 고어 묘사 대신 '이상함'과 '암시'로 공포를 만든다 (유튜브 정책).
- caption: 화면 상단 강조 문구, 12자 이내. 수칙연출이면 "수칙 N", 기상이면 짧은 훅.
- image_prompt: 영어, 정지 이미지용. 장면의 구도·피사체를 구체적으로 쓰고 맨 끝에 반드시 다음 스타일 문구를 붙인다: "{STYLE_SUFFIX}"
- video_prompt: 영어. image_prompt 이미지를 첫 프레임으로 5초간 움직이는 지시. 카메라 움직임 1개 + 피사체/환경 움직임 1~2개 (예: "slow dolly forward down the aisle, fluorescent light flickers, a figure at the far end slowly turns its head"). 끝에 "subtle film grain, no cuts, no text"를 붙인다. 공포는 갑작스러운 점프보다 '천천히 다가오는 이상함'.
- motion: (영상이 없을 때 정지 이미지 카메라 효과) {', '.join(MOTIONS)} 중 하나. 기상은 zoom_out 또는 shake, 규칙위반은 shake 권장.
- sfx: {', '.join(SFX)} 중 하나. 규칙위반은 hit, 수칙발견은 static_burst 권장.
- hashtags: #괴담 #규칙괴담 #shorts 포함 5~8개.
- 결말이 '반전'이면 마지막 수칙을 '거짓(손글씨로 덧붙인) 수칙'으로 쓴다. 화면의 수칙 종이에서 그 줄만 볼펜 손글씨로 그려진다.
"""


def build_user_prompt(meta: dict) -> str:
    p = PLACES.get(meta["place"], {})
    place = meta.get("place_name") or p.get("name", meta["place"])
    if place != p.get("name"):  # 직접 입력한 장소면 프리셋 힌트를 쓰지 않는다
        p = {}
    world = WORLDS[meta["world"]]
    ending = ENDINGS[meta["ending"]]
    lines = [
        f"장소: {place}",
        f"장소 비주얼 힌트(영어): {p.get('visual', place)}",
        f"수칙 문서 예시 제목: {p.get('rulebook', place + ' 이용 수칙')} (더 그럴듯하게 바꿔도 됨)",
        f"세계관: {world['name']} — {world['guide']}",
        f"결말 유형: {ending['name']} — {ending['guide']}",
        f"수칙 개수: {meta['rules']}개 (수칙연출 장면도 {meta['rules']}개)",
        f"목표 길이: {meta['target_seconds']}초",
    ]
    if meta.get("idea"):
        lines.append(f"추가 아이디어: {meta['idea']}")
    if meta.get("avoid"):
        lines.append("이미 만든 편과 겹치지 않게 피할 것: " + " / ".join(meta["avoid"]))
    lines.append("위 조건으로 괴담 쇼츠 대본 하나를 JSON으로 작성하세요.")
    return "\n".join(lines)


def validate(script: dict, rules_expected: int | None = None) -> list[str]:
    """구조 검사. 문제 목록을 돌려준다(비어 있으면 통과)."""
    errs = []
    for sc in script.get("scenes", []):
        sc.setdefault("video_prompt", "")
    for k in SCRIPT_SCHEMA["required"]:
        if k not in script:
            errs.append(f"필드 누락: {k}")
    if errs:
        return errs
    stages = [s.get("stage") for s in script["scenes"]]
    order = [STAGES.index(s) if s in STAGES else -1 for s in stages]
    if -1 in order:
        errs.append(f"알 수 없는 stage: {stages}")
    elif order != sorted(order):
        errs.append(f"stage 순서가 구조와 다름: {stages}")
    for need in STAGES:
        if need not in stages:
            errs.append(f"stage 누락: {need}")
    n_rules = len(script["rules"])
    if rules_expected and n_rules != rules_expected:
        errs.append(f"수칙 개수 {n_rules} ≠ 요청 {rules_expected}")
    if stages.count("수칙연출") != n_rules:
        errs.append(f"수칙연출 장면 {stages.count('수칙연출')}개 ≠ 수칙 {n_rules}개")
    if script["violated_rule"] not in {r["number"] for r in script["rules"]}:
        errs.append("violated_rule이 수칙 번호에 없음")
    for i, s in enumerate(script["scenes"]):
        if s.get("motion") not in MOTIONS:
            errs.append(f"scene {i} motion 값 오류: {s.get('motion')}")
        if s.get("sfx") not in SFX:
            errs.append(f"scene {i} sfx 값 오류: {s.get('sfx')}")
        if not s.get("narration", "").strip():
            errs.append(f"scene {i} 나레이션 비어 있음")
    return errs


def estimate_seconds(script: dict, syllables_per_sec: float = 4.8) -> float:
    chars = sum(len(s["narration"].replace(" ", "")) for s in script["scenes"])
    return chars / syllables_per_sec


def generate_with_claude(meta: dict, cfg: dict) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    model = cfg["script"]["model"]
    kwargs = dict(
        model=model,
        max_tokens=16000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(meta)}],
        output_config={"effort": cfg["script"]["effort"], "format": {"type": "json_schema", "schema": SCRIPT_SCHEMA}},
    )
    # 정책 분류기가 공포 묘사를 오탐해 거절하면 서버에서 다른 모델로 자동 재시도
    if model in ("claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5", "claude-fable-5-1"):
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    else:
        resp = client.messages.create(**kwargs)
    if resp.stop_reason == "refusal":
        raise RuntimeError(f"Claude가 요청을 거절했습니다: {getattr(resp, 'stop_details', None)}")
    if resp.stop_reason == "max_tokens":
        raise RuntimeError("출력이 max_tokens에서 잘렸습니다.")
    text = "".join(b.text for b in resp.content if b.type == "text")
    return json.loads(text)


def run(job: Path, meta: dict, cfg: dict) -> dict:
    out = job / "script.json"
    if out.exists():
        script = json.loads(out.read_text(encoding="utf-8"))
    elif os.environ.get("ANTHROPIC_API_KEY"):
        script = None
        last_errs: list[str] = []
        for attempt in range(2):
            cand = generate_with_claude(meta, cfg)
            last_errs = validate(cand, meta["rules"])
            if not last_errs:
                script = cand
                break
        if script is None:
            (job / "script_invalid.json").write_text(json.dumps(cand, ensure_ascii=False, indent=2), encoding="utf-8")
            raise RuntimeError("생성된 대본이 구조 검사를 통과하지 못했습니다: " + "; ".join(last_errs))
        out.write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    else:
        req = job / "script_request.md"
        req.write_text(
            "# 대본 요청 (Claude Code가 직접 작성)\n\n"
            "아래 system/user 프롬프트대로 대본을 쓰고, `script_schema.json` 형식에 맞춰 "
            f"`{out.name}`으로 이 폴더에 저장한 뒤 다시 run 하세요.\n\n"
            f"## system\n\n{SYSTEM_PROMPT}\n\n## user\n\n{build_user_prompt(meta)}\n",
            encoding="utf-8",
        )
        (job / "script_schema.json").write_text(json.dumps(SCRIPT_SCHEMA, ensure_ascii=False, indent=2), encoding="utf-8")
        raise NeedsScript(f"ANTHROPIC_API_KEY가 없어 대본 요청서를 남겼습니다: {req}")

    errs = validate(script, meta["rules"])
    if errs:
        raise RuntimeError("script.json 구조 오류: " + "; ".join(errs))
    return script

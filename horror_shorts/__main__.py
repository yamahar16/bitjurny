"""CLI.

  python -m horror_shorts places
  python -m horror_shorts make --place mart --world napolitan --ending loop --rules 4
  python -m horror_shorts make --place subway --count 3          # 같은 장소 3편 연속 (시리즈)
  python -m horror_shorts run jobs/20261102-150000-mart [--force voice] [--upload]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from . import pipeline
from .config import JOBS_DIR, load_config
from .images import NeedsImages
from .videos import NeedsVideos
from .presets import ENDINGS, PLACES, WORLDS
from .script import NeedsScript


def cmd_places(_args, _cfg) -> None:
    print("장소 (--place):")
    for k, v in PLACES.items():
        print(f"  {k:<10} {v['name']}")
    print("\n세계관 (--world):")
    for k, v in WORLDS.items():
        print(f"  {k:<10} {v['name']}")
    print("\n결말 (--ending):")
    for k, v in ENDINGS.items():
        print(f"  {k:<10} {v['name']} — {v['guide'][:40]}…")


def _run_job(job: Path, cfg: dict, args) -> bool:
    try:
        out = pipeline.run(job, cfg, upload=args.upload, force=getattr(args, "force", None))
        print(f"\n완료: {out}")
        return True
    except (NeedsScript, NeedsImages, NeedsVideos) as e:
        print(f"\n⏸ 멈춤 — {e}\n   준비되면: python -m horror_shorts run {job}")
        return False


def cmd_make(args, cfg) -> None:
    previous: list[str] = []
    for n in range(args.count):
        place = args.place if args.place != "random" else random.choice(list(PLACES))
        meta = {
            "place": place,
            "place_name": args.place_name or PLACES.get(place, {}).get("name", place),
            "world": args.world if args.world != "random" else random.choice(list(WORLDS)),
            "ending": args.ending if args.ending != "random" else random.choice(list(ENDINGS)),
            "rules": args.rules or cfg["script"]["rules"],
            "target_seconds": args.seconds or cfg["script"]["target_seconds"],
            "idea": args.idea,
            "images": args.images,
            "videos": args.videos,
            "style": args.style,
            "avoid": previous[-5:],
        }
        job = pipeline.new_job(meta)
        print(f"\n=== [{n + 1}/{args.count}] {meta['place_name']} · {WORLDS[meta['world']]['name']} · "
              f"{ENDINGS[meta['ending']]['name']} → {job}")
        if not _run_job(job, cfg, args):
            break
        sc = json.loads((job / "script.json").read_text(encoding="utf-8"))
        previous.append(f"{sc['title']} (수칙: {', '.join(r['text'][:18] for r in sc['rules'])})")


def cmd_run(args, cfg) -> None:
    job = Path(args.job)
    if not job.exists():
        job = JOBS_DIR / args.job
    if args.videos:
        mp = job / "meta.json"
        meta = json.loads(mp.read_text(encoding="utf-8"))
        meta["videos"] = args.videos
        mp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    _run_job(job, cfg, args)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="horror_shorts", description="괴담 쇼츠 자동화")
    ap.add_argument("--config", type=Path, default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("places", help="장소·세계관·결말 목록")

    mk = sub.add_parser("make", help="새 괴담 쇼츠 만들기")
    mk.add_argument("--place", default="mart", help="장소 키 또는 random (목록: places)")
    mk.add_argument("--place-name", default=None, help="프리셋에 없는 장소 이름 직접 입력 (예: '새벽 3시 찜질방')")
    mk.add_argument("--world", default="napolitan", choices=[*WORLDS, "random"])
    mk.add_argument("--ending", default="loop", choices=[*ENDINGS, "random"])
    mk.add_argument("--rules", type=int, default=None, help="수칙 개수 (3~6)")
    mk.add_argument("--seconds", type=int, default=None, help="목표 길이 (초)")
    mk.add_argument("--idea", default="", help="추가 아이디어")
    mk.add_argument("--images", default=None, choices=["procedural", "kling", "manual"])
    mk.add_argument("--videos", default=None, choices=["kling", "manual", "none"], help="장면 영상 (기본: 모든 장면 Kling 영상)")
    mk.add_argument("--style", default=None, choices=["ps1", "realistic"], help="화풍 (기본: ps1 레트로 공포 게임)")
    mk.add_argument("--count", type=int, default=1, help="연속 생성 편수")
    mk.add_argument("--upload", action="store_true", help="유튜브 업로드까지 (기본 비공개)")

    rn = sub.add_parser("run", help="기존 job 이어서 실행")
    rn.add_argument("job")
    rn.add_argument("--force", choices=pipeline.STEPS, default=None, help="이 단계부터 다시 만들기")
    rn.add_argument("--upload", action="store_true")
    rn.add_argument("--videos", default=None, choices=["kling", "manual", "none"], help="영상 방식 바꾸기 (none: 영상 없는 장면은 정지 이미지로)")

    args = ap.parse_args(argv)
    cfg = load_config(args.config)
    {"places": cmd_places, "make": cmd_make, "run": cmd_run}[args.cmd](args, cfg)


if __name__ == "__main__":
    sys.exit(main())

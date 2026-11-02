"""업로드 대기열 (자동 게시).

  python -m horror_shorts queue jobs/20261102-225321-doorbell   # 대기열에 넣기 (upload_queue/<이름>/)
  python -m horror_shorts upload-queue                            # 대기열 업로드 (GitHub Actions가 실행)

대기열 폴더를 git push 하면 .github/workflows/horror-upload.yml 이 GitHub 비밀값(Secrets)으로 업로드한다.
PC·클라우드 세션이 꺼져 있어도 GitHub 서버에서 올라가므로 폰만으로 운영할 수 있다.

예약 공개: config upload.schedule (기본 "19:00", 한국시간) — 하루 upload.per_day 편씩 다음 빈 시간에 공개 예약.
schedule 을 비우면 upload.privacy 그대로 올린다.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import ROOT

QUEUE_DIR = ROOT / "upload_queue"
KST = timezone(timedelta(hours=9))


def enqueue(job: Path, cfg: dict, log=print) -> Path:
    """final.mp4 를 업로드용(용량 작게)으로 다시 인코딩해 대기열에 넣는다."""
    for f in ("final.mp4", "upload.json"):
        if not (job / f).exists():
            raise RuntimeError(f"{job / f} 가 없습니다. 먼저 run 으로 영상을 완성하세요.")
    out = QUEUE_DIR / job.name
    out.mkdir(parents=True, exist_ok=True)
    qc = cfg["upload"].get("queue_encode", {})
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(job / "final.mp4"),
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(qc.get("crf", 25)),
                    "-maxrate", qc.get("maxrate", "3300k"), "-bufsize", qc.get("bufsize", "6600k"),
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
                    str(out / "video.mp4")], check=True)
    shutil.copy(job / "upload.json", out / "upload.json")
    if (job / "thumbnail.jpg").exists():
        shutil.copy(job / "thumbnail.jpg", out / "thumbnail.jpg")
    log(f"  대기열: {out} ({(out / 'video.mp4').stat().st_size / 1e6:.1f}MB)")
    return out


def _taken_slots() -> list[datetime]:
    slots = []
    for f in QUEUE_DIR.glob("*/uploaded.json"):
        at = json.loads(f.read_text(encoding="utf-8")).get("publish_at")
        if at:
            slots.append(datetime.fromisoformat(at.replace("Z", "+00:00")))
    return slots


def next_slot(cfg: dict, now: datetime | None = None) -> str | None:
    """하루 per_day 편, schedule 시각(한국시간)부터 2시간 간격으로 다음 빈 공개 시각 (UTC ISO)."""
    ucfg = cfg["upload"]
    sched = (ucfg.get("schedule") or "").strip()
    if not sched:
        return None
    hh, mm = map(int, sched.split(":"))
    per_day = max(1, int(ucfg.get("per_day", 1)))
    now = (now or datetime.now(timezone.utc)).astimezone(KST)
    taken = {s.astimezone(KST).replace(second=0, microsecond=0) for s in _taken_slots()}
    day = now.date()
    for _ in range(366):
        for k in range(per_day):
            t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=KST) + timedelta(hours=2 * k)
            if t > now + timedelta(minutes=30) and t not in taken:
                return t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        day += timedelta(days=1)
    return None


def pending() -> list[Path]:
    return sorted(d for d in QUEUE_DIR.iterdir()
                  if d.is_dir() and (d / "video.mp4").exists() and not (d / "uploaded.json").exists()) \
        if QUEUE_DIR.exists() else []


def upload_all(cfg: dict, log=print) -> int:
    from .publish import upload_video, youtube_client

    items = pending()
    if not items:
        log("대기열에 올릴 영상이 없습니다.")
        return 0
    yt = youtube_client(cfg)
    n = 0
    for d in items:
        meta = json.loads((d / "upload.json").read_text(encoding="utf-8"))
        at = next_slot(cfg)
        log(f"▶ 업로드: {meta['title']}" + (f" (공개 예약 {at})" if at else ""))
        vid = upload_video(yt, d / "video.mp4", meta, cfg, d / "thumbnail.jpg", publish_at=at, log=log)
        info = {"video_id": vid, "url": f"https://youtu.be/{vid}", "studio": f"https://studio.youtube.com/video/{vid}/edit",
                "title": meta["title"], "publish_at": at, "privacy": "private" if at else cfg["upload"]["privacy"],
                "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        (d / "uploaded.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
        (d / "video.mp4").unlink()  # 올린 영상은 저장소에서 지운다 (용량)
        log(f"  ✅ {info['url']}")
        n += 1
    return n

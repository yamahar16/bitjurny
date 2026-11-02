"""업로드 대기열 (자동 게시).

  python -m horror_shorts queue jobs/20261102-225321-doorbell   # 대기열에 넣기 (upload_queue/<이름>/)
  python -m horror_shorts upload-queue                            # 대기열 업로드 (GitHub Actions가 실행)

대기열 폴더를 git push 하면 .github/workflows/horror-upload.yml 이 GitHub 비밀값(Secrets)으로 업로드한다.
PC·클라우드 세션이 꺼져 있어도 GitHub 서버에서 올라가므로 폰만으로 운영할 수 있다.

예약 공개: config upload.schedule (기본 06:00·12:00·18:00, 한국시간) — 대기열 순서대로 다음 빈 시간에 공개 예약.
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
    # 쇼츠는 API로 썸네일을 못 정하므로, 맨 끝에 썸네일을 잠깐(기본 0.2초) 붙여 두고 앱에서 그 프레임을 커버로 고른다
    tail = float(cfg["upload"].get("end_thumbnail_seconds", 0.2))
    thumb = job / "thumbnail.jpg"
    W, H, fps = cfg["render"]["width"], cfg["render"]["height"], cfg["render"]["fps"]
    if tail > 0 and thumb.exists():
        inputs = ["-i", str(job / "final.mp4"), "-loop", "1", "-framerate", str(fps), "-t", f"{tail}", "-i", str(thumb),
                  "-f", "lavfi", "-t", f"{tail}", "-i", "anullsrc=r=44100:cl=stereo"]
        fc = (f"[0:v]fps={fps},scale={W}:{H},setsar=1,format=yuv420p[v0];"
              f"[1:v]fps={fps},scale={W}:{H},setsar=1,format=yuv420p[v1];"
              "[0:a]aresample=44100,aformat=channel_layouts=stereo[a0];[2:a]aformat=channel_layouts=stereo[a1];"
              "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
        mapping = ["-filter_complex", fc, "-map", "[v]", "-map", "[a]"]
    else:
        inputs, mapping = ["-i", str(job / "final.mp4")], []
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, *mapping,
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
    """다음 빈 공개 시각 (UTC ISO). upload.schedule: "19:00" 또는 ["06:00","12:00","18:00"] (한국시간),
    upload.start_date: "2026-11-04" 처럼 이 날짜 이전 슬롯은 쓰지 않음."""
    ucfg = cfg["upload"]
    sched = ucfg.get("schedule") or []
    if isinstance(sched, str):
        sched = [x.strip() for x in sched.split(",") if x.strip()]
    if not sched:
        return None
    times = sorted(tuple(map(int, t.split(":"))) for t in sched)
    now = (now or datetime.now(timezone.utc)).astimezone(KST)
    taken = {s.astimezone(KST).replace(second=0, microsecond=0) for s in _taken_slots()}
    day = now.date()
    if ucfg.get("start_date"):
        day = max(day, datetime.strptime(str(ucfg["start_date"]), "%Y-%m-%d").date())
    for _ in range(366):
        for hh, mm in times:
            t = datetime(day.year, day.month, day.day, hh, mm, tzinfo=KST)
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

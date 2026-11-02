"""5~7단계: SEO 메타데이터, 썸네일, 유튜브 업로드."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from . import overlays
from .presets import PLACES, WORLDS


def seo(job: Path, script: dict, meta: dict) -> dict:
    tags = []
    for h in script["hashtags"] + ["#괴담", "#규칙괴담", "#shorts"]:
        h = "#" + h.lstrip("#").replace(" ", "")
        if h not in tags:
            tags.append(h)
    title = script["title"].strip()
    if "#shorts" not in title.lower():
        title = f"{title} #shorts"
    title = title[:100]
    desc = (f"{script['description'].strip()}\n\n"
            "이 이야기는 창작된 픽션입니다. 실제 인물·장소·사건과 관련이 없습니다.\n\n"
            + " ".join(tags[:12]))
    data = {
        "title": title,
        "title_options": script.get("title_options", []),
        "description": desc,
        "tags": [t.lstrip("#") for t in tags][:15],
        "place": PLACES.get(meta["place"], {}).get("name", meta["place"]),
        "world": WORLDS[meta["world"]]["name"],
    }
    (job / "upload.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # 사람이 읽는 대본 파일
    lines = [f"# {script['title']}", "", f"[{script['rulebook_title']}]"]
    for r in script["rules"]:
        mark = " ← 위반" if r["number"] == script["violated_rule"] else ""
        lines.append(f"{r['number']}. {r['text']}{mark}\n   (어기면: {r['violation_result']})")
    lines.append("")
    for i, s in enumerate(script["scenes"]):
        lines.append(f"## {i:02d} [{s['stage']}] {s.get('caption', '')}")
        lines.append(s["narration"])
        lines.append(f"  · 이미지: {s['image_prompt']}")
        lines.append(f"  · 카메라: {s['motion']} / 효과음: {s['sfx']}\n")
    (job / "script.txt").write_text("\n".join(lines), encoding="utf-8")
    return data


def thumbnail(job: Path, script: dict, cfg: dict) -> Path:
    W, H = cfg["render"]["width"], cfg["render"]["height"]
    bg_path = job / "images" / "thumbnail_bg.png"
    if not bg_path.exists():
        idx = next((i for i, s in enumerate(script["scenes"]) if s["stage"] == "규칙위반"), 0)
        bg_path = job / "images" / f"scene_{idx:02d}.png"
    img = overlays.thumbnail(Image.open(bg_path), script["thumbnail_text"].replace("\\n", "\n"), "규칙 괴담", (W, H))
    out = job / "thumbnail.jpg"
    img.save(out, quality=92)
    return out


def youtube_client(cfg: dict):
    """YouTube API 클라이언트. 인증 정보 우선순위:
      1) YOUTUBE_TOKEN_JSON  : PC에서 받은 토큰 파일(json) 내용 전체 (refresh_token·client_id·client_secret 포함)
      2) YOUTUBE_REFRESH_TOKEN + YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET
      3) youtube_token.json 파일 / client_secret.json 으로 브라우저 로그인 (PC)
    클라우드·GitHub Actions 에서는 1) 또는 2)를 비밀값(Secrets)으로 넣는다."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError as e:
        raise RuntimeError("업로드하려면: pip install google-api-python-client google-auth-oauthlib") from e

    import os

    ucfg = cfg["upload"]
    root = Path.cwd()
    secret, token = root / ucfg["client_secret"], root / ucfg["token"]
    scopes = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
    creds = None
    if os.environ.get("YOUTUBE_TOKEN_JSON", "").strip():
        info = json.loads(os.environ["YOUTUBE_TOKEN_JSON"])
        creds = Credentials.from_authorized_user_info(info, info.get("scopes") or scopes)
    elif os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip():
        creds = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"].strip(),
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=os.environ["YOUTUBE_CLIENT_ID"].strip(),
                            client_secret=os.environ["YOUTUBE_CLIENT_SECRET"].strip())
    elif token.exists():
        creds = Credentials.from_authorized_user_file(str(token), scopes)
    if creds and not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not secret.exists():
            raise RuntimeError("유튜브 인증 정보가 없습니다. YOUTUBE_TOKEN_JSON 또는 YOUTUBE_REFRESH_TOKEN/CLIENT_ID/"
                               f"CLIENT_SECRET 비밀값, 혹은 {secret.name}(OAuth 데스크톱 클라이언트)가 필요합니다.")
        from google_auth_oauthlib.flow import InstalledAppFlow

        creds = InstalledAppFlow.from_client_secrets_file(str(secret), scopes).run_local_server(port=0)
        token.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds)


def upload_video(yt, video: Path, meta: dict, cfg: dict, thumb: Path | None = None,
                 publish_at: str | None = None, log=print) -> str:
    """영상 1개 업로드. publish_at(UTC ISO8601)을 주면 비공개로 올린 뒤 그 시각에 자동 공개된다."""
    from googleapiclient.http import MediaFileUpload

    ucfg = cfg["upload"]
    status = {"privacyStatus": ucfg["privacy"], "selfDeclaredMadeForKids": False,
              "containsSyntheticMedia": True}
    if publish_at:
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    body = {"snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                        "categoryId": ucfg["category_id"], "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
            "status": status}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(video), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    if thumb and thumb.exists():
        try:  # 커스텀 썸네일은 채널 전화번호 인증이 필요할 수 있다
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb))).execute()
        except Exception as e:
            log(f"  ⚠ 썸네일 설정 실패 (Studio에서 직접 적용): {e}")
    return vid


def upload(job: Path, cfg: dict, log=print) -> str:
    """job 폴더의 final.mp4 를 바로 업로드 (기본 비공개)."""
    yt = youtube_client(cfg)
    meta = json.loads((job / "upload.json").read_text(encoding="utf-8"))
    vid = upload_video(yt, job / "final.mp4", meta, cfg, job / "thumbnail.jpg", log=log)
    url = f"https://youtu.be/{vid}"
    (job / "uploaded.txt").write_text(url, encoding="utf-8")
    return url

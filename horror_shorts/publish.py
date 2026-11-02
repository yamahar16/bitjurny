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


def upload(job: Path, cfg: dict, log=print) -> str:
    """YouTube Data API v3 업로드. client_secret.json(OAuth 데스크톱 앱)이 필요하다. 기본 비공개."""
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
    except ImportError as e:
        raise RuntimeError("업로드하려면: pip install google-api-python-client google-auth-oauthlib") from e

    import os

    ucfg = cfg["upload"]
    root = Path.cwd()
    secret, token = root / ucfg["client_secret"], root / ucfg["token"]
    scopes = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.force-ssl"]
    creds = None
    # 클라우드/서버: 브라우저 로그인이 안 되므로 PC에서 받은 토큰을 환경변수로 넣는다
    #   YOUTUBE_TOKEN_JSON = 토큰 파일(json) 내용 전체 (refresh_token, client_id, client_secret 포함)
    #   또는 YOUTUBE_REFRESH_TOKEN + YOUTUBE_CLIENT_ID + YOUTUBE_CLIENT_SECRET
    if os.environ.get("YOUTUBE_TOKEN_JSON"):
        info = json.loads(os.environ["YOUTUBE_TOKEN_JSON"])
        creds = Credentials.from_authorized_user_info(info, info.get("scopes") or scopes)
    elif os.environ.get("YOUTUBE_REFRESH_TOKEN"):
        creds = Credentials(None, refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
                            token_uri="https://oauth2.googleapis.com/token",
                            client_id=os.environ["YOUTUBE_CLIENT_ID"], client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
                            scopes=scopes)
    elif token.exists():
        creds = Credentials.from_authorized_user_file(str(token), scopes)
    if creds and not creds.valid and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        if not secret.exists():
            raise RuntimeError("유튜브 인증 정보가 없습니다. YOUTUBE_TOKEN_JSON 환경변수(토큰 파일 내용) 또는 "
                               f"{secret.name}(OAuth 데스크톱 클라이언트)가 필요합니다.")
        creds = InstalledAppFlow.from_client_secrets_file(str(secret), scopes).run_local_server(port=0)
        token.write_text(creds.to_json(), encoding="utf-8")

    yt = build("youtube", "v3", credentials=creds)
    meta = json.loads((job / "upload.json").read_text(encoding="utf-8"))
    body = {
        "snippet": {"title": meta["title"], "description": meta["description"], "tags": meta["tags"],
                    "categoryId": ucfg["category_id"], "defaultLanguage": "ko"},
        "status": {"privacyStatus": ucfg["privacy"], "selfDeclaredMadeForKids": False},
    }
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(str(job / "final.mp4"), chunksize=-1, resumable=True))
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    vid = resp["id"]
    try:
        yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": "ko", "name": "한국어"}},
                             media_body=MediaFileUpload(str(job / "subtitles.srt"))).execute()
    except Exception as e:  # 자막 실패는 업로드 실패가 아님
        log(f"  ⚠ 자막 업로드 실패: {e}")
    try:  # 커스텀 썸네일은 채널 전화번호 인증이 필요할 수 있다
        yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(job / "thumbnail.jpg"))).execute()
    except Exception as e:
        log(f"  ⚠ 썸네일 설정 실패 (Studio에서 직접 적용): {e}")
    url = f"https://studio.youtube.com/video/{vid}/edit"
    (job / "uploaded.txt").write_text(url, encoding="utf-8")
    return url

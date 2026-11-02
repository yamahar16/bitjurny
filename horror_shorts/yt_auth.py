"""폰만으로 유튜브 로그인 (Google OAuth 기기 코드 방식).

GitHub Actions 'horror-youtube-auth' 워크플로가 실행한다:
  1) 구글에 기기 코드 요청 → 로그에 "google.com/device 에서 코드 XXXX-XXXX 입력" 출력
  2) 사용자가 폰으로 google.com/device 열고 코드 입력·허용
  3) 받은 refresh token 을 YOUTUBE_CLIENT_SECRET 으로 암호화해 upload_queue/.youtube_token.enc 로 저장 (커밋)

refresh token 은 client_id·client_secret 없이는 쓸 수 없고, 암호화 키도 client_secret 이라
저장소가 공개여도 GitHub Secrets 없이는 쓸모가 없다.

필요한 GitHub Secrets: YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET
  (Google Cloud 콘솔 → 사용자 인증 정보 → OAuth 클라이언트 ID → 유형 'TV 및 입력 제한 기기')
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import requests

from .config import ROOT

TOKEN_FILE = ROOT / "upload_queue" / ".youtube_token.enc"
SCOPE = "https://www.googleapis.com/auth/youtube"


def _fernet(client_secret: str):
    from cryptography.fernet import Fernet

    key = base64.urlsafe_b64encode(hashlib.sha256(("horror-shorts:" + client_secret).encode()).digest())
    return Fernet(key)


def load_refresh_token(client_secret: str, path: Path = TOKEN_FILE) -> str | None:
    if not path.exists():
        return None
    return _fernet(client_secret).decrypt(path.read_bytes()).decode()


def device_login(client_id: str, client_secret: str, path: Path = TOKEN_FILE, log=print) -> None:
    r = requests.post("https://oauth2.googleapis.com/device/code",
                      data={"client_id": client_id, "scope": SCOPE}, timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"기기 코드 요청 실패: {r.status_code} {r.text[:300]}")
    d = r.json()
    url = d.get("verification_url") or d.get("verification_uri")
    log(f"::notice title=유튜브 로그인::{url} 에서 코드 {d['user_code']} 입력 → 계정 선택 → 허용")
    log(f"YOUTUBE_LOGIN_CODE={d['user_code']}  URL={url}  (유효 {d['expires_in'] // 60}분)")
    sys.stdout.flush()
    interval = int(d.get("interval", 5))
    deadline = time.time() + int(d["expires_in"])
    while time.time() < deadline:
        time.sleep(interval)
        t = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
            "client_id": client_id, "client_secret": client_secret, "device_code": d["device_code"],
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code"}).json()
        err = t.get("error")
        if err == "authorization_pending":
            continue
        if err == "slow_down":
            interval += 5
            continue
        if err:
            raise RuntimeError(f"로그인 실패: {err} {t.get('error_description', '')}")
        if not t.get("refresh_token"):
            raise RuntimeError("refresh token 을 받지 못했습니다.")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_fernet(client_secret).encrypt(t["refresh_token"].encode()))
        log(f"✅ 유튜브 로그인 완료 → {path.relative_to(ROOT)} (암호화 저장)")
        return
    raise TimeoutError("시간 안에 코드 입력이 되지 않았습니다. 워크플로를 다시 실행하세요.")


if __name__ == "__main__":
    device_login(os.environ["YOUTUBE_CLIENT_ID"].strip(), os.environ["YOUTUBE_CLIENT_SECRET"].strip())

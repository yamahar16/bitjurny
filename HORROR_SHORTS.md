# 괴담 쇼츠 자동화 (horror_shorts)

규칙 괴담 쇼츠를 **대본 → 음성 → 이미지 → Kling 영상 → 렌더 → 제목·설명 → 썸네일 → (업로드)** 까지 한 번에 만듭니다.
기본값은 **모든 장면을 Kling 영상으로** 넣는 것입니다. 영상이 없는 장면만 정지 이미지 + 카메라 효과로 대체됩니다.

## 대본 구조 (고정)
**기상 → 상황 파악 → 수칙 발견 → 수칙별 상황 연출 → 규칙 위반 → 끝**

- 도입부 후킹: 괴담에 휘말린 기괴한 상황, 또는 낯선 장소에서 눈을 뜬다
- 수칙마다 (수칙 문장 / 시험받는 상황 / 어겼을 때 결과) 세트로 설계하고, 위반한 수칙의 결과를 실제로 보여준다
- SCP·나폴리탄 갤러리는 **세계관과 장르 문법만 참고**해서 오리지널로 각색 (SCP 번호·개체명·게시글 원문 사용 금지)

## 설치
```bash
pip install -r requirements-horror.txt   # ffmpeg 필요 (libass 포함 빌드)
```
한글 폰트(나눔고딕·나눔명조·나눔펜, OFL)는 첫 실행 때 자동으로 받습니다.

## 사용법
```bash
python -m horror_shorts places                       # 장소·세계관·결말 목록
python -m horror_shorts make --place mart --world napolitan --ending loop --rules 4
python -m horror_shorts make --place random --ending random --count 5   # 5편 연속
python -m horror_shorts make --place elevator --place-name "새벽 3시 찜질방" --idea "주인공은 신입 알바생"
python -m horror_shorts run jobs/<폴더> --force voice  # 특정 단계부터 다시
python -m horror_shorts run jobs/<폴더> --upload       # 유튜브 업로드 (기본 비공개)
python -m horror_shorts run jobs/<폴더> --videos none  # 빠진 영상은 정지 이미지로 대체하고 마무리
```

| 옵션 | 값 |
|---|---|
| `--place` | mart(무한마트) subway(심야 지하철) train(끝나지 않는 열차) elevator store(야간 편의점) hospital school restarea pool parking, random |
| `--place-name` | 프리셋에 없는 장소를 직접 입력 (배경 자체 생성 시 `--place`의 공간 형태를 빌려 씀) |
| `--world` | napolitan(규칙 괴담) scp(격리 기록) mixed |
| `--ending` | loop(무한 루프) become(그것이 된다) vanish(소멸) viewer(시청자 지목) twist(반전) |

## 단계별 동작
| 단계 | 하는 일 | 필요한 것 |
|---|---|---|
| script | Claude가 구조에 맞춰 대본 JSON 생성 (구조 검사 후 실패 시 1회 재생성) | `ANTHROPIC_API_KEY`. 없으면 `script_request.md`를 남기고 멈춤 → Claude Code가 `script.json`을 써 넣고 `run` |
| voice | 문장별 TTS → 앞뒤 무음 제거 → 0.3초 간격으로 이어붙임 (자막 타이밍 정확) | 무료 (edge-tts) |
| images | 장면별 9:16 이미지 | `procedural`: 무료 자체 생성(테스트용) / `kling`: `KLING_ACCESS_KEY`, `KLING_SECRET_KEY` / `manual`: `images/scene_XX.png` 직접 넣기 (`prompts.json` 참고) |
| videos | 장면마다 Kling image-to-video (첫 프레임 = 장면 이미지, 5/10초). `videos/requests.json`에 장면별 프롬프트·길이 | `kling`: API 키 / `manual`(기본): Claude Code가 **Kling 커넥터**로 만들어 `videos/scene_XX.mp4`로 넣음 / `none`: 영상 없이 |
| render | Kling 영상은 장면 길이에 맞춰 최대 1.6배 슬로우 + 깜빡임·노이즈 동일 적용. 영상 없는 장면은 느린 줌·패닝·흔들림 + 형광등 깜빡임 + 필름 노이즈 + 비네팅, 수칙 종이·수칙 카드·위반 도장 오버레이, 저음 드론 BGM + 효과음(자체 합성), 자막(ASS) | ffmpeg |
| seo | `upload.json`(제목 #shorts, 설명, 태그), `script.txt`(읽기용 대본) | |
| thumbnail | 1080x1920 썸네일 | |
| upload | YouTube Data API 비공개 업로드 + 한국어 자막 | `client_secret.json` (OAuth 데스크톱 앱) |

## 결과물 (jobs/<날짜>-<장소>/)
`final.mp4` · `thumbnail.jpg` · `upload.json` · `script.json` · `script.txt` · `subtitles.srt` · `images/` · `voice/`

예시 대본: `horror_shorts/examples/mart_loop.json` (무한마트 · 무한 루프 결말, 약 51초)

## Claude Code 세션에서 Kling 커넥터로 돌리는 흐름 (API 키 없이)
1. `make` → 대본 요청서가 나오면 Claude Code가 `script.json` 작성 → `run`
2. 이미지: `--images manual` 이면 `images/prompts.json` 대로 Kling text-to-image(9:16)로 만들어 `images/scene_XX.png`로 저장
3. 영상: `videos/requests.json` 대로 Kling image-to-video (첫 프레임 = 위 이미지) → `videos/scene_XX.mp4`
4. `run` 다시 → 렌더·자막·썸네일 완료

장면 9개 기준 Kling 사용량: 이미지 10장 + 5~10초 영상 9개.

## 자동 게시 (폰만으로 운영)
완성된 영상을 대기열에 넣고 push 하면 **GitHub Actions**(`.github/workflows/horror-upload.yml`)가 유튜브에 올립니다.
PC·클라우드 세션이 꺼져 있어도 GitHub 서버에서 올라갑니다.

```bash
python -m horror_shorts queue jobs/<폴더>     # upload_queue/<폴더>/ 에 업로드용(약 15MB) 영상·제목·썸네일
git add upload_queue && git commit -m "대기열" && git push
```

- 공개 방식: 비공개로 올린 뒤 **매일 06:00·12:00·18:00(한국시간)에 1편씩 자동 공개 예약** (`upload.schedule`, `upload.start_date`).
  예약 전에는 YouTube Studio 앱에서 확인·취소할 수 있습니다. `schedule: []` 이면 `upload.privacy` 그대로 올립니다.
- 올린 뒤 `upload_queue/<폴더>/uploaded.json`(영상 주소·공개 시각)이 기록되고 영상 파일은 대기열에서 지워집니다.
- 필요한 저장소 Secrets (GitHub → Settings → Secrets and variables → Actions → New repository secret):
  - `YOUTUBE_TOKEN_JSON` : PC의 `youtube_token.json` 내용 전체 (가장 간단), 또는
  - `YOUTUBE_REFRESH_TOKEN` + `YOUTUBE_CLIENT_ID` + `YOUTUBE_CLIENT_SECRET`
- 비밀값이 없으면 Actions는 경고만 남기고 영상은 대기열에 그대로 둡니다. 비밀값을 넣은 뒤 Actions 탭에서 `horror-upload` → Run workflow.
- 주의: 구글 OAuth 앱이 "테스트" 상태면 refresh token이 7일 뒤 만료됩니다 → OAuth 동의 화면에서 "프로덕션으로 게시".
  API 감사를 받지 않은 새 Google Cloud 프로젝트로 올린 영상은 유튜브가 비공개로 고정할 수 있으니, 기존에 쓰던 프로젝트의 클라이언트를 쓰세요.

### 폰만으로 유튜브 로그인 (PC 없이, 한 번만)
1. Google Cloud 콘솔(폰 브라우저) → 기존에 쓰던 프로젝트 → API 및 서비스 → 사용자 인증 정보 → 사용자 인증 정보 만들기 → OAuth 클라이언트 ID → 유형 **TV 및 입력 제한 기기** → 클라이언트 ID·보안 비밀 확인
2. GitHub 저장소 → Settings → Secrets and variables → Actions 에 `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET` 추가
3. Actions 탭 → `horror-youtube-auth` → Run workflow → 로그에 나온 코드를 폰에서 google.com/device 에 입력 → 허용
4. 토큰이 암호화돼 `upload_queue/.youtube_token.enc` 로 저장되고, 이후 업로드는 전부 자동

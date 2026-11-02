# 괴담 쇼츠 자동화 (horror_shorts)

규칙 괴담 쇼츠를 **대본 → 음성 → 이미지 → 렌더 → 제목·설명 → 썸네일 → (업로드)** 까지 한 번에 만듭니다.

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
| render | 느린 줌·패닝·흔들림 + 형광등 깜빡임 + 필름 노이즈 + 비네팅, 수칙 종이·수칙 카드·위반 도장 오버레이, 저음 드론 BGM + 효과음(자체 합성), 자막(ASS) | ffmpeg |
| seo | `upload.json`(제목 #shorts, 설명, 태그), `script.txt`(읽기용 대본) | |
| thumbnail | 1080x1920 썸네일 | |
| upload | YouTube Data API 비공개 업로드 + 한국어 자막 | `client_secret.json` (OAuth 데스크톱 앱) |

## 결과물 (jobs/<날짜>-<장소>/)
`final.mp4` · `thumbnail.jpg` · `upload.json` · `script.json` · `script.txt` · `subtitles.srt` · `images/` · `voice/`

예시 대본: `horror_shorts/examples/mart_loop.json` (무한마트 · 무한 루프 결말, 약 51초)

# 괴담 쇼츠 자동 제작 매뉴얼 (예약 실행용)

하루 3번(한국시간 03:47 · 09:47 · 15:47) 이 문서대로 **1편을 만들고 업로드 예약까지** 끝낸다.

### 자동 실행 방식 (중요)
- 예약 작업(트리거)은 이 세션으로 메시지를 못 보내고(ACCESS_DENIED), 새 세션에는 Kling 커넥터가 없어 쓸 수 없다.
- 그래서 **Kling이 연결된 메인 세션이 백그라운드 타이머로 스스로 깨어난다**:
  `scratchpad/autopilot_timer.sh` 를 run_in_background(timeout 7200000)로 실행 → 끝나면 출력이
  `PRODUCE ...` 이면 이 문서대로 1편 제작, `WAIT ...` 이면 타이머를 다시 실행. 제작이 끝나면 반드시 타이머를 다시 켠다.
- 타이머 스크립트가 없어졌으면(컨테이너 재시작) 다음 시각까지 남은 초를 계산해 같은 방식으로 다시 만든다.
공개 시각은 다음 빈 슬롯(06:00 · 12:00 · 18:00)이며, 항상 공개 1시간 전보다 훨씬 먼저 업로드가 끝나 있어야 한다.

사용자는 폰으로만 본다. **질문하지 말고 끝까지 진행**하고, 마지막에 한국어로 짧게 결과만 보고한다.

## 0. 준비
```bash
cd <저장소 루트>            # yamahar16/bitjurny
git fetch origin claude/horror-shorts-automation-kmdj17
git checkout claude/horror-shorts-automation-kmdj17 && git pull origin claude/horror-shorts-automation-kmdj17
pip install -q -r requirements-horror.txt cryptography
```
- 반드시 이 브랜치에서 작업하고 이 브랜치로 push 한다 (업로드 워크플로와 예약 슬롯 기록이 여기 있다).
- Kling은 claude.ai **Kling 커넥터**(`mcp__kling-ai__*`)를 쓴다. 크레딧 확인: `query_membership_and_credits` — 700 미만이면 만들지 말고 보고만.

## 1. 소재 고르기
- `horror_shorts/episodes.json` 의 `backlog` 맨 위 항목을 쓴다. backlog가 비면 디시 공포·나폴리탄 갤 반응 좋은 소재 결로 새로 3개 채운다 (done과 겹치지 않게).
- 결말(ending): loop / become / vanish / viewer / twist. 최근 2편과 같은 결말은 피한다.

## 2. 대본 (script.json 직접 작성)
기존 예시를 그대로 따라 한다: `horror_shorts/examples/doorbell_twist_ps1.json`, `arcade_loop_ps1.json`.
- 장면 9개: 기상 → 상황파악 → 수칙발견 → 수칙연출 ×4 (rule_number 1~4) → 규칙위반 → 끝.
- 나레이션 합계 45~50초 (한국어 약 4.8음절/초). 한 장면 1~3문장. 강조는 `*별표*`.
- 괴이의 대사는 큰따옴표 `"..."` 로 2~4번 (빨간 자막 + 다른 목소리로 자동 처리).
- twist 결말이면 4번 수칙을 손글씨(가짜 수칙)로, 위반 장면 rule_number는 실제로 어긴 수칙 번호.
- 1번 장면 caption 에 시각(예: "AM 3:12"), 끝 장면 caption 에 짧은 문구.
- image_prompt: 영어, 장면 묘사 + 아래 PS1 접미사. 사람은 옷을 다 입고 얼굴은 그림자로. 실존 인물·브랜드·노출 금지.
  `dark gritty late-1990s PS1 survival horror game screenshot, low-poly 3D models, blurry low-resolution pixelated textures, heavy darkness, dim flickering light, fog, muted desaturated colors, uncanny mannequin-like characters fully clothed, faces hidden in shadow, VHS grain, eerie, vertical 9:16, no text, no letters, no UI, no watermark`
  종이·간판이 나오는 장면은 `no readable words, no English text` 를 꼭 넣는다.
- video_prompt: 카메라·움직임 1문장 + `, subtle film grain, no cuts, no text`.
- 나머지 필드: title, title_options(3), hook, rulebook_title, rules[{number,text,violation_result}], violated_rule, thumbnail_text("두 줄\n문구"), thumbnail_prompt, description(2줄), hashtags(7개, #shorts 포함).

job 만들기:
```python
import json
from horror_shorts import pipeline
meta = {"place": "<영문키>", "place_name": "<한글 장소>", "world": "napolitan", "ending": "<결말>", "rules": 4,
        "target_seconds": 55, "idea": "", "images": "manual", "videos": None, "style": "ps1", "avoid": []}
job = pipeline.new_job(meta)
(job / "script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
```
그리고 `horror_shorts/examples/<place>_<ending>_ps1.json` 으로도 저장한다.
`python -m horror_shorts run jobs/<job>` → 음성 생성 후 이미지 단계에서 멈춘다 (정상).

## 3. 이미지 (Kling, 장면 9장)
- `mcp__kling-ai__text_to_image` · model `gemini-3.1-flash-image` · arguments: prompt, aspect_ratio `9:16`, img_resolution `1k` (장당 10크레딧). 9개를 한 번에 제출.
- `query_tasks` 로 완료 확인 → `urlWithoutWatermark` 를 `jobs/<job>/images/raw/scene_XX.img` 로 받는다 (curl).
- 9장을 한 장으로 이어붙여 직접 보고 검수: 읽히는 영어/글자, 게임 UI 글씨("LOADING" 등), 대본과 모순(“아무도 없었다”인데 사람이 보임), 노출, 실존 인물 닮음 → 프롬프트를 고쳐 **한 번만** 다시 만든다.
- PIL로 `images/scene_XX.png` 로 저장 → `python -m horror_shorts run jobs/<job>` → 영상 단계에서 멈추고 `videos/requests.json` 생성.

## 4. 영상 (Kling, 장면 9개, 720p)
- `mcp__kling-ai__image_to_video` · model `kling-video-v3_0_turbo` · arguments: prompt(= video_prompt), duration(requests.json 값), resolution `720p` · inputs: `[{"name":"first_image","inputType":"URL","url":<그 장면 Kling 이미지 URL>}]` (초당 8크레딧).
- 완료되면 `urlWithoutWatermark` 를 `videos/scene_XX.mp4` 로 받는다.
- 실패한 장면은 다시 제출하지 말고 그 장면만 정지 이미지로 둔다: `python -m horror_shorts run jobs/<job> --videos none`.

## 5. 렌더 · 검수
- `python -m horror_shorts run jobs/<job>` → final.mp4 (약 50~60초), thumbnail.jpg, upload.json.
- 프레임 10여 장을 뽑아 한 장으로 보고 자막·수칙 패널·빨간 대사가 정상인지 확인.

## 6. 업로드 예약
```bash
python -m horror_shorts queue jobs/<job>          # 끝에 썸네일 0.2초 붙은 업로드본
# episodes.json: backlog 맨 위 항목을 빼고 done 에 {"job","place","title","ending"} 추가
git add upload_queue horror_shorts/episodes.json horror_shorts/examples horror_shorts/presets.py
git commit -m "자동 제작: <제목>"
git push -u origin claude/horror-shorts-automation-kmdj17
```
push 하면 GitHub Actions `horror-upload` 가 업로드하고 `upload_queue/<job>/uploaded.json` 을 커밋한다.
1~3분 뒤 `git fetch` 로 uploaded.json 이 생겼는지 확인한다 (최대 10분). 실패하면 `mcp__github__get_job_logs` 로 원인을 보고 고칠 수 있으면 고쳐서 다시 push.

## 7. 보고 (한국어, 짧게)
- 제목, 공개 예약 시각(한국시간), 영상 링크(youtu.be), 이번 편 Kling 사용량·남은 크레딧
- 커버: 업로드본 맨 끝 0.2초 + 1/3 지점 0.3초에 썸네일이 들어간다(자동 커버 실험). 공개 후 https://www.youtube.com/oembed?url=https://www.youtube.com/shorts/<id>&format=json 의 thumbnail_url 이미지를 받아 썸네일로 잡혔는지 확인해 보고에 적는다
- 문제가 있었으면 무엇을 어떻게 처리했는지

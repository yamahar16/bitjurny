#!/bin/bash
# 다음 제작 시각(한국시간 03:47·09:47·15:47)까지 최대 115분 기다린 뒤 PRODUCE / WAIT 출력
python3 - <<'PY'
import time, datetime as dt
KST = dt.timezone(dt.timedelta(hours=9))
now = dt.datetime.now(KST)
cands = []
for d in range(0, 2):
    day = (now + dt.timedelta(days=d)).date()
    for hh, mm in ((3, 47), (9, 47), (15, 47)):
        t = dt.datetime(day.year, day.month, day.day, hh, mm, tzinfo=KST)
        if t > now:
            cands.append(t)
target = min(cands)
wait = (target - now).total_seconds()
chunk = min(wait, 115 * 60)
time.sleep(chunk)
left = wait - chunk
print(("PRODUCE " if left <= 0 else "WAIT ") + target.strftime("%m-%d %H:%M KST") + f" (남은 {left/60:.0f}분)")
PY

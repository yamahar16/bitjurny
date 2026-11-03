// 날짜 → 오늘의 문제, 연속 기록, 칭호 계산 (화면과 분리된 순수 로직)

// 요일별 주제 (0 = 일요일)
export const CATEGORY_BY_WEEKDAY = ["challenge", "history", "science", "korean", "economy", "life", "world"];

export const CATEGORY_LABEL = {
  history: "역사",
  science: "과학",
  korean: "우리말",
  economy: "경제",
  life: "생활",
  world: "세계",
  challenge: "일요 고난도"
};

// 문제 순환의 기준일 (월요일). 이 날부터 매주 다음 문제로 넘어가요.
const EPOCH = Date.UTC(2026, 10, 2); // 2026-11-02
const DAY_MS = 24 * 60 * 60 * 1000;

export const TITLES = [
  { min: 100, name: "상식왕" },
  { min: 60, name: "상식 달인" },
  { min: 30, name: "상식 박사" },
  { min: 15, name: "상식 탐험가" },
  { min: 5, name: "상식 새내기" },
  { min: 0, name: "상식 새싹" }
];

export function toDateKey(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

export function fromDateKey(key) {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function addDays(key, days) {
  const date = fromDateKey(key);
  date.setDate(date.getDate() + days);
  return toDateKey(date);
}

function dayNumber(key) {
  const [y, m, d] = key.split("-").map(Number);
  return Math.round((Date.UTC(y, m - 1, d) - EPOCH) / DAY_MS);
}

function mod(n, m) {
  return ((n % m) + m) % m;
}

export function categoryForDate(key) {
  return CATEGORY_BY_WEEKDAY[fromDateKey(key).getDay()];
}

export function questionForDate(bank, key) {
  const category = categoryForDate(key);
  const list = bank[category];
  const week = Math.floor(dayNumber(key) / 7);
  return list[mod(week, list.length)];
}

export function findQuestion(bank, id) {
  for (const list of Object.values(bank)) {
    const found = list.find((q) => q.id === id);
    if (found) return found;
  }
  return null;
}

// 오늘(또는 아직 안 풀었다면 어제)까지 매일 이어서 푼 날 수
export function currentStreak(daily, todayKey) {
  let key = daily[todayKey] ? todayKey : addDays(todayKey, -1);
  let streak = 0;
  while (daily[key]) {
    streak += 1;
    key = addDays(key, -1);
  }
  return streak;
}

export function longestStreak(daily) {
  const keys = Object.keys(daily).sort();
  let best = 0;
  let run = 0;
  let prev = null;
  for (const key of keys) {
    run = prev && addDays(prev, 1) === key ? run + 1 : 1;
    best = Math.max(best, run);
    prev = key;
  }
  return best;
}

export function totalCorrect(records) {
  return Object.values(records.daily).filter((r) => r.correct).length
    + Object.values(records.catchup).filter((r) => r.correct).length;
}

export function titleFor(correctCount) {
  return TITLES.find((t) => correctCount >= t.min).name;
}

export function nextTitle(correctCount) {
  const upcoming = [...TITLES].reverse().find((t) => t.min > correctCount);
  return upcoming ? { name: upcoming.name, remaining: upcoming.min - correctCount } : null;
}

// 최근 7일 중 아직 풀지 않은 가장 최근 날짜 (놓친 문제 풀기)
export function latestMissedDate(records, todayKey, days = 7) {
  for (let i = 1; i <= days; i += 1) {
    const key = addDays(todayKey, -i);
    if (!records.daily[key] && !records.catchup[key]) return key;
  }
  return null;
}

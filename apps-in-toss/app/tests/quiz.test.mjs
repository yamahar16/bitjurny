// 날짜·연속 기록 로직 테스트: node tests/quiz.test.mjs
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  addDays,
  categoryForDate,
  currentStreak,
  latestMissedDate,
  longestStreak,
  nextTitle,
  questionForDate,
  titleFor,
  totalCorrect
} from "../src/quiz.js";

const CATEGORIES = ["history", "science", "korean", "economy", "life", "world", "challenge"];
const bank = Object.fromEntries(CATEGORIES.map((c) => [c, JSON.parse(readFileSync(new URL(`../src/questions/${c}.json`, import.meta.url), "utf8"))]));

let passed = 0;
function test(name, fn) {
  fn();
  passed += 1;
  console.log(`✓ ${name}`);
}

test("요일별 주제", () => {
  assert.equal(categoryForDate("2026-11-02"), "history"); // 월
  assert.equal(categoryForDate("2026-11-03"), "science"); // 화
  assert.equal(categoryForDate("2026-11-08"), "challenge"); // 일
});

test("같은 날짜에는 항상 같은 문제, 주제도 일치", () => {
  for (let i = -400; i < 400; i += 1) {
    const key = addDays("2026-11-03", i);
    const q = questionForDate(bank, key);
    assert.ok(q, key);
    assert.equal(q.category, categoryForDate(key));
    assert.equal(questionForDate(bank, key).id, q.id);
  }
});

test("26주 동안 같은 주제의 문제가 반복되지 않음", () => {
  const seen = new Set();
  for (let i = 0; i < 26 * 7; i += 1) seen.add(questionForDate(bank, addDays("2026-11-02", i)).id);
  assert.equal(seen.size, 26 * 7);
});

test("연도·월 경계 날짜 계산", () => {
  assert.equal(addDays("2026-12-31", 1), "2027-01-01");
  assert.equal(addDays("2027-03-01", -1), "2027-02-28");
  assert.equal(addDays("2028-03-01", -1), "2028-02-29");
});

test("연속 기록: 오늘 안 풀었으면 어제까지 이어진 기록 유지", () => {
  const daily = { "2026-11-01": {}, "2026-11-02": {} };
  assert.equal(currentStreak(daily, "2026-11-03"), 2);
  daily["2026-11-03"] = {};
  assert.equal(currentStreak(daily, "2026-11-03"), 3);
  assert.equal(currentStreak(daily, "2026-11-05"), 0);
});

test("최장 기록", () => {
  const daily = { "2026-10-01": {}, "2026-10-02": {}, "2026-10-03": {}, "2026-10-10": {}, "2026-10-11": {} };
  assert.equal(longestStreak(daily), 3);
  assert.equal(longestStreak({}), 0);
});

test("놓친 문제: 최근 7일 중 안 푼 가장 최근 날짜", () => {
  const records = { daily: { "2026-11-02": {} }, catchup: { "2026-11-01": {} } };
  assert.equal(latestMissedDate(records, "2026-11-03"), "2026-10-31");
  const all = { daily: {}, catchup: {} };
  for (let i = 1; i <= 7; i += 1) all.daily[addDays("2026-11-03", -i)] = {};
  assert.equal(latestMissedDate(all, "2026-11-03"), null);
});

test("칭호", () => {
  assert.equal(titleFor(0), "상식 새싹");
  assert.equal(titleFor(5), "상식 새내기");
  assert.equal(titleFor(100), "상식왕");
  assert.deepEqual(nextTitle(3), { name: "상식 새내기", remaining: 2 });
  assert.equal(nextTitle(150), null);
  assert.equal(totalCorrect({ daily: { a: { correct: true }, b: { correct: false } }, catchup: { c: { correct: true } } }), 2);
});

console.log(`\n${passed}개 테스트 통과`);

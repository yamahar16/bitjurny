// 문제 데이터 형식 검사: 빌드 전에 자동으로 실행돼요.
import { readFileSync } from "node:fs";

const CATEGORIES = ["history", "science", "korean", "economy", "life", "world", "challenge"];
const errors = [];
const ids = new Set();
const texts = new Set();

for (const category of CATEGORIES) {
  const url = new URL(`../src/questions/${category}.json`, import.meta.url);
  let list;
  try {
    list = JSON.parse(readFileSync(url, "utf8"));
  } catch (error) {
    errors.push(`${category}.json 을 읽을 수 없어요: ${error.message}`);
    continue;
  }
  if (!Array.isArray(list) || list.length < 26) errors.push(`${category}: 최소 26문제가 필요해요 (현재 ${list?.length ?? 0})`);
  const spread = [0, 0, 0, 0];
  for (const q of list) {
    const where = `${category}/${q.id}`;
    if (!q.id || ids.has(q.id)) errors.push(`${where}: id가 없거나 중복이에요`);
    ids.add(q.id);
    if (q.category !== category) errors.push(`${where}: category 값이 ${category}가 아니에요`);
    if (typeof q.q !== "string" || !q.q.trim().endsWith("?")) errors.push(`${where}: 질문은 '?'로 끝나야 해요`);
    if (texts.has(q.q)) errors.push(`${where}: 같은 질문이 이미 있어요`);
    texts.add(q.q);
    if (!Array.isArray(q.choices) || q.choices.length !== 4) errors.push(`${where}: 보기는 4개여야 해요`);
    else if (new Set(q.choices).size !== 4) errors.push(`${where}: 보기가 중복돼요`);
    if (!Number.isInteger(q.answer) || q.answer < 0 || q.answer > 3) errors.push(`${where}: answer는 0~3이어야 해요`);
    else spread[q.answer] += 1;
    if (!q.explanation || q.explanation.length < 20) errors.push(`${where}: 해설이 너무 짧아요`);
    if (!q.source) errors.push(`${where}: 출처가 없어요`);
  }
  console.log(`${category.padEnd(9)} ${String(list.length).padStart(3)}문제  정답 위치 분포 ${spread.join("/")}`);
}

if (errors.length) {
  console.error(`\n문제 데이터 오류 ${errors.length}건:\n- ${errors.join("\n- ")}`);
  process.exit(1);
}
console.log(`\n총 ${ids.size}문제, 형식 검사 통과`);

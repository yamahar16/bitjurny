// 기록 저장: 토스 앱 안에서는 네이티브 Storage, 밖에서는 localStorage를 써요.
import { Storage } from "@apps-in-toss/web-framework";

const KEY = "haruSangsik.records.v1";

export function emptyRecords() {
  return { v: 1, daily: {}, catchup: {} };
}

function normalize(raw) {
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object") return emptyRecords();
    return {
      v: 1,
      daily: parsed.daily && typeof parsed.daily === "object" ? parsed.daily : {},
      catchup: parsed.catchup && typeof parsed.catchup === "object" ? parsed.catchup : {}
    };
  } catch {
    return emptyRecords();
  }
}

function readLocal() {
  try {
    return localStorage.getItem(KEY);
  } catch {
    return null;
  }
}

function writeLocal(value) {
  try {
    localStorage.setItem(KEY, value);
  } catch {
    // 저장 공간을 쓸 수 없는 환경이면 네이티브 저장소만 사용해요.
  }
}

export async function loadRecords() {
  try {
    const nativeValue = await Storage.getItem(KEY);
    if (nativeValue != null) {
      writeLocal(nativeValue);
      return normalize(nativeValue);
    }
  } catch (error) {
    console.warn("[storage] 네이티브 저장소를 사용할 수 없어요.", error);
  }
  const local = readLocal();
  return local ? normalize(local) : emptyRecords();
}

let queue = Promise.resolve();

export function saveRecords(records) {
  const value = JSON.stringify(records);
  writeLocal(value);
  queue = queue
    .then(() => Storage.setItem(KEY, value))
    .catch((error) => console.warn("[storage] 네이티브 저장 실패", error));
  return queue;
}

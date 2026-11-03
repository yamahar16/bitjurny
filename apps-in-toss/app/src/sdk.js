// 앱인토스 SDK 호출을 한곳에 모아, 토스 앱 밖(브라우저)에서도 안전하게 동작하게 해요.
import {
  Environment,
  Share,
  TossAds,
  generateHapticFeedback,
  getTossShareLink,
  loadFullScreenAd,
  showFullScreenAd
} from "@apps-in-toss/web-framework";

export const APP_NAME = "harusangsik";

// 콘솔에서 발급한 광고 그룹 ID를 .env에 넣으면 실제 광고가 나가요.
// 비워 두면 앱인토스 테스트 광고 ID를 써요. (실제 ID로 테스트하면 정책 위반이에요)
const AD_IDS = {
  rewarded: import.meta.env.VITE_AD_REWARDED_ID || "ait-ad-test-rewarded-id",
  banner: import.meta.env.VITE_AD_BANNER_ID || "ait-ad-test-banner-id"
};

function safe(fn, fallback) {
  try {
    return fn();
  } catch {
    return fallback;
  }
}

// ---------- 진입 링크 ----------
// 정식: intoss://harusangsik?c=<문제ID>&r=<1|0>
// 콘솔 QR 테스트: ...?_deploymentId=...&queryParams={"c":"...","r":"1"}
export function readLaunchParams() {
  const params = {};
  const sources = [safe(() => Environment.initialURL, ""), window.location.href];
  for (const source of sources) {
    if (!source) continue;
    const queryIndex = source.indexOf("?");
    if (queryIndex < 0) continue;
    const search = new URLSearchParams(source.slice(queryIndex + 1).split("#")[0]);
    for (const [key, value] of search) {
      if (key === "queryParams") {
        const nested = safe(() => JSON.parse(value), null);
        if (nested && typeof nested === "object") Object.assign(params, nested);
      } else if (!(key in params)) {
        params[key] = value;
      }
    }
  }
  return params;
}

// ---------- 햅틱 ----------
export function haptic(type) {
  safe(() => generateHapticFeedback({ type }).catch(() => {}));
}

// ---------- 공유 ----------
export async function shareChallenge({ questionId, correct, message }) {
  const path = `intoss://${APP_NAME}?c=${encodeURIComponent(questionId)}&r=${correct ? 1 : 0}`;
  let link = path;
  try {
    link = await getTossShareLink(path);
  } catch (error) {
    console.warn("[share] 공유 링크 생성 실패", error);
  }
  const text = `${message}\n${link}`;
  try {
    await Share.sendMessage({ message: text });
    return "shared";
  } catch (error) {
    console.warn("[share] 토스 공유 시트 실패, 브라우저 공유로 대체", error);
  }
  if (navigator.share) {
    try {
      await navigator.share({ text });
      return "shared";
    } catch {
      return "cancelled";
    }
  }
  try {
    await navigator.clipboard.writeText(text);
    return "copied";
  } catch {
    return "failed";
  }
}

// ---------- 보상형 광고 ----------
const rewarded = { supported: false, loaded: false, failed: false, unregister: null, listeners: new Set() };

function notifyRewarded() {
  rewarded.listeners.forEach((listener) => listener());
}

export function onRewardedChange(listener) {
  rewarded.listeners.add(listener);
  return () => rewarded.listeners.delete(listener);
}

export function rewardedStatus() {
  if (!rewarded.supported || rewarded.failed) return "free"; // 광고를 쓸 수 없으면 무료로 열어줘요
  return rewarded.loaded ? "ready" : "loading";
}

export function preloadRewarded() {
  rewarded.supported = safe(() => loadFullScreenAd.isSupported(), false);
  if (!rewarded.supported) return notifyRewarded();
  rewarded.loaded = false;
  rewarded.failed = false;
  rewarded.unregister?.();
  rewarded.unregister = safe(() => loadFullScreenAd({
    options: { adGroupId: AD_IDS.rewarded },
    onEvent: (event) => {
      if (event.type === "loaded") {
        rewarded.loaded = true;
        notifyRewarded();
      }
    },
    onError: (error) => {
      console.warn("[ads] 보상형 광고 로드 실패", error);
      rewarded.failed = true;
      notifyRewarded();
    }
  }), null);
  notifyRewarded();
}

// 광고를 끝까지 본 경우에만 true로 끝나요.
export function showRewarded() {
  return new Promise((resolve) => {
    if (rewardedStatus() === "free") return resolve(true);
    let earned = false;
    try {
      showFullScreenAd({
      options: { adGroupId: AD_IDS.rewarded },
      onEvent: (event) => {
        if (event.type === "userEarnedReward") earned = true;
        if (event.type === "dismissed") {
          rewarded.loaded = false;
          resolve(earned);
          preloadRewarded();
        }
      },
      onError: (error) => {
        console.warn("[ads] 보상형 광고 표시 실패", error);
        rewarded.loaded = false;
        resolve(false);
        preloadRewarded();
      }
      });
    } catch (error) {
      console.warn("[ads] 보상형 광고 호출 실패", error);
      resolve(false);
    }
  });
}

// ---------- 배너 광고 ----------
let bannerReady = null;

function initBanner() {
  if (bannerReady) return bannerReady;
  bannerReady = new Promise((resolve) => {
    if (!safe(() => TossAds.initialize.isSupported(), false)) return resolve(false);
    try {
      TossAds.initialize({
        callbacks: {
          onInitialized: () => resolve(true),
          onInitializationFailed: (error) => {
            console.warn("[ads] 배너 초기화 실패", error);
            resolve(false);
          }
        }
      });
    } catch (error) {
      console.warn("[ads] 배너 초기화 호출 실패", error);
      resolve(false);
    }
  });
  return bannerReady;
}

export async function attachBanner(container) {
  if (!(await initBanner())) return null;
  if (!container.isConnected) return null;
  container.classList.add("banner-slot--active");
  const result = safe(() => TossAds.attachBanner(AD_IDS.banner, container, {
    theme: "light",
    tone: "grey",
    variant: "card",
    callbacks: {
      onNoFill: () => container.classList.remove("banner-slot--active"),
      onAdFailedToRender: () => container.classList.remove("banner-slot--active")
    }
  }), null);
  if (!result) container.classList.remove("banner-slot--active");
  return result;
}

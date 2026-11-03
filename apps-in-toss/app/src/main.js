import { QUESTION_BANK } from "./questions/index.js";
import {
  CATEGORY_LABEL,
  addDays,
  categoryForDate,
  currentStreak,
  findQuestion,
  fromDateKey,
  latestMissedDate,
  longestStreak,
  nextTitle,
  questionForDate,
  titleFor,
  toDateKey,
  totalCorrect
} from "./quiz.js";
import { loadRecords, saveRecords } from "./storage.js";
import {
  attachBanner,
  haptic,
  onRewardedChange,
  preloadRewarded,
  readLaunchParams,
  rewardedStatus,
  shareChallenge,
  showRewarded
} from "./sdk.js";

const app = document.getElementById("app");
const toastEl = document.getElementById("toast");
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const state = {
  records: null,
  today: toDateKey(new Date()),
  challenge: null, // { question, friendCorrect, answer }
  calendarMonth: null,
  banner: null
};

// ---------- 유틸 ----------
function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function formatDate(key, withWeekday = true) {
  const date = fromDateKey(key);
  const text = `${date.getMonth() + 1}월 ${date.getDate()}일`;
  return withWeekday ? `${text} ${WEEKDAYS[date.getDay()]}요일` : text;
}

let toastTimer;
function toast(message) {
  toastEl.textContent = message;
  toastEl.classList.add("toast--visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove("toast--visible"), 2200);
}

function persist() {
  saveRecords(state.records);
}

// ---------- 라우팅 (토스 내비게이션 바의 뒤로가기와 연동) ----------
function go(hash, { replace = false } = {}) {
  if (replace) {
    history.replaceState(null, "", hash);
    render();
  } else if (location.hash === hash) {
    render();
  } else {
    location.hash = hash;
  }
}

function currentRoute() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  return { name: parts[0] || "home", param: parts[1] };
}

// ---------- 공통 조각 ----------
function headerHtml() {
  const streak = currentStreak(state.records.daily, state.today);
  return `
    <header class="top">
      <div>
        <p class="top__date">${formatDate(state.today)}</p>
        <h1 class="top__brand">하루상식</h1>
      </div>
      <a class="streak ${streak ? "" : "streak--zero"}" href="#/calendar" aria-label="연속 ${streak}일, 도장 달력 보기">
        <span aria-hidden="true">🔥</span> ${streak}일째
      </a>
    </header>`;
}

function questionHtml(question, { label, selected = null }) {
  const answered = selected !== null;
  const choices = question.choices.map((choice, index) => {
    let cls = "choice";
    let mark = "";
    if (answered) {
      if (index === question.answer) { cls += " choice--correct"; mark = "정답"; }
      else if (index === selected) { cls += " choice--wrong"; mark = "내 선택"; }
      else cls += " choice--dim";
    }
    return `
      <button class="${cls}" type="button" data-choice="${index}" ${answered ? "disabled" : ""}>
        <span class="choice__num">${index + 1}</span>
        <span class="choice__text">${escapeHtml(choice)}</span>
        ${mark ? `<span class="choice__mark">${mark}</span>` : ""}
      </button>`;
  }).join("");
  return `
    <section class="card question">
      <p class="chip">${escapeHtml(label)}</p>
      <h2 class="question__text">${escapeHtml(question.q)}</h2>
      <div class="choices">${choices}</div>
    </section>`;
}

function verdictHtml(correct) {
  return `
    <div class="verdict ${correct ? "verdict--ok" : "verdict--no"}" role="status">
      <span class="stamp" aria-hidden="true">${correct ? "정답" : "아쉬움"}</span>
      <p class="verdict__text">${correct ? "맞혔어요! 도장 하나 쾅" : "아쉽지만 틀렸어요"}</p>
    </div>`;
}

function explanationHtml(question) {
  return `
    <section class="card explain">
      <p class="explain__title">알고 보면</p>
      <p class="explain__body">${escapeHtml(question.explanation)}</p>
      <p class="explain__source">출처 · ${escapeHtml(question.source)}</p>
    </section>`;
}

function bannerSlotHtml() {
  return `<div class="banner-slot" id="bannerSlot" aria-label="광고"></div>`;
}

function catchupButtonHtml() {
  const missed = latestMissedDate(state.records, state.today);
  if (!missed) return "";
  const status = rewardedStatus();
  const label = status === "ready" ? "광고 보고 놓친 문제 풀기" : status === "loading" ? "놓친 문제 준비 중…" : "놓친 문제 풀기";
  return `
    <button class="btn btn--ghost" type="button" data-action="catchup" data-date="${missed}" ${status === "loading" ? "disabled" : ""}>
      ${label}
      <span class="btn__sub">${formatDate(missed)} · ${CATEGORY_LABEL[categoryForDate(missed)]}</span>
    </button>`;
}

// ---------- 화면: 오늘의 문제 ----------
function renderHome() {
  const question = questionForDate(QUESTION_BANK, state.today);
  const record = state.records.daily[state.today];
  const label = `오늘의 문제 · ${CATEGORY_LABEL[categoryForDate(state.today)]}`;

  if (!record) {
    app.innerHTML = `${headerHtml()}${questionHtml(question, { label })}
      <p class="hint">하루에 딱 한 문제예요. 신중하게 골라 주세요.</p>`;
    app.querySelectorAll("[data-choice]").forEach((button) => {
      button.addEventListener("click", () => answerDaily(question, Number(button.dataset.choice)));
    });
    return;
  }

  const correct = record.correct;
  const correctCount = totalCorrect(state.records);
  const upcoming = nextTitle(correctCount);
  app.innerHTML = `${headerHtml()}
    ${verdictHtml(correct)}
    ${questionHtml(question, { label, selected: record.choice })}
    ${explanationHtml(question)}
    <section class="actions">
      <button class="btn btn--primary" type="button" data-action="share">친구에게 이 문제 내기</button>
      <button class="btn btn--secondary" type="button" data-action="calendar">
        도장 달력 보기 <span class="btn__sub">${titleFor(correctCount)}${upcoming ? ` · ${upcoming.name}까지 ${upcoming.remaining}문제` : ""}</span>
      </button>
      ${catchupButtonHtml()}
    </section>
    <p class="hint">내일 0시에 새 문제가 열려요.</p>
    ${bannerSlotHtml()}`;
  bindResultActions(question, correct);
  mountBanner();
}

function answerDaily(question, choice) {
  if (state.records.daily[state.today]) return;
  const correct = choice === question.answer;
  state.records.daily[state.today] = { id: question.id, choice, correct, at: Date.now() };
  persist();
  haptic(correct ? "success" : "error");
  render();
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function bindResultActions(question, correct) {
  app.querySelector('[data-action="share"]')?.addEventListener("click", () => share(question, correct));
  app.querySelector('[data-action="calendar"]')?.addEventListener("click", () => go("#/calendar"));
  app.querySelector('[data-action="home"]')?.addEventListener("click", () => go("#/", { replace: true }));
  app.querySelector('[data-action="catchup"]')?.addEventListener("click", async (event) => {
    const date = event.currentTarget.dataset.date;
    const ok = await showRewarded();
    if (ok) go(`#/catchup/${date}`);
    else toast("광고를 끝까지 보면 놓친 문제를 풀 수 있어요.");
  });
}

async function share(question, correct) {
  const message = `[하루상식] ${CATEGORY_LABEL[question.category]} 문제, 맞힐 수 있어요?\n"${question.q}"\n나는 ${correct ? "맞혔어요 ⭕" : "틀렸어요 ❌"}`;
  const result = await shareChallenge({ questionId: question.id, correct, message });
  if (result === "copied") toast("링크를 복사했어요. 친구에게 붙여넣어 보내 주세요.");
  if (result === "failed") toast("공유하지 못했어요. 잠시 후 다시 시도해 주세요.");
}

// ---------- 화면: 놓친 문제 ----------
function renderCatchup(dateKey) {
  const valid = dateKey && dateKey < state.today && dateKey >= addDays(state.today, -7) && !state.records.daily[dateKey];
  if (!valid) return go("#/", { replace: true });
  const question = questionForDate(QUESTION_BANK, dateKey);
  const record = state.records.catchup[dateKey];
  const label = `놓친 문제 · ${formatDate(dateKey)} · ${CATEGORY_LABEL[categoryForDate(dateKey)]}`;

  if (!record) {
    app.innerHTML = `${headerHtml()}${questionHtml(question, { label })}
      <p class="hint">놓친 문제는 연속 기록에는 들어가지 않지만, 정답 수에는 더해져요.</p>`;
    app.querySelectorAll("[data-choice]").forEach((button) => {
      button.addEventListener("click", () => {
        const choice = Number(button.dataset.choice);
        const correct = choice === question.answer;
        state.records.catchup[dateKey] = { id: question.id, choice, correct, at: Date.now() };
        persist();
        haptic(correct ? "success" : "error");
        render();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
    return;
  }

  app.innerHTML = `${headerHtml()}
    ${verdictHtml(record.correct)}
    ${questionHtml(question, { label, selected: record.choice })}
    ${explanationHtml(question)}
    <section class="actions">
      <button class="btn btn--primary" type="button" data-action="share">친구에게 이 문제 내기</button>
      <button class="btn btn--secondary" type="button" data-action="home">오늘의 문제로 돌아가기</button>
    </section>
    ${bannerSlotHtml()}`;
  bindResultActions(question, record.correct);
  mountBanner();
}

// ---------- 화면: 지난 문제 다시 보기 ----------
function renderDay(dateKey) {
  const record = state.records.daily[dateKey] || state.records.catchup[dateKey];
  const question = record && findQuestion(QUESTION_BANK, record.id);
  if (!question) return go("#/calendar", { replace: true });
  const label = `${formatDate(dateKey)} · ${CATEGORY_LABEL[question.category]}`;
  app.innerHTML = `${headerHtml()}
    ${verdictHtml(record.correct)}
    ${questionHtml(question, { label, selected: record.choice })}
    ${explanationHtml(question)}
    <section class="actions">
      <button class="btn btn--primary" type="button" data-action="share">친구에게 이 문제 내기</button>
    </section>`;
  bindResultActions(question, record.correct);
}

// ---------- 화면: 친구가 보낸 문제 ----------
function renderChallenge() {
  const challenge = state.challenge;
  if (!challenge) return go("#/", { replace: true });
  const { question, friendCorrect } = challenge;

  if (challenge.answer == null) {
    app.innerHTML = `${headerHtml()}
      <section class="friend">
        <p class="friend__title">친구가 보낸 문제예요</p>
        <p class="friend__body">친구는 이미 풀었어요. 결과는 풀고 나서 알려드릴게요.</p>
      </section>
      ${questionHtml(question, { label: `${CATEGORY_LABEL[question.category]} 문제` })}`;
    app.querySelectorAll("[data-choice]").forEach((button) => {
      button.addEventListener("click", () => {
        const choice = Number(button.dataset.choice);
        const correct = choice === question.answer;
        challenge.answer = choice;
        // 친구가 보낸 문제가 오늘의 문제라면 오늘 기록으로도 남겨요.
        if (question.id === questionForDate(QUESTION_BANK, state.today).id && !state.records.daily[state.today]) {
          state.records.daily[state.today] = { id: question.id, choice, correct, at: Date.now() };
          persist();
        }
        haptic(correct ? "success" : "error");
        render();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
    });
    return;
  }

  const correct = challenge.answer === question.answer;
  const summary = correct && friendCorrect ? "둘 다 정답! 실력이 막상막하예요."
    : correct ? "친구는 틀렸는데 나는 맞혔어요!"
      : friendCorrect ? "이번엔 친구가 한 수 위였어요."
        : "둘 다 틀렸어요. 이제 둘 다 알게 됐네요!";
  const todayDone = Boolean(state.records.daily[state.today]);
  app.innerHTML = `${headerHtml()}
    <section class="card versus">
      <div class="versus__row">
        <div class="versus__who"><span>친구</span><strong class="${friendCorrect ? "ok" : "no"}">${friendCorrect ? "⭕ 정답" : "❌ 오답"}</strong></div>
        <div class="versus__who"><span>나</span><strong class="${correct ? "ok" : "no"}">${correct ? "⭕ 정답" : "❌ 오답"}</strong></div>
      </div>
      <p class="versus__summary">${summary}</p>
    </section>
    ${questionHtml(question, { label: `${CATEGORY_LABEL[question.category]} 문제`, selected: challenge.answer })}
    ${explanationHtml(question)}
    <section class="actions">
      <button class="btn btn--primary" type="button" data-action="home">${todayDone ? "오늘 결과 보기" : "오늘의 문제 풀기"}</button>
      <button class="btn btn--secondary" type="button" data-action="share">나도 친구에게 이 문제 내기</button>
    </section>`;
  bindResultActions(question, correct);
}

// ---------- 화면: 도장 달력 ----------
function renderCalendar() {
  const todayDate = fromDateKey(state.today);
  if (!state.calendarMonth) state.calendarMonth = { y: todayDate.getFullYear(), m: todayDate.getMonth() };
  const { y, m } = state.calendarMonth;
  const first = new Date(y, m, 1);
  const daysInMonth = new Date(y, m + 1, 0).getDate();
  const cells = [];
  for (let i = 0; i < first.getDay(); i += 1) cells.push('<span class="day day--empty"></span>');
  for (let d = 1; d <= daysInMonth; d += 1) {
    const key = toDateKey(new Date(y, m, d));
    const daily = state.records.daily[key];
    const late = !daily && state.records.catchup[key];
    const record = daily || late;
    let cls = "day";
    let inner = `<span class="day__num">${d}</span>`;
    if (record?.correct) { cls += late ? " day--late" : " day--stamp"; inner += '<span class="day__stamp" aria-hidden="true">정답</span>'; }
    else if (record) cls += " day--played";
    if (key === state.today) cls += " day--today";
    const label = `${m + 1}월 ${d}일${record ? (record.correct ? " 정답" : " 오답") : ""}`;
    cells.push(record
      ? `<button class="${cls}" type="button" data-day="${key}" aria-label="${label}">${inner}</button>`
      : `<span class="${cls}" aria-label="${label}">${inner}</span>`);
  }

  const correctCount = totalCorrect(state.records);
  const upcoming = nextTitle(correctCount);
  const isCurrentMonth = y === todayDate.getFullYear() && m === todayDate.getMonth();
  app.innerHTML = `${headerHtml()}
    <section class="card stats">
      <div class="stats__title">
        <p class="chip">${titleFor(correctCount)}</p>
        ${upcoming ? `<p class="stats__next">${upcoming.name}까지 정답 ${upcoming.remaining}개 남았어요</p>` : '<p class="stats__next">최고 칭호에 도달했어요!</p>'}
      </div>
      <div class="stats__grid">
        <div><strong>${currentStreak(state.records.daily, state.today)}일</strong><span>연속 기록</span></div>
        <div><strong>${longestStreak(state.records.daily)}일</strong><span>최장 기록</span></div>
        <div><strong>${correctCount}개</strong><span>누적 정답</span></div>
      </div>
    </section>
    <section class="card calendar">
      <div class="calendar__bar">
        <button class="icon-btn" type="button" data-month="-1" aria-label="이전 달">‹</button>
        <h2>${y}년 ${m + 1}월</h2>
        <button class="icon-btn" type="button" data-month="1" aria-label="다음 달" ${isCurrentMonth ? "disabled" : ""}>›</button>
      </div>
      <div class="weekdays" aria-hidden="true">${WEEKDAYS.map((w) => `<span>${w}</span>`).join("")}</div>
      <div class="days">${cells.join("")}</div>
      <p class="calendar__legend"><span class="legend legend--stamp"></span>정답 <span class="legend legend--played"></span>오답 <span class="legend legend--late"></span>놓친 문제 정답</p>
    </section>
    <p class="hint">푼 날짜를 누르면 문제와 해설을 다시 볼 수 있어요.</p>
    ${bannerSlotHtml()}`;

  app.querySelectorAll("[data-month]").forEach((button) => button.addEventListener("click", () => {
    const next = new Date(y, m + Number(button.dataset.month), 1);
    state.calendarMonth = { y: next.getFullYear(), m: next.getMonth() };
    render();
  }));
  app.querySelectorAll("[data-day]").forEach((button) => button.addEventListener("click", () => go(`#/day/${button.dataset.day}`)));
  mountBanner();
}

// ---------- 렌더 ----------
function mountBanner() {
  const slot = document.getElementById("bannerSlot");
  if (!slot) return;
  attachBanner(slot).then((banner) => {
    if (!banner) return;
    if (!slot.isConnected) banner.destroy();
    else state.banner = banner;
  });
}

function render() {
  state.today = toDateKey(new Date());
  state.banner?.destroy?.();
  state.banner = null;
  const route = currentRoute();
  if (route.name === "calendar") renderCalendar();
  else if (route.name === "day") renderDay(route.param);
  else if (route.name === "catchup") renderCatchup(route.param);
  else if (route.name === "challenge") renderChallenge();
  else renderHome();
}

async function init() {
  app.innerHTML = '<div class="loading">오늘의 문제를 불러오고 있어요</div>';
  state.records = await loadRecords();

  const params = readLaunchParams();
  const sharedQuestion = params.c ? findQuestion(QUESTION_BANK, params.c) : null;
  if (sharedQuestion) {
    state.challenge = { question: sharedQuestion, friendCorrect: params.r === "1", answer: null };
    history.replaceState(null, "", "#/challenge");
  } else if (location.hash) {
    history.replaceState(null, "", "#/");
  }

  window.addEventListener("hashchange", render);
  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState === "visible" && toDateKey(new Date()) !== state.today) render();
  });
  onRewardedChange(() => {
    const route = currentRoute().name;
    if (route === "home") {
      const button = app.querySelector('[data-action="catchup"]');
      if (button) button.outerHTML = catchupButtonHtml();
      bindResultActions(questionForDate(QUESTION_BANK, state.today), state.records.daily[state.today]?.correct);
    }
  });
  render();
  preloadRewarded();
}

init();

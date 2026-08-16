(() => {
  "use strict";

  // ==============================
  // APP STATE
  // ==============================
  const STORAGE_KEY = "vocalLessonJournalRecords";
  const state = {
    records: [],
    selectedDate: toDateKey(new Date()),
    visibleYear: new Date().getFullYear(),
    visibleMonth: new Date().getMonth(),
    editingId: null
  };

  const elements = {};
  let toastTimer;

  function initApp() {
    cacheElements();
    state.records = loadRecords();
    bindEvents();
    renderCalendar();
    renderSelectedDate();
    renderLessonRecords();
  }

  function cacheElements() {
    ["calendarTitle", "calendarGrid", "selectedDateTitle", "recordsList", "previousMonth",
      "nextMonth", "todayButton", "addRecordButton", "exportButton", "importButton",
      "importFile", "lessonFormModal", "lessonForm", "formTitle", "formDateLabel",
      "studentName", "studentNameError", "saveButton", "detailModal", "detailTitle",
      "detailContent", "toast"].forEach((id) => { elements[id] = document.getElementById(id); });
  }

  function bindEvents() {
    elements.previousMonth.addEventListener("click", () => changeMonth(-1));
    elements.nextMonth.addEventListener("click", () => changeMonth(1));
    elements.todayButton.addEventListener("click", goToToday);
    elements.addRecordButton.addEventListener("click", () => openLessonForm());
    elements.lessonForm.addEventListener("submit", saveLessonRecord);
    elements.exportButton.addEventListener("click", exportBackup);
    elements.importButton.addEventListener("click", () => elements.importFile.click());
    elements.importFile.addEventListener("change", (event) => {
      const [file] = event.target.files;
      if (file) importBackup(file);
      event.target.value = "";
    });
    document.querySelectorAll("[data-close-form]").forEach((button) => button.addEventListener("click", closeLessonForm));
    document.querySelectorAll("[data-close-detail]").forEach((button) => button.addEventListener("click", () => elements.detailModal.close()));
    elements.lessonFormModal.addEventListener("click", closeOnBackdrop);
    elements.detailModal.addEventListener("click", closeOnBackdrop);
  }

  // ==============================
  // LOCAL STORAGE
  // ==============================
  function loadRecords() {
    try {
      const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
      return Array.isArray(parsed) ? parsed.filter(isValidRecord) : [];
    } catch (error) {
      console.error("저장 데이터를 읽지 못했습니다.", error);
      showToast("저장된 데이터를 읽지 못했습니다.");
      return [];
    }
  }

  function saveRecords() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state.records));
      return true;
    } catch (error) {
      console.error("데이터 저장에 실패했습니다.", error);
      alert("데이터를 저장하지 못했습니다. 브라우저 저장 공간을 확인해주세요.");
      return false;
    }
  }

  function isValidRecord(record) {
    return Boolean(record && typeof record === "object" && typeof record.id === "string" &&
      /^\d{4}-\d{2}-\d{2}$/.test(record.date) && typeof record.studentName === "string");
  }

  // ==============================
  // CALENDAR
  // ==============================
  function renderCalendar() {
    const { visibleYear: year, visibleMonth: month } = state;
    elements.calendarTitle.textContent = `${year}년 ${month + 1}월`;
    elements.calendarGrid.replaceChildren();

    const firstWeekday = new Date(year, month, 1).getDay();
    const firstCellDate = new Date(year, month, 1 - firstWeekday);
    const recordCounts = state.records.reduce((counts, record) => {
      counts[record.date] = (counts[record.date] || 0) + 1;
      return counts;
    }, {});

    for (let index = 0; index < 42; index += 1) {
      const date = new Date(firstCellDate.getFullYear(), firstCellDate.getMonth(), firstCellDate.getDate() + index);
      const dateKey = toDateKey(date);
      const button = document.createElement("button");
      button.type = "button";
      button.className = "calendar-day";
      button.setAttribute("role", "gridcell");
      button.setAttribute("aria-label", formatFullDate(dateKey));
      button.textContent = date.getDate();
      if (date.getMonth() !== month) button.classList.add("outside");
      if (dateKey === toDateKey(new Date())) button.classList.add("today");
      if (dateKey === state.selectedDate) {
        button.classList.add("selected");
        button.setAttribute("aria-selected", "true");
      }
      if (recordCounts[dateKey]) {
        const badge = document.createElement("span");
        badge.className = `record-badge${recordCounts[dateKey] > 1 ? " count" : ""}`;
        badge.textContent = recordCounts[dateKey] > 1 ? String(recordCounts[dateKey]) : "";
        badge.setAttribute("aria-label", `레슨 ${recordCounts[dateKey]}개`);
        button.appendChild(badge);
      }
      button.addEventListener("click", () => selectDate(dateKey));
      elements.calendarGrid.appendChild(button);
    }
  }

  function changeMonth(offset) {
    const next = new Date(state.visibleYear, state.visibleMonth + offset, 1);
    state.visibleYear = next.getFullYear();
    state.visibleMonth = next.getMonth();
    renderCalendar();
  }

  function goToToday() {
    const today = new Date();
    state.visibleYear = today.getFullYear();
    state.visibleMonth = today.getMonth();
    selectDate(toDateKey(today));
  }

  function selectDate(dateKey) {
    state.selectedDate = dateKey;
    const date = fromDateKey(dateKey);
    state.visibleYear = date.getFullYear();
    state.visibleMonth = date.getMonth();
    renderCalendar();
    renderSelectedDate();
    renderLessonRecords();
  }

  // ==============================
  // LESSON RECORD CRUD
  // ==============================
  function addRecord(record) {
    state.records.push(record);
    return saveRecords();
  }

  function updateRecord(updatedRecord) {
    const index = state.records.findIndex((record) => record.id === updatedRecord.id);
    if (index < 0) return false;
    state.records[index] = updatedRecord;
    return saveRecords();
  }

  function editLessonRecord(id) {
    const record = state.records.find((item) => item.id === id);
    if (record) openLessonForm(record);
  }

  function deleteLessonRecord(id) {
    const record = state.records.find((item) => item.id === id);
    if (!record || !confirm("이 레슨 기록을 삭제할까요?\n삭제한 기록은 되돌릴 수 없습니다.")) return;
    const previous = state.records;
    state.records = state.records.filter((item) => item.id !== id);
    if (!saveRecords()) {
      state.records = previous;
      return;
    }
    refreshViews();
    showToast("레슨 기록을 삭제했습니다.");
  }

  // ==============================
  // FORM
  // ==============================
  function openLessonForm(record = null) {
    state.editingId = record?.id || null;
    elements.lessonForm.reset();
    clearNameError();
    elements.formTitle.textContent = record ? "레슨 기록 수정" : "레슨 기록 추가";
    elements.formDateLabel.textContent = formatFullDate(state.selectedDate);
    elements.saveButton.textContent = record ? "수정 저장" : "저장";
    if (record) {
      ["studentName", "lessonTime", "lessonNumber", "songs", "lessonContent", "goodPoints",
        "improvementPoints", "homework", "instructorMemo"].forEach((name) => {
        elements.lessonForm.elements[name].value = record[name] ?? "";
      });
    }
    elements.lessonFormModal.showModal();
    requestAnimationFrame(() => elements.studentName.focus());
  }

  function closeLessonForm() {
    elements.lessonFormModal.close();
    state.editingId = null;
    elements.lessonForm.reset();
    clearNameError();
  }

  function saveLessonRecord(event) {
    event.preventDefault();
    const formData = new FormData(elements.lessonForm);
    const studentName = String(formData.get("studentName") || "").trim();
    if (!studentName) {
      elements.studentName.classList.add("invalid");
      elements.studentNameError.textContent = "학생 이름을 입력해주세요.";
      elements.studentName.focus();
      return;
    }
    clearNameError();
    const existing = state.records.find((record) => record.id === state.editingId);
    const now = new Date().toISOString();
    const record = {
      id: existing?.id || createId(),
      date: existing?.date || state.selectedDate,
      studentName,
      lessonTime: String(formData.get("lessonTime") || ""),
      lessonNumber: formData.get("lessonNumber") ? Number(formData.get("lessonNumber")) : null,
      songs: String(formData.get("songs") || "").trim(),
      lessonContent: String(formData.get("lessonContent") || "").trim(),
      goodPoints: String(formData.get("goodPoints") || "").trim(),
      improvementPoints: String(formData.get("improvementPoints") || "").trim(),
      homework: String(formData.get("homework") || "").trim(),
      instructorMemo: String(formData.get("instructorMemo") || "").trim(),
      createdAt: existing?.createdAt || now,
      updatedAt: now
    };
    const succeeded = existing ? updateRecord(record) : addRecord(record);
    if (!succeeded) return;
    closeLessonForm();
    refreshViews();
    showToast(existing ? "레슨 기록을 수정했습니다." : "레슨 기록을 저장했습니다.");
  }

  function clearNameError() {
    elements.studentName.classList.remove("invalid");
    elements.studentNameError.textContent = "";
  }

  // ==============================
  // BACKUP / RESTORE
  // ==============================
  function exportBackup() {
    const payload = { app: "vocalLessonJournal", version: 1, exportedAt: new Date().toISOString(), records: state.records };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `vocal_lesson_backup_${toDateKey(new Date())}.json`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
    showToast("백업 파일을 다운로드했습니다.");
  }

  async function importBackup(file) {
    try {
      const parsed = JSON.parse(await file.text());
      const imported = Array.isArray(parsed) ? parsed : parsed?.records;
      if (!Array.isArray(imported) || !imported.every(isValidRecord)) throw new Error("Invalid backup");
      if (!confirm("백업 데이터를 불러오시겠습니까?\n현재 저장된 데이터와 병합됩니다.")) return;
      const merged = new Map(state.records.map((record) => [record.id, record]));
      imported.forEach((record) => merged.set(record.id, record));
      const previous = state.records;
      state.records = [...merged.values()];
      if (!saveRecords()) {
        state.records = previous;
        return;
      }
      refreshViews();
      showToast(`${imported.length}개의 백업 기록을 불러왔습니다.`);
    } catch (error) {
      console.error("백업 복원 오류", error);
      alert("올바른 레슨일지 백업 파일이 아닙니다.");
    }
  }

  // ==============================
  // UI RENDERING
  // ==============================
  function renderSelectedDate() {
    elements.selectedDateTitle.textContent = formatFullDate(state.selectedDate);
  }

  function renderLessonRecords() {
    elements.recordsList.replaceChildren();
    const records = state.records
      .filter((record) => record.date === state.selectedDate)
      .sort((a, b) => (a.lessonTime || "99:99").localeCompare(b.lessonTime || "99:99") || a.studentName.localeCompare(b.studentName, "ko"));

    if (!records.length) {
      const empty = createElement("div", "empty-state");
      empty.append(createElement("p", "", "이 날짜에는 아직 레슨 기록이 없습니다."));
      const button = createElement("button", "button button-primary", "+ 첫 레슨 기록 작성");
      button.type = "button";
      button.addEventListener("click", () => openLessonForm());
      empty.appendChild(button);
      elements.recordsList.appendChild(empty);
      return;
    }

    records.forEach((record) => elements.recordsList.appendChild(createRecordCard(record)));
  }

  function createRecordCard(record) {
    const card = createElement("article", "record-card");
    const top = createElement("div", "record-top");
    top.append(
      createElement("span", "record-time", record.lessonTime || "시간 미정"),
      createElement("span", "record-name", record.studentName)
    );
    if (record.lessonNumber) top.appendChild(createElement("span", "record-number", `${record.lessonNumber}회차`));
    card.appendChild(top);
    if (record.songs) card.appendChild(createElement("p", "record-song", record.songs));
    if (record.lessonContent) {
      const preview = record.lessonContent.length > 110 ? `${record.lessonContent.slice(0, 110)}…` : record.lessonContent;
      card.appendChild(createElement("p", "record-preview", preview));
    }
    const actions = createElement("div", "record-actions");
    [["상세보기", "button button-secondary", () => showRecordDetail(record.id)],
      ["수정", "button button-secondary", () => editLessonRecord(record.id)],
      ["삭제", "button button-danger", () => deleteLessonRecord(record.id)]].forEach(([label, className, handler]) => {
      const button = createElement("button", className, label);
      button.type = "button";
      button.addEventListener("click", handler);
      actions.appendChild(button);
    });
    card.appendChild(actions);
    return card;
  }

  function showRecordDetail(id) {
    const record = state.records.find((item) => item.id === id);
    if (!record) return;
    elements.detailTitle.textContent = record.studentName;
    elements.detailContent.replaceChildren();
    const meta = createElement("div", "detail-meta");
    [formatFullDate(record.date), record.lessonTime || "시간 미정", record.lessonNumber ? `${record.lessonNumber}회차` : ""]
      .filter(Boolean).forEach((text) => meta.appendChild(createElement("span", "detail-chip", text)));
    elements.detailContent.appendChild(meta);
    [["레슨곡", record.songs], ["오늘의 레슨", record.lessonContent], ["잘된 점", record.goodPoints],
      ["보완할 점", record.improvementPoints], ["다음 과제", record.homework], ["강사 메모", record.instructorMemo]]
      .filter(([, value]) => value)
      .forEach(([title, value]) => {
        const section = createElement("section", "detail-section");
        section.append(createElement("h3", "", title), createElement("p", "", value));
        elements.detailContent.appendChild(section);
      });
    elements.detailModal.showModal();
  }

  function refreshViews() {
    renderCalendar();
    renderSelectedDate();
    renderLessonRecords();
  }

  function closeOnBackdrop(event) {
    if (event.target === event.currentTarget) event.currentTarget.close();
  }

  function showToast(message) {
    if (!elements.toast) return;
    clearTimeout(toastTimer);
    elements.toast.textContent = message;
    elements.toast.classList.add("show");
    toastTimer = setTimeout(() => elements.toast.classList.remove("show"), 2600);
  }

  function createElement(tag, className = "", text = "") {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (text !== "") element.textContent = text;
    return element;
  }

  function createId() {
    return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }

  function toDateKey(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  function fromDateKey(dateKey) {
    const [year, month, day] = dateKey.split("-").map(Number);
    return new Date(year, month - 1, day);
  }

  function formatFullDate(dateKey) {
    return new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric", weekday: "long" }).format(fromDateKey(dateKey));
  }

  document.addEventListener("DOMContentLoaded", initApp);
})();

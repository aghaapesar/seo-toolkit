/**
 * Jalali (Persian) date utilities for calendar UI.
 * Input: Gregorian or Jalali parts
 * Output: converted dates and formatted strings
 */

function gregorianToJalali(gy, gm, gd) {
  const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
  let jy = gy <= 1600 ? 0 : 979;
  gy -= gy <= 1600 ? 621 : 1600;
  const gy2 = gm > 2 ? gy + 1 : gy;
  let days =
    365 * gy +
    Math.floor((gy2 + 3) / 4) -
    Math.floor((gy2 + 99) / 100) +
    Math.floor((gy2 + 399) / 400) -
    80 +
    gd +
    g_d_m[gm - 1];
  jy += 33 * Math.floor(days / 12053);
  days %= 12053;
  jy += 4 * Math.floor(days / 1461);
  days %= 1461;
  jy += Math.floor((days - 1) / 365);
  if (days > 365) days = (days - 1) % 365;
  const jm = days < 186 ? 1 + Math.floor(days / 31) : 7 + Math.floor((days - 186) / 30);
  const jd = 1 + (days < 186 ? days % 31 : (days - 186) % 30);
  return { jy, jm, jd };
}

function jalaliToGregorian(jy, jm, jd) {
  let gy;
  jy += 1595;
  let days =
    -355668 +
    365 * jy +
    Math.floor(jy / 33) * 8 +
    Math.floor(((jy % 33) + 3) / 4) +
    jd +
    (jm < 7 ? (jm - 1) * 31 : (jm - 7) * 30 + 186);
  gy = 400 * Math.floor(days / 146097);
  days %= 146097;
  if (days > 36524) {
    gy += 100 * Math.floor(--days / 36524);
    days %= 36524;
    if (days >= 365) days++;
  }
  gy += 4 * Math.floor(days / 1461);
  days %= 1461;
  if (days > 365) {
    gy += Math.floor((days - 1) / 365);
    days = (days - 1) % 365;
  }
  const gd = days + 1;
  const sal_a = [
    0, 31, (gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0 ? 29 : 28,
    31, 30, 31, 30, 31, 31, 30, 31, 30, 31,
  ];
  let gm = 0;
  let v = gd;
  for (gm = 0; gm < 13 && v > sal_a[gm]; gm++) v -= sal_a[gm];
  return { gy, gm, gd: v };
}

function jalaliDaysInMonth(jy, jm) {
  if (jm <= 6) return 31;
  if (jm <= 11) return 30;
  const r = (((jy - (jy > 0 ? 474 : 473)) % 2820) + 474 + 2820) % 2820;
  return r === 0 ? 30 : 29;
}

function formatJalaliDate(isoDate, lang) {
  if (!isoDate) return "—";
  const parts = String(isoDate).slice(0, 10).split("-").map(Number);
  if (parts.length < 3 || parts.some((n) => Number.isNaN(n))) return isoDate;
  const { jy, jm, jd } = gregorianToJalali(parts[0], parts[1], parts[2]);
  const j = `${jy}/${String(jm).padStart(2, "0")}/${String(jd).padStart(2, "0")}`;
  if (lang === "fa") return j;
  return `${j} (Jalali)`;
}

function isoFromJalali(jy, jm, jd) {
  const { gy, gm, gd } = jalaliToGregorian(jy, jm, jd);
  return `${gy}-${String(gm).padStart(2, "0")}-${String(gd).padStart(2, "0")}`;
}

const JALALI_MONTHS_FA = [
  "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
  "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
];

const JALALI_MONTHS_EN = [
  "Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
  "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand",
];

/**
 * Build HTML for a Jalali picker wrapper (selects filled by initJalaliDatePicker).
 * Input: wrapper id, optional hidden input name.
 */
function jalaliPickerHtml(wrapperId, hiddenName, hiddenId) {
  const hid = hiddenId || `${wrapperId}-iso`;
  const nameAttr = hiddenName ? ` name="${hiddenName}"` : "";
  return `
    <div class="jalali-date-picker" id="${wrapperId}">
      <select class="j-year" aria-label="Year"></select>
      <select class="j-month" aria-label="Month"></select>
      <select class="j-day" aria-label="Day"></select>
      <input type="hidden"${nameAttr} id="${hid}" />
    </div>`;
}

/**
 * Bind Jalali <select> pickers to a hidden ISO Gregorian input.
 * Input: wrapper element id, optional { lang, defaultIso, allowEmpty, onChange }
 */
function initJalaliDatePicker(wrapperId, options = {}) {
  const wrap = document.getElementById(wrapperId);
  if (!wrap) return null;
  const lang = options.lang || document.documentElement.lang || "fa";
  const hidden = wrap.querySelector('input[type="hidden"]');
  const yearSel = wrap.querySelector(".j-year");
  const monthSel = wrap.querySelector(".j-month");
  const daySel = wrap.querySelector(".j-day");
  if (!hidden || !yearSel || !monthSel || !daySel) return null;

  const allowEmpty = !!options.allowEmpty;
  const months = lang === "fa" ? JALALI_MONTHS_FA : JALALI_MONTHS_EN;
  const emptyLabel = lang === "fa" ? "بدون تاریخ" : "No date";

  const now = new Date();
  const todayJ = gregorianToJalali(now.getFullYear(), now.getMonth() + 1, now.getDate());

  let defaultIso = options.defaultIso;
  if (defaultIso === undefined && !allowEmpty) {
    const tomorrow = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    defaultIso = `${tomorrow.getFullYear()}-${String(tomorrow.getMonth() + 1).padStart(2, "0")}-${String(tomorrow.getDate()).padStart(2, "0")}`;
  }

  let defaultJ = todayJ;
  if (defaultIso && String(defaultIso).length >= 10) {
    const p = String(defaultIso).slice(0, 10).split("-").map(Number);
    if (p.length >= 3 && !p.some((n) => Number.isNaN(n))) {
      defaultJ = gregorianToJalali(p[0], p[1], p[2]);
    }
  }

  const minYear = todayJ.jy - 2;
  const maxYear = todayJ.jy + 5;

  yearSel.innerHTML = "";
  if (allowEmpty) {
    const emptyOpt = document.createElement("option");
    emptyOpt.value = "";
    emptyOpt.textContent = emptyLabel;
    yearSel.appendChild(emptyOpt);
  }
  for (let y = minYear; y <= maxYear; y++) {
    const opt = document.createElement("option");
    opt.value = String(y);
    opt.textContent = String(y);
    yearSel.appendChild(opt);
  }

  monthSel.innerHTML = "";
  months.forEach((name, idx) => {
    const opt = document.createElement("option");
    opt.value = String(idx + 1);
    opt.textContent = name;
    monthSel.appendChild(opt);
  });

  const setPickerEnabled = (enabled) => {
    monthSel.disabled = !enabled;
    daySel.disabled = !enabled;
  };

  const fillDays = () => {
    const jy = Number(yearSel.value);
    const jm = Number(monthSel.value);
    if (!jy || !jm) {
      daySel.innerHTML = "";
      return;
    }
    const maxDay = jalaliDaysInMonth(jy, jm);
    const prev = Number(daySel.value) || defaultJ.jd || 1;
    daySel.innerHTML = "";
    for (let d = 1; d <= maxDay; d++) {
      const opt = document.createElement("option");
      opt.value = String(d);
      opt.textContent = String(d);
      if (d === Math.min(prev, maxDay)) opt.selected = true;
      daySel.appendChild(opt);
    }
  };

  const syncHidden = () => {
    if (!yearSel.value) {
      hidden.value = "";
      setPickerEnabled(false);
    } else {
      setPickerEnabled(true);
      const iso = isoFromJalali(Number(yearSel.value), Number(monthSel.value), Number(daySel.value));
      hidden.value = iso;
    }
    hidden.dispatchEvent(new Event("change", { bubbles: true }));
    if (typeof options.onChange === "function") options.onChange(hidden.value);
  };

  if (defaultIso && String(defaultIso).length >= 10) {
    yearSel.value = String(defaultJ.jy);
    monthSel.value = String(defaultJ.jm);
    fillDays();
    daySel.value = String(defaultJ.jd);
    setPickerEnabled(true);
  } else if (allowEmpty) {
    yearSel.value = "";
    setPickerEnabled(false);
  } else {
    yearSel.value = String(defaultJ.jy);
    monthSel.value = String(defaultJ.jm);
    fillDays();
    daySel.value = String(defaultJ.jd);
    setPickerEnabled(true);
  }

  syncHidden();

  yearSel.addEventListener("change", () => {
    if (!yearSel.value) {
      syncHidden();
      return;
    }
    if (!monthSel.value) monthSel.value = "1";
    fillDays();
    syncHidden();
  });
  monthSel.addEventListener("change", () => { fillDays(); syncHidden(); });
  daySel.addEventListener("change", syncHidden);

  return { hidden, yearSel, monthSel, daySel, syncHidden };
}

/**
 * Re-init picker with a new ISO date (or clear when empty).
 */
function setJalaliPickerIso(wrapperId, iso, options = {}) {
  const lang = options.lang || document.documentElement.lang || "fa";
  return initJalaliDatePicker(wrapperId, {
    ...options,
    lang,
    defaultIso: iso || "",
    allowEmpty: options.allowEmpty !== false,
  });
}

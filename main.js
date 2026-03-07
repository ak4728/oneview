const API_BASE = "";
const PREFS_KEY = "oneview.preferences.v1";
const FAV_KEY = "oneview.favorites.v1";
const LOG_COLLAPSED_KEY = "oneview.signalLogCollapsed.v1";
const PREDEFINED_TICKERS = [
  "BTC-USD", "ETH-USD", "SOL-USD", "AAPL", "TSLA", "NVDA", "MSFT", "EURUSD=X"
];
const CONFIRM_DEFAULTS = { "1m": 10, "5m": 5, "15m": 4, "30m": 3, "1d": 2 };

let myChart = null;
let autoTimer = null;
let countdown = 0;
let countdownInterval = null;

let lastRawCandles = null;
let lastCandles = null;
let lastResult = null;
let lastSignals = null;
let isSignalLogCollapsed = true;

function $(id) { return document.getElementById(id); }

function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}

function saveJSON(key, value) {
  try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
}

function loadSignalLogCollapsed() {
  const value = loadJSON(LOG_COLLAPSED_KEY, true);
  return typeof value === "boolean" ? value : true;
}

function setSignalLogCollapsed(collapsed) {
  isSignalLogCollapsed = Boolean(collapsed);
  const tableScroll = $("tableScroll");
  const btn = $("toggleSignalLogBtn");
  if (!tableScroll || !btn) return;

  tableScroll.style.display = isSignalLogCollapsed ? "none" : "block";
  btn.textContent = isSignalLogCollapsed ? "Show" : "Hide";
  saveJSON(LOG_COLLAPSED_KEY, isSignalLogCollapsed);
}

function toggleSignalLog() {
  setSignalLogCollapsed(!isSignalLogCollapsed);
}

function getPreferences() {
  return {
    symbol: $("symbolInput").value.trim().toUpperCase() || "BTC-USD",
    interval: $("intervalSelect").value,
    atrPeriod: $("atrPeriod").value,
    multiplier: $("multiplier").value,
    atrMethod: $("atrMethod").value,
    confirmBars: $("confirmBars").value,
    rangeFilter: $("rangeFilter").value,
    showSignals: $("showSignals").checked,
    highlighting: $("highlighting").checked,
    smcEnabled: $("smcEnabled").checked,
    smcBosChoch: $("smcBosChoch").checked,
    smcOrderBlocks: $("smcOrderBlocks").checked,
    smcOBCount: $("smcOBCount").value,
    smcSwingLen: $("smcSwingLen").value,
    autoRefresh: $("autoRefresh").checked,
  };
}

function applyPreferences() {
  const prefs = loadJSON(PREFS_KEY, null);
  if (!prefs) return;
  if (prefs.symbol) $("symbolInput").value = prefs.symbol;
  if (prefs.interval) $("intervalSelect").value = prefs.interval;
  if (prefs.atrPeriod) $("atrPeriod").value = prefs.atrPeriod;
  if (prefs.multiplier) $("multiplier").value = prefs.multiplier;
  if (prefs.atrMethod) $("atrMethod").value = prefs.atrMethod;
  if (prefs.confirmBars) $("confirmBars").value = prefs.confirmBars;
  if (prefs.rangeFilter) $("rangeFilter").value = prefs.rangeFilter;

  if (typeof prefs.showSignals === "boolean") $("showSignals").checked = prefs.showSignals;
  if (typeof prefs.highlighting === "boolean") $("highlighting").checked = prefs.highlighting;
  if (typeof prefs.smcEnabled === "boolean") $("smcEnabled").checked = prefs.smcEnabled;
  if (typeof prefs.smcBosChoch === "boolean") $("smcBosChoch").checked = prefs.smcBosChoch;
  if (typeof prefs.smcOrderBlocks === "boolean") $("smcOrderBlocks").checked = prefs.smcOrderBlocks;
  if (prefs.smcOBCount) $("smcOBCount").value = prefs.smcOBCount;
  if (prefs.smcSwingLen) $("smcSwingLen").value = prefs.smcSwingLen;

  // restore this only after listeners are ready in init
  if (typeof prefs.autoRefresh === "boolean") $("autoRefresh").checked = prefs.autoRefresh;
}

function persistPreferences() {
  saveJSON(PREFS_KEY, getPreferences());
}

function getFavorites() {
  return loadJSON(FAV_KEY, []);
}

function setFavorites(list) {
  const normalized = [...new Set(list.map(s => String(s || "").trim().toUpperCase()).filter(Boolean))];
  saveJSON(FAV_KEY, normalized);
  renderFavoriteTickers();
}

function addFavorite(symbol) {
  const ticker = String(symbol || "").trim().toUpperCase();
  if (!ticker) return;
  const favorites = getFavorites();
  if (!favorites.includes(ticker)) favorites.push(ticker);
  setFavorites(favorites);
}

function removeFavorite(symbol) {
  const favorites = getFavorites().filter(s => s !== symbol);
  setFavorites(favorites);
}

function clickTicker(symbol) {
  $("symbolInput").value = symbol;
  persistPreferences();
  fetchAndRun();
}

function renderPredefinedTickers() {
  const host = $("predefinedTickerList");
  host.innerHTML = PREDEFINED_TICKERS.map(symbol => (
    `<button class="ticker-chip" data-symbol="${symbol}">${symbol}</button>`
  )).join("");

  host.querySelectorAll(".ticker-chip").forEach(btn => {
    btn.addEventListener("click", () => clickTicker(btn.dataset.symbol));
  });
}

function renderFavoriteTickers() {
  const host = $("favoriteTickerList");
  const favorites = getFavorites();
  if (!favorites.length) {
    host.innerHTML = `<span class="status-text">No custom favorites yet.</span>`;
    return;
  }

  host.innerHTML = favorites.map(symbol => (
    `<span class="ticker-chip favorite-chip">
      <span class="fav-open" data-symbol="${symbol}">${symbol}</span>
      <button class="chip-remove" data-remove="${symbol}" title="Remove">x</button>
    </span>`
  )).join("");

  host.querySelectorAll(".fav-open").forEach(el => {
    el.addEventListener("click", () => clickTicker(el.dataset.symbol));
  });

  host.querySelectorAll(".chip-remove").forEach(el => {
    el.addEventListener("click", (event) => {
      event.stopPropagation();
      removeFavorite(el.dataset.remove);
    });
  });
}

function setStatus(msg, type = "ok") {
  $("statusRow").style.display = "flex";
  $("statusDot").className = "dot" + (type === "loading" ? " loading" : type === "error" ? " error" : "");
  $("statusText").textContent = msg;
}

function showLoading(show) {
  $("loading-overlay").style.display = show ? "flex" : "none";
  $("chartWrap").style.display = "block";
}

function autoConfirmBars(interval) {
  $("confirmBars").value = CONFIRM_DEFAULTS[interval] || 5;
}

function parseDate(dateStr) {
  const raw = String(dateStr || "").trim();
  if (!raw) return new Date(NaN);

  const isoLike = raw.includes("T") ? raw : raw.replace(" ", "T");
  const hasZone = /[zZ]$|[+\-]\d{2}:?\d{2}$/.test(isoLike);
  return new Date(hasZone ? isoLike : `${isoLike}Z`);
}

function formatLocalDateTime(dateStr) {
  const dt = parseDate(dateStr);
  if (Number.isNaN(dt.getTime())) return String(dateStr || "");
  return dt.toLocaleString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatLocalDay(dateStr) {
  const dt = parseDate(dateStr);
  if (Number.isNaN(dt.getTime())) return String(dateStr || "").slice(0, 10);
  return dt.toLocaleDateString([], {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function formatChartLabel(dateStr, interval) {
  const dt = parseDate(dateStr);
  if (Number.isNaN(dt.getTime())) return String(dateStr || "");

  if (interval === "1d") {
    return dt.toLocaleDateString([], { month: "short", day: "numeric" });
  }

  return dt.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function applyRangeFilter(candles, mode) {
  if (!Array.isArray(candles) || !candles.length) return [];
  if (mode === "all") return candles;

  if (mode === "last-day") {
    const lastDate = formatLocalDay(candles[candles.length - 1].date);
    return candles.filter(c => formatLocalDay(c.date) === lastDate);
  }

  if (mode === "last-24h") {
    const latest = parseDate(candles[candles.length - 1].date).getTime();
    const cutoff = latest - 24 * 60 * 60 * 1000;
    return candles.filter(c => parseDate(c.date).getTime() >= cutoff);
  }

  return candles;
}

function calcTR(c) {
  return c.map((d, i) => {
    if (i === 0) return d.high - d.low;
    const p = c[i - 1];
    return Math.max(d.high - d.low, Math.abs(d.high - p.close), Math.abs(d.low - p.close));
  });
}

function calcRMA(vals, period) {
  const r = new Array(vals.length).fill(NaN);
  let sum = 0;
  let cnt = 0;
  for (let i = 0; i < vals.length; i++) {
    if (isNaN(vals[i])) continue;
    if (cnt < period) {
      sum += vals[i];
      cnt++;
      if (cnt === period) r[i] = sum / period;
    } else {
      r[i] = (r[i - 1] * (period - 1) + vals[i]) / period;
    }
  }
  return r;
}

function calcSMA(vals, period) {
  const r = new Array(vals.length).fill(NaN);
  for (let i = period - 1; i < vals.length; i++) {
    let s = 0;
    for (let j = 0; j < period; j++) s += vals[i - j];
    r[i] = s / period;
  }
  return r;
}

function calcSuperTrend(candles, period, mult, useRMA) {
  const tr = calcTR(candles);
  const atr = useRMA ? calcRMA(tr, period) : calcSMA(tr, period);
  const n = candles.length;
  const up = new Array(n).fill(NaN);
  const dn = new Array(n).fill(NaN);
  const trend = new Array(n).fill(1);

  for (let i = 0; i < n; i++) {
    if (isNaN(atr[i])) continue;
    const hl2 = (candles[i].high + candles[i].low) / 2;
    const rawUp = hl2 - mult * atr[i];
    const rawDn = hl2 + mult * atr[i];
    const prevUp = i > 0 && !isNaN(up[i - 1]) ? up[i - 1] : rawUp;
    const prevDn = i > 0 && !isNaN(dn[i - 1]) ? dn[i - 1] : rawDn;
    const pClose = i > 0 ? candles[i - 1].close : candles[i].close;

    up[i] = pClose > prevUp ? Math.max(rawUp, prevUp) : rawUp;
    dn[i] = pClose < prevDn ? Math.min(rawDn, prevDn) : rawDn;

    const pTrend = i > 0 ? trend[i - 1] : 1;
    if (pTrend === -1 && candles[i].close > prevDn) trend[i] = 1;
    else if (pTrend === 1 && candles[i].close < prevUp) trend[i] = -1;
    else trend[i] = pTrend;
  }

  const st = trend.map((t, i) => t === 1 ? up[i] : dn[i]);
  return { up, dn, trend, st };
}

function extractSignals(candles, result) {
  const confirmBars = parseInt($("confirmBars").value, 10) || 3;
  const signals = [];
  const n = candles.length;

  let inFlip = false;
  let flipDir = 0;
  let flipBar = -1;
  let consecutiveCount = 0;

  for (let i = 1; i < n; i++) {
    if (isNaN(result.trend[i]) || isNaN(result.trend[i - 1])) continue;
    const trendChanged = result.trend[i] !== result.trend[i - 1];

    if (trendChanged) {
      inFlip = true;
      flipDir = result.trend[i];
      flipBar = i;
      consecutiveCount = 1;
    } else if (inFlip) {
      if (result.trend[i] === flipDir) {
        consecutiveCount++;
        if (consecutiveCount >= confirmBars) {
          signals.push({
            i,
            flipBar,
            type: flipDir === 1 ? "BUY" : "SELL",
            date: candles[i].date,
            close: candles[i].close,
            st: result.st[i],
            flipDate: candles[flipBar].date,
          });
          inFlip = false;
        }
      } else {
        inFlip = true;
        flipDir = result.trend[i];
        flipBar = i;
        consecutiveCount = 1;
      }
    }
  }

  return signals;
}

function calcSMC(candles) {
  const n = candles.length;
  const swingLen = parseInt($("smcSwingLen").value, 10) || 5;
  const obCount = parseInt($("smcOBCount").value, 10) || 5;

  const swingHighs = [];
  const swingLows = [];

  for (let i = swingLen; i < n - swingLen; i++) {
    let isHigh = true;
    let isLow = true;
    for (let k = 1; k <= swingLen; k++) {
      if (candles[i].high <= candles[i - k].high || candles[i].high <= candles[i + k].high) isHigh = false;
      if (candles[i].low >= candles[i - k].low || candles[i].low >= candles[i + k].low) isLow = false;
    }
    if (isHigh) swingHighs.push({ i, price: candles[i].high });
    if (isLow) swingLows.push({ i, price: candles[i].low });
  }

  const structures = [];
  let structureBias = null;

  const allSwings = [
    ...swingHighs.map(s => ({ ...s, kind: "high" })),
    ...swingLows.map(s => ({ ...s, kind: "low" })),
  ].sort((a, b) => a.i - b.i);

  let prevHigh = null;
  let prevLow = null;

  for (const swing of allSwings) {
    if (swing.kind === "high") {
      for (let ci = (prevHigh ? prevHigh.i : 0) + 1; ci <= swing.i; ci++) {
        if (prevHigh && candles[ci].close > prevHigh.price) {
          const tag = structureBias === "bear" ? "CHoCH" : "BOS";
          structures.push({ i: ci, type: tag, bias: "bull", level: prevHigh.price, fromI: prevHigh.i });
          structureBias = "bull";
          break;
        }
      }
      prevHigh = swing;
    } else {
      for (let ci = (prevLow ? prevLow.i : 0) + 1; ci <= swing.i; ci++) {
        if (prevLow && candles[ci].close < prevLow.price) {
          const tag = structureBias === "bull" ? "CHoCH" : "BOS";
          structures.push({ i: ci, type: tag, bias: "bear", level: prevLow.price, fromI: prevLow.i });
          structureBias = "bear";
          break;
        }
      }
      prevLow = swing;
    }
  }

  const orderBlocks = [];
  for (const s of structures) {
    if (s.bias === "bull") {
      for (let k = s.i - 1; k >= Math.max(0, s.fromI); k--) {
        if (candles[k].close < candles[k].open) {
          orderBlocks.push({ i: k, bias: "bull", high: candles[k].high, low: candles[k].low, breakI: s.i });
          break;
        }
      }
    } else {
      for (let k = s.i - 1; k >= Math.max(0, s.fromI); k--) {
        if (candles[k].close > candles[k].open) {
          orderBlocks.push({ i: k, bias: "bear", high: candles[k].high, low: candles[k].low, breakI: s.i });
          break;
        }
      }
    }
  }

  for (const ob of orderBlocks) {
    ob.mitigated = false;
    for (let ci = ob.breakI + 1; ci < n; ci++) {
      if (ob.bias === "bull" && candles[ci].low < ob.low) { ob.mitigated = true; break; }
      if (ob.bias === "bear" && candles[ci].high > ob.high) { ob.mitigated = true; break; }
    }
  }

  return {
    structures,
    orderBlocks: orderBlocks.filter(ob => !ob.mitigated).slice(-obCount),
  };
}

function renderChart(candles, result, signals, showSig, smcData) {
  const interval = $("intervalSelect").value;
  const labels = candles.map(c => formatChartLabel(c.date, interval));
  const closes = candles.map(c => c.close);
  const highlighting = $("highlighting").checked;

  const stUp = result.st.map((v, i) => result.trend[i] === 1 ? v : null);
  const stDn = result.st.map((v, i) => result.trend[i] === -1 ? v : null);

  const bgPlugin = {
    id: "trendBg",
    beforeDraw(chart) {
      if (!highlighting) return;
      const { ctx, chartArea: { right, top, bottom }, scales } = chart;
      for (let i = 0; i < candles.length; i++) {
        const x0 = scales.x.getPixelForValue(i);
        const x1 = i + 1 < candles.length ? scales.x.getPixelForValue(i + 1) : right;
        ctx.fillStyle = result.trend[i] === 1 ? "rgba(45,223,132,0.04)" : "rgba(255,90,103,0.04)";
        ctx.fillRect(x0, top, x1 - x0, bottom - top);
      }
    }
  };

  const datasets = [
    { label: "Close", data: closes, borderColor: "#dce7f5", borderWidth: 1.5, pointRadius: 0, tension: 0, order: 3 },
    { label: "ST Up", data: stUp, borderColor: "#2ddf84", borderWidth: 2, pointRadius: 0, spanGaps: false, tension: 0, order: 2 },
    { label: "ST Down", data: stDn, borderColor: "#ff5a67", borderWidth: 2, pointRadius: 0, spanGaps: false, tension: 0, order: 2 },
  ];

  if (showSig) {
    const buyData = new Array(candles.length).fill(null);
    const sellData = new Array(candles.length).fill(null);

    signals.forEach(s => {
      if (s.type === "BUY") buyData[s.i] = s.close * 0.997;
      if (s.type === "SELL") sellData[s.i] = s.close * 1.003;
    });

    datasets.push({
      label: "BUY", showLine: false, order: 1, data: buyData,
      borderColor: "#2ddf84", backgroundColor: "#2ddf84", pointStyle: "triangle", pointRadius: 9,
    });

    datasets.push({
      label: "SELL", showLine: false, order: 1, data: sellData,
      borderColor: "#ff5a67", backgroundColor: "#ff5a67", pointStyle: "triangle", pointRadius: 9, rotation: 180,
    });
  }

  const signalLabelsPlugin = {
    id: "signalLabels",
    afterDatasetsDraw(chart) {
      if (!showSig) return;
      const { ctx, scales } = chart;
      ctx.save();
      ctx.font = "bold 10px 'Atkinson Hyperlegible Next', sans-serif";
      ctx.textBaseline = "middle";

      signals.forEach(s => {
        const xPos = scales.x.getPixelForValue(s.i);
        const yVal = s.type === "BUY" ? s.close * 0.997 : s.close * 1.003;
        const yPos = scales.y.getPixelForValue(yVal);
        ctx.fillStyle = s.type === "BUY" ? "#2ddf84" : "#ff5a67";
        ctx.fillText(s.type === "BUY" ? "Buy" : "Sell", xPos + 10, yPos);
      });

      ctx.restore();
    }
  };

  const smcPlugin = {
    id: "smcOverlay",
    afterDraw(chart) {
      if (!smcData || !$("smcEnabled").checked) return;
      const showBosChoch = $("smcBosChoch").checked;
      const showOB = $("smcOrderBlocks").checked;
      const { ctx, chartArea: { right, top, bottom }, scales } = chart;

      ctx.save();

      if (showOB && smcData.orderBlocks) {
        for (const ob of smcData.orderBlocks) {
          const x0 = scales.x.getPixelForValue(ob.i);
          const yHi = scales.y.getPixelForValue(ob.high);
          const yLo = scales.y.getPixelForValue(ob.low);
          const h = Math.abs(yHi - yLo);

          ctx.fillStyle = ob.bias === "bull" ? "rgba(90,155,255,0.16)" : "rgba(255,90,103,0.16)";
          ctx.strokeStyle = ob.bias === "bull" ? "rgba(90,155,255,0.5)" : "rgba(255,90,103,0.5)";
          ctx.lineWidth = 1;
          ctx.fillRect(x0, yHi, right - x0, h);
          ctx.strokeRect(x0, yHi, right - x0, h);
        }
      }

      if (showBosChoch && smcData.structures) {
        for (const s of smcData.structures) {
          if (s.i < candles.length * 0.4) continue;
          const xFrom = scales.x.getPixelForValue(s.fromI);
          const xTo = scales.x.getPixelForValue(s.i);
          const yLvl = scales.y.getPixelForValue(s.level);
          if (yLvl < top || yLvl > bottom) continue;

          const isBull = s.bias === "bull";
          const isChoch = s.type === "CHoCH";
          let color;
          if (isChoch) color = isBull ? "#5a9bff" : "#ffcb4a";
          else color = isBull ? "#2ddf84" : "#ff5a67";

          ctx.strokeStyle = color;
          ctx.lineWidth = 1.5;
          ctx.setLineDash(isChoch ? [4, 3] : []);
          ctx.beginPath();
          ctx.moveTo(xFrom, yLvl);
          ctx.lineTo(xTo, yLvl);
          ctx.stroke();
          ctx.setLineDash([]);

          ctx.fillStyle = color;
          ctx.font = "bold 9px 'Atkinson Hyperlegible Next', sans-serif";
          ctx.fillText(s.type, xTo + 3, isBull ? yLvl - 6 : yLvl + 12);
        }
      }

      ctx.restore();
    }
  };

  if (myChart) myChart.destroy();
  const ctx = $("priceChart").getContext("2d");

  myChart = new Chart(ctx, {
    type: "line",
    data: { labels, datasets },
    options: {
      responsive: true,
      animation: { duration: 250 },
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: { labels: { color: "#8ca0ba", font: { family: "Atkinson Hyperlegible Next", size: 11 }, boxWidth: 14 } },
        tooltip: {
          backgroundColor: "#141f31",
          borderColor: "#314867",
          borderWidth: 1,
          titleColor: "#dce7f5",
          bodyColor: "#c0d0e8",
          callbacks: {
            title(context) {
              if (!context.length) return "";
              const idx = context[0].dataIndex;
              return formatLocalDateTime(candles[idx].date);
            },
            label(context) {
              if (context.parsed.y == null) return null;
              return ` ${context.dataset.label}: ${context.parsed.y.toLocaleString(undefined, { maximumFractionDigits: 4 })}`;
            }
          }
        },
        zoom: {
          zoom: { wheel: { enabled: true }, pinch: { enabled: true }, mode: "x" },
          pan: { enabled: true, mode: "x" },
          limits: { x: { minRange: 10 } }
        }
      },
      scales: {
        x: { ticks: { color: "#8ca0ba", maxTicksLimit: 10, maxRotation: 0 }, grid: { color: "#263247" } },
        y: { ticks: { color: "#8ca0ba" }, grid: { color: "#263247" } },
      }
    },
    plugins: [bgPlugin, signalLabelsPlugin, smcPlugin],
  });

  showLoading(false);
  $("chartWrap").style.display = "block";
}

function renderCards(candles, signals, json) {
  const buys = signals.filter(s => s.type === "BUY");
  const sells = signals.filter(s => s.type === "SELL");
  const last = candles[candles.length - 1];

  $("buyCount").textContent = buys.length;
  $("sellCount").textContent = sells.length;
  $("lastBuy").textContent = buys.length ? `Last: ${formatLocalDateTime(buys[buys.length - 1].date)}` : "No buy signals";
  $("lastSell").textContent = sells.length ? `Last: ${formatLocalDateTime(sells[sells.length - 1].date)}` : "No sell signals";
  $("candleCount").textContent = candles.length;
  $("dataRange").textContent = `${formatLocalDay(candles[0].date)} -> ${formatLocalDay(last.date)}`;
  $("lastClose").textContent = last.close.toLocaleString(undefined, { maximumFractionDigits: 4 });
  $("lastCloseTime").textContent = formatLocalDateTime(last.date);

  $("cardsRow").style.display = "grid";
}

function updatePriceDisplay(candles) {
  const last = candles[candles.length - 1];
  const prev = candles.length > 1 ? candles[candles.length - 2] : null;
  const chg = prev ? ((last.close - prev.close) / prev.close * 100) : 0;
  const sym = $("symbolInput").value.trim().toUpperCase();

  $("livePrice").textContent = last.close.toLocaleString(undefined, { maximumFractionDigits: 4 });
  $("livePriceMeta").textContent = `${sym} · ${chg >= 0 ? "+" : ""}${chg.toFixed(2)}% · ${formatLocalDateTime(last.date)}`;
  $("livePriceMeta").style.color = chg >= 0 ? "var(--green)" : "var(--red)";
  $("priceDisplay").style.display = "block";
}

function renderTable(signals, symbol, interval) {
  $("symbolBadge").textContent = `${symbol} · ${interval}`;
  const tbody = $("signalBody");

  if (!signals.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:20px">No signals in this window</td></tr>';
  } else {
    tbody.innerHTML = signals.slice().reverse().map((s, idx) => `
      <tr>
        <td style="color:var(--muted)">${signals.length - idx}</td>
        <td>${formatLocalDateTime(s.date)}</td>
        <td><span class="tag ${s.type.toLowerCase()}">${s.type}</span></td>
        <td>${s.close.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
        <td style="color:${s.type === "BUY" ? "var(--green)" : "var(--red)"}">${s.st.toLocaleString(undefined, { maximumFractionDigits: 4 })}</td>
        <td style="color:var(--muted);font-size:0.76rem">${formatLocalDateTime(s.flipDate)}</td>
      </tr>
    `).join("");
  }

  $("tableWrap").style.display = "block";
  setSignalLogCollapsed(isSignalLogCollapsed);
}

async function fetchData(symbol, interval) {
  const url = `${API_BASE}/api/ohlcv?symbol=${encodeURIComponent(symbol)}&interval=${interval}`;
  const res = await fetch(url);
  const json = await res.json();
  if (!res.ok) throw new Error(json.error || "API error");
  return json;
}

function processFromRaw(json) {
  const symbol = $("symbolInput").value.trim().toUpperCase() || "BTC-USD";
  const interval = $("intervalSelect").value;
  const period = parseInt($("atrPeriod").value, 10) || 10;
  const mult = parseFloat($("multiplier").value) || 3.0;
  const useRMA = $("atrMethod").value === "rma";
  const showSig = $("showSignals").checked;
  const rangeFilter = $("rangeFilter").value;

  let candles = applyRangeFilter(lastRawCandles, rangeFilter);
  if (!candles.length) {
    throw new Error("No candles left after filter. Try a wider range.");
  }

  const result = calcSuperTrend(candles, period, mult, useRMA);
  const signals = extractSignals(candles, result);
  const smcData = calcSMC(candles);

  lastCandles = candles;
  lastResult = result;
  lastSignals = signals;

  renderChart(candles, result, signals, showSig, smcData);
  renderCards(candles, signals, json);
  renderTable(signals, symbol, interval);
  updatePriceDisplay(candles);

  const lastTrendIdx = result.trend.findLastIndex(v => !isNaN(v));
  const lastTrend = result.trend[lastTrendIdx];
  const badge = $("trendBadge");
  badge.style.display = "inline-flex";
  badge.className = "trend-badge " + (lastTrend === 1 ? "trend-up" : "trend-down");
  badge.textContent = lastTrend === 1 ? "Uptrend" : "Downtrend";

  setStatus(`${candles.length}/${json.count} candles · ${symbol} · ${interval} · updated ${new Date().toLocaleTimeString()}`);
  $("refreshBtn").disabled = false;
}

async function fetchAndRun() {
  const symbol = $("symbolInput").value.trim().toUpperCase() || "BTC-USD";
  const interval = $("intervalSelect").value;

  $("symbolInput").value = symbol;
  $("empty-state").style.display = "none";
  $("refreshBtn").disabled = true;
  setStatus("Fetching data...", "loading");
  showLoading(true);

  try {
    const json = await fetchData(symbol, interval);
    lastRawCandles = json.data;
    processFromRaw(json);
    persistPreferences();
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
    showLoading(false);
  }
}

function rerender() {
  if (!lastCandles || !lastResult || !lastSignals) return;
  const showSig = $("showSignals").checked;
  const smcData = calcSMC(lastCandles);
  renderChart(lastCandles, lastResult, lastSignals, showSig, smcData);
}

function recomputeFromRawIfAvailable() {
  if (!lastRawCandles) return;
  try {
    processFromRaw({ count: lastRawCandles.length });
    persistPreferences();
  } catch (err) {
    setStatus(`Error: ${err.message}`, "error");
  }
}

function resetZoom() {
  if (myChart) myChart.resetZoom();
}

function stopAutoRefresh() {
  clearInterval(autoTimer);
  clearInterval(countdownInterval);
  $("countdownText").textContent = "";
}

function toggleAutoRefresh() {
  const on = $("autoRefresh").checked;
  stopAutoRefresh();

  if (on) {
    const intervalSecs = 60;
    countdown = intervalSecs;

    const tick = () => {
      countdown -= 1;
      $("countdownText").textContent = `(${countdown}s)`;
      if (countdown <= 0) {
        countdown = intervalSecs;
        fetchAndRun();
      }
    };

    countdownInterval = setInterval(tick, 1000);
    fetchAndRun();
  }

  persistPreferences();
}

function initEvents() {
  $("refreshBtn").addEventListener("click", fetchAndRun);
  $("toggleSignalLogBtn").addEventListener("click", toggleSignalLog);

  $("intervalSelect").addEventListener("change", () => {
    autoConfirmBars($("intervalSelect").value);
    persistPreferences();
  });

  $("symbolInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") fetchAndRun();
  });

  $("addFavoriteBtn").addEventListener("click", () => {
    addFavorite($("favoriteInput").value);
    $("favoriteInput").value = "";
  });

  $("favoriteInput").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      addFavorite($("favoriteInput").value);
      $("favoriteInput").value = "";
    }
  });

  $("resetZoomBtn").addEventListener("click", resetZoom);
  $("autoRefresh").addEventListener("change", toggleAutoRefresh);

  [
    "showSignals", "highlighting", "smcEnabled", "smcBosChoch", "smcOrderBlocks"
  ].forEach(id => {
    $(id).addEventListener("change", () => {
      persistPreferences();
      rerender();
    });
  });

  [
    "atrPeriod", "multiplier", "atrMethod", "confirmBars", "rangeFilter",
    "smcOBCount", "smcSwingLen"
  ].forEach(id => {
    $(id).addEventListener("change", recomputeFromRawIfAvailable);
  });

  ["symbolInput"].forEach(id => $(id).addEventListener("change", persistPreferences));
}

function init() {
  isSignalLogCollapsed = loadSignalLogCollapsed();
  setSignalLogCollapsed(isSignalLogCollapsed);

  applyPreferences();
  initEvents();
  renderPredefinedTickers();
  renderFavoriteTickers();

  if (loadJSON(PREFS_KEY, null)?.autoRefresh) {
    toggleAutoRefresh();
  }
}

document.addEventListener("DOMContentLoaded", init);

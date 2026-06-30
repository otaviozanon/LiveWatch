var API_URL = "https://ozlivewatch.pages.dev";
var BASE_RAW = "https://raw.githubusercontent.com/otaviozanon/LiveWatch/main/";

var PLAYLISTS = {
  brasil: {
    m3u: "playlists/m3u/LiveWatch-PlaylistBR.m3u",
    m3u8: "playlists/m3u8/LiveWatch-PlaylistBR.m3u8",
  },
  global: {
    m3u: "playlists/m3u/LiveWatch-PlaylistWorld.m3u",
    m3u8: "playlists/m3u8/LiveWatch-PlaylistWorld.m3u8",
  },
  "iptv-org": {
    m3u: "playlists/m3u/LiveWatch-PlaylistIPTVORG.m3u",
    m3u8: "playlists/m3u8/LiveWatch-PlaylistIPTVORG.m3u8",
  },
  manotv: {
    m3u: "playlists/m3u/LiveWatch-PlaylistManoTV.m3u",
    m3u8: "playlists/m3u8/LiveWatch-PlaylistManoTV.m3u8",
  },
  all: {
    m3u: "playlists/m3u/LiveWatch-PlaylistAll.m3u",
    m3u8: "playlists/m3u8/LiveWatch-PlaylistAll.m3u8",
  },
};
var profileSelect = null;

var T = {
  pt: {
    systemReady: "Sistema pronto.",
    dispatching: "Disparando workflow...",
    errorDispatch: "Erro ao disparar: {0}",
    workflowStarted: "Workflow iniciado.",
    fail: "Falha: {0}",
    waitingStart: "Aguardando in\u00edcio...",
    running: "Executando...",
    completed: "Conclu\u00eddo",
    playlistUpdated: "Playlist atualizada.",
    workflowFailed: "Workflow falhou.",
    summary: "Resumo:",
    divider: "---------------------",
    listsExtracted: "Listas extra\u00eddas: {0}",
    listStats: "  {0} | {1} linhas -> {2} entradas",
    totalFiltered: "Total de canais filtrados: {0}",
    totalFinal: "Total final: {0} canais",
    playlistGenerated: "{0} gerado.",
    timeout: "Tempo limite atingido.",
    timeoutShort: "Tempo limite",
    failed: "Falhou",
    // Log translations (PT key -> EN value)
    log_pt: {
      "Buscando": "Buscando",
      "listas encontradas": "listas encontradas",
      "entradas": "entradas",
      "linhas": "linhas",
      "registros": "registros",
      "canais BR": "canais BR",
      "canais validos": "canais validos",
      "streams": "streams",
      "canais indesejados": "canais indesejados",
      "canais recategorizados": "canais recategorizados",
      "grupos excluidos": "grupos excluidos",
      "canais filtrados (grupo)": "canais filtrados (grupo)",
      "URLs bloqueadas": "URLs bloqueadas",
      "duplicatas URL": "duplicatas URL",
      "conflitos renomeados": "conflitos renomeados",
      "nomes normalizados": "nomes normalizados",
      "Total combinado": "Total combinado",
      "Total pos-filtro": "Total pos-filtro",
    },
    log_en: {
      "Buscando": "Fetching",
      "listas encontradas": "lists found",
      "entradas": "entries",
      "linhas": "lines",
      "registros": "records",
      "canais BR": "BR channels",
      "canais validos": "valid channels",
      "streams": "streams",
      "canais indesejados": "unwanted channels",
      "canais recategorizados": "recategorized channels",
      "grupos excluidos": "excluded groups",
      "canais filtrados (grupo)": "channels filtered (group)",
      "URLs bloqueadas": "blocked URLs",
      "duplicatas URL": "URL duplicates",
      "conflitos renomeados": "renamed conflicts",
      "nomes normalizados": "normalized names",
      "Total combinado": "Combined total",
      "Total pos-filtro": "Post-filter total",
    },    btnUpdate: "ATUALIZAR",
    btnDownload: "DOWNLOAD",
    btnCopy: "COPIAR URL",
    copied: "COPIADO",
    copyError: "Erro ao copiar URL.",
    sourceWorker: "Link curto",
    sourceRaw: "Raw GitHub",
    profileBrasil: "Brasil",
    profileGlobal: "Global",
    profileIptvorg: "IPTV-ORG",
    profileManotv: "ManoTV",
    profileAll: "Todos",
    headerTitle: "LiveWatch &mdash; Lista IPTV",
    // EPG tab
    epgLoading: "Carregando playlist e guia...",
    epgParsing: "Processando {0} MB de XML...",
    epgError: "Erro: {0}",
    epgParseError: "Erro ao processar: {0}",
    epgNoPrograms: "Nenhum programa encontrado para os canais da playlist.",
    epgNoTitle: "Sem t\u00edtulo",
    epgFooterChannels: "{0} CANAIS",
    epgBtnUpdate: "ATUALIZAR",
    epgBtnDownload: "DOWNLOAD",
    epgBtnCopy: "COPIAR URL",
    epgCountryBR: "Brasil",
    epgCountryUS: "Estados Unidos",
  },
  en: {
    systemReady: "System ready.",
    dispatching: "Dispatching workflow...",
    errorDispatch: "Error dispatching: {0}",
    workflowStarted: "Workflow started.",
    fail: "Error: {0}",
    waitingStart: "Waiting to start...",
    running: "Running...",
    completed: "Completed",
    playlistUpdated: "Playlist updated.",
    workflowFailed: "Workflow FAILED.",
    summary: "Summary:",
    divider: "---------------------",
    listsExtracted: "Extracted lists: {0}",
    listStats: "  {0} | {1} lines -> {2} entries",
    totalFiltered: "Total filtered channels: {0}",
    totalFinal: "Final total: {0} channels",
    playlistGenerated: "{0} generated.",
    timeout: "Timeout reached.",
    timeoutShort: "Timeout",
    failed: "Failed",
    log_pt: {
      "Buscando": "Buscando", "listas encontradas": "listas encontradas",
      "entradas": "entradas", "linhas": "linhas", "registros": "registros",
      "canais BR": "canais BR", "canais validos": "canais validos",
      "streams": "streams",
      "canais indesejados": "canais indesejados",
      "canais recategorizados": "canais recategorizados",
      "grupos excluidos": "grupos excluidos",
      "canais filtrados (grupo)": "canais filtrados (grupo)",
      "URLs bloqueadas": "URLs bloqueadas",
      "duplicatas URL": "duplicatas URL",
      "conflitos renomeados": "conflitos renomeados",
      "nomes normalizados": "nomes normalizados",
      "Total combinado": "Total combinado",
      "Total pos-filtro": "Total pos-filtro",
    },
    log_en: {
      "Buscando": "Fetching", "listas encontradas": "lists found",
      "entradas": "entries", "linhas": "lines", "registros": "records",
      "canais BR": "BR channels", "canais validos": "valid channels",
      "streams": "streams",
      "canais indesejados": "unwanted channels",
      "canais recategorizados": "recategorized channels",
      "grupos excluidos": "excluded groups",
      "canais filtrados (grupo)": "channels filtered (group)",
      "URLs bloqueadas": "blocked URLs",
      "duplicatas URL": "URL duplicates",
      "conflitos renomeados": "renamed conflicts",
      "nomes normalizados": "normalized names",
      "Total combinado": "Combined total",
      "Total pos-filtro": "Post-filter total",
    },
    btnUpdate: "UPDATE",
    btnDownload: "DOWNLOAD",
    btnCopy: "COPY URL",
    copied: "COPIED",
    copyError: "Error copying URL.",
    sourceWorker: "Short link",
    sourceRaw: "Raw GitHub",
    profileBrasil: "Brazil",
    profileGlobal: "Global",
    profileIptvorg: "IPTV-ORG",
    profileManotv: "ManoTV",
    profileAll: "All",
    headerTitle: "LiveWatch &mdash; IPTV List",
    // EPG tab
    epgLoading: "Loading playlist and guide...",
    epgParsing: "Processing {0} MB of XML...",
    epgError: "Error: {0}",
    epgParseError: "Error processing: {0}",
    epgNoPrograms: "No programs found for playlist channels.",
    epgNoTitle: "No title",
    epgFooterChannels: "{0} CHANNELS",
    epgBtnUpdate: "UPDATE",
    epgBtnDownload: "DOWNLOAD",
    epgBtnCopy: "COPY URL",
    epgCountryBR: "Brazil",
    epgCountryUS: "United States",
  },
};

var lang = localStorage.getItem("livewatch-lang") || "pt";
var currentProfile = localStorage.getItem("livewatch-profile") || "brasil";

function t(key) {
  var args = Array.prototype.slice.call(arguments, 1);
  var msg = (T[lang] && T[lang][key]) || T.en[key] || key;
  for (var i = 0; i < args.length; i++) {
    msg = msg.replace("{" + i + "}", args[i]);
  }
  return msg;
}

var logsEl = document.getElementById("logs");
var progressWrap = document.getElementById("progress-wrap");
var progressFill = document.getElementById("progress-fill");
var progressLabel = document.getElementById("progress-label");
var btnEl = document.getElementById("btn-update");
var dlBtnEl = document.getElementById("btn-download");
var copyBtnEl = document.getElementById("btn-copy");
var formatSelect = document.getElementById("format-select");
var sourceSelect = document.getElementById("source-select");
var updatedEl = document.getElementById("last-updated");
profileSelect = document.getElementById("profile-select");

var progressTimer = null;
var progressVal = 0;

function getPlaylistUrl(format, source) {
  format = format || formatSelect.value || "m3u8";
  source = source || sourceSelect.value || "worker";
  if (source === "raw") {
    return BASE_RAW + PLAYLISTS[currentProfile][format];
  }
  return API_URL + "/p/" + currentProfile + "." + format;
}

function applyLang() {
  document.querySelectorAll(".lang-btn").forEach(function (b) {
    b.classList.toggle("active", b.dataset.lang === lang);
  });
  btnEl.innerHTML = "&#x21BB; " + t("btnUpdate");
  dlBtnEl.innerHTML = "&#x21E9; " + t("btnDownload");
  copyBtnEl.innerHTML = "&#x2398; " + t("btnCopy");
  sourceSelect.options[0].text = t("sourceWorker");
  sourceSelect.options[1].text = t("sourceRaw");
  profileSelect.options[0].text = t("profileBrasil");
  profileSelect.options[1].text = t("profileGlobal");
  profileSelect.options[2].text = t("profileIptvorg");
  profileSelect.options[3].text = t("profileManotv");
  profileSelect.options[4].text = t("profileAll");
  document.getElementById("header-title").innerHTML = t("headerTitle");
  var epgRefBtn = document.getElementById("btn-epg-refresh");
  var epgDlBtn2 = document.getElementById("btn-epg-download");
  var epgCopyBtn2 = document.getElementById("btn-epg-copy");
  if (epgRefBtn) epgRefBtn.innerHTML = "&#x21BB; " + t("epgBtnUpdate");
  if (epgDlBtn2) epgDlBtn2.innerHTML = "&#x21E9; " + t("epgBtnDownload");
  if (epgCopyBtn2) epgCopyBtn2.innerHTML = "&#x2398; " + t("epgBtnCopy");
  var epgCountry = document.getElementById("epg-country-select");
  if (epgCountry) {
    epgCountry.options[0].text = t("epgCountryBR");
    epgCountry.options[1].text = t("epgCountryUS");
  }
  logsEl.innerHTML =
    '<div class="log dim" id="first-log">[LiveWatch] ' +
    t("systemReady") +
    "</div>";
  localStorage.setItem("livewatch-lang", lang);
  refreshFirstLine();
}

document.getElementById("lang-toggle").addEventListener("click", function (e) {
  var btn = e.target.closest(".lang-btn");
  if (!btn || btn.dataset.lang === lang) return;
  lang = btn.dataset.lang;
  applyLang();
});

profileSelect.addEventListener("change", function () {
  currentProfile = profileSelect.value;
  localStorage.setItem("livewatch-profile", currentProfile);
  loadLastRun();
});

profileSelect.value = currentProfile;

function log(msg, cls, delay) {
  cls = cls || "dim";
  if (delay) {
    setTimeout(function () {
      var div = document.createElement("div");
      div.className = "log " + cls;
      div.textContent = "[LiveWatch] " + msg;
      logsEl.appendChild(div);
      logsEl.scrollTop = logsEl.scrollHeight;
    }, delay);
    return;
  }
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.textContent = "[LiveWatch] " + msg;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
  return div;
}

function updateClock(d) {
  if (!d) {
    updatedEl.textContent = "";
    return;
  }
  updatedEl.textContent = d.toLocaleString(lang === "pt" ? "pt-BR" : "en-US");
  refreshFirstLine();
}

function refreshFirstLine() {
  var el = document.getElementById("first-log");
  if (!el) return;
  el.textContent = "[LiveWatch] " + t("systemReady");
}

function saveCounts(totalChannels, withEpg) {
  if (totalChannels)
    localStorage.setItem("livewatch-last-count", totalChannels);
  if (withEpg) localStorage.setItem("livewatch-last-epg", withEpg);
  refreshFirstLine();
}

function loadLastRun() {
  fetch(API_URL + "/file-time", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: PLAYLISTS[currentProfile].m3u8 }),
  })
    .then(function (resp) {
      return resp.json();
    })
    .then(function (data) {
      if (data.date) updateClock(new Date(data.date));
    })
    .catch(function () {});
}

function showProgress(label) {
  progressWrap.style.display = "block";
  progressLabel.textContent = label || t("waitingStart");
  progressVal = 0;
  progressFill.style.width = "0%";
  progressVal = 8;
  progressFill.style.width = progressVal + "%";
  if (progressTimer) clearInterval(progressTimer);
  progressTimer = setInterval(function () {
    if (progressVal < 85) {
      progressVal += Math.random() * 6;
      if (progressVal > 85) progressVal = 85;
      progressFill.style.width = progressVal + "%";
    }
  }, 1200);
}

function completeProgress(label) {
  if (progressTimer) clearInterval(progressTimer);
  progressVal = 100;
  progressFill.style.width = "100%";
  progressLabel.textContent = label || "";
  setTimeout(function () {
    progressWrap.style.display = "none";
  }, 1500);
}

function triggerWorkflow() {
  btnEl.disabled = true;
  // Switch to LOGS tab if on EPG
  if (window._currentTab === "epg") window.switchTab("logs");

  // Clear old log lines bottom-to-top instantly
  var lines = logsEl.querySelectorAll(".log");
  var delay = 0;
  for (var i = lines.length - 1; i >= 0; i--) {
    (function (el, d) {
      setTimeout(function () {
        el.remove();
      }, d);
    })(lines[i], delay);
    delay += 80;
  }
  setTimeout(function () {
    log(t("dispatching") + " (" + currentProfile + ")", "action");

    fetch(API_URL + "/trigger", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ profile: currentProfile }),
    })
      .then(function (resp) {
        return resp.json();
      })
      .then(function (data) {
        if (!data.ok) {
          log(t("errorDispatch", data.error), "error");
          btnEl.disabled = false;
          return;
        }
        log(t("workflowStarted"), "success");
        showProgress(t("waitingStart"));
        pollLogs();
      })
      .catch(function (e) {
        log(t("fail", e.message), "error");
        btnEl.disabled = false;
      });
  }, delay + 100);
}

function pollLogs() {
  var maxAttempts = 180;
  var delay = 3000;
  var attempt = 0;

  function tick() {
    attempt++;
    if (attempt > maxAttempts) {
      completeProgress(t("timeoutShort"));
      log(t("timeout"), "warn");
      btnEl.disabled = false;
      return;
    }

    fetch(API_URL + "/status", { method: "POST", body: "{}" })
      .then(function (resp) {
        return resp.json();
      })
      .then(function (data) {
        var run = (data.workflow_runs || [])[0];
        if (!run) {
          setTimeout(tick, delay);
          return;
        }

        if (run.status === "in_progress") {
          progressLabel.textContent = t("running");
        }

        if (run.status === "completed") {
          if (run.conclusion === "success") {
            completeProgress(t("completed"));
            var ts = new Date(run.updated_at || run.created_at);
            updateClock(ts);
            setTimeout(function () {
              fetchSummary(run.id);
            }, 2000);
          } else {
            completeProgress(t("failed"));
            log(t("workflowFailed"), "error");
            log(
              "https://github.com/otaviozanon/LiveWatch/actions/runs/" + run.id,
              "dim",
            );
            btnEl.disabled = false;
          }
        } else {
          setTimeout(tick, delay);
        }
      })
      .catch(function () {
        setTimeout(tick, delay);
      });
  }

  setTimeout(tick, 2500);
}

function fetchSummary(runId) {
  fetch(API_URL + "/logs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runId: runId }),
  })
    .then(function (resp) {
      return resp.ok ? resp.text() : null;
    })
    .then(function (text) {
      if (!text) {
        log(t("playlistUpdated"), "success");
        btnEl.disabled = false;
        return;
      }
      renderSummary(text);
    })
    .catch(function () {
      log(t("playlistUpdated"), "success");
      btnEl.disabled = false;
    });
}

function stripAnsi(str) {
  return str.replace(/\x1b\[[0-9;]*m/g, "");
}

function renderSummary(text) {
  var lines = text.replace(/\r\n/g, "\n").replace(/\r/g, "\n").split("\n");
  var entries = [];
  var currentProfile = null;
  var totalFinal = null;

  // Helper: translate log text from PT to current language
  function trLog(ptText) {
    if (lang === "pt") return ptText;
    var dict = T.en.log_en || {};
    for (var key in dict) {
      if (ptText.indexOf(key) !== -1) {
        // Preserve numbers: "1797 canais indesejados" -> "1797 unwanted channels"
        var numMatch = ptText.match(/^(\d+)\s+(.+)/);
        if (numMatch && key === numMatch[2]) {
          return numMatch[1] + " " + dict[key];
        }
        // For patterns like "Total combinado: 4630" -> "Combined total: 4630"
        var colonMatch = ptText.match(/^(.+?):\s*(\d+)/);
        if (colonMatch && key === colonMatch[1]) {
          return dict[key] + ": " + colonMatch[2];
        }
        return ptText.replace(key, dict[key]);
      }
    }
    return ptText;
  }

  for (var i = 0; i < lines.length; i++) {
    var line = stripAnsi(lines[i]);
    var idx = line.indexOf("[LiveWatch]");
    if (idx === -1) continue;
    var msg = line.substring(idx + 12).trim();
    var clean = msg.replace(/^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*/, "");
    if (!clean) continue;

    // Profile header
    var pm = clean.match(/^--- (.+) ---$/);
    if (pm) {
      currentProfile = pm[1];
      entries.push({ type: "header", text: pm[1] });
      continue;
    }

    if (!currentProfile && !clean.match(/^\[/)) continue;

    // Classify by prefix
    var mPlus = clean.match(/^\[\+\]\s*(.+)/);
    var mMinus = clean.match(/^\[-\]\s*(.+)/);
    var mStar = clean.match(/^\[\*\]\s*(.+)/);
    var mInfo = clean.match(/^\[i\]\s*(.+)/);
    var mBang = clean.match(/^\[!\]\s*(.+)/);

    if (mPlus) {
      var txt = trLog(mPlus[1]);
      var fm = txt.match(/Final:?\s*(\d+)\s*canais/);
      if (fm) totalFinal = fm[1];
      entries.push({ type: "plus", text: txt });
    } else if (mMinus) {
      entries.push({ type: "minus", text: trLog(mMinus[1]) });
    } else if (mStar) {
      entries.push({ type: "star", text: trLog(mStar[1]) });
    } else if (mInfo) {
      entries.push({ type: "info", text: trLog(mInfo[1]) });
    } else if (mBang) {
      entries.push({ type: "error", text: trLog(mBang[1]) });
    }
  }

  log(t("summary"), "white", 0);
  log(t("divider"), "dim", 100);

  var delay = 200;
  var lastWasHeader = false;

  for (var e = 0; e < entries.length; e++) {
    var entry = entries[e];
    if (entry.type === "header") {
      if (lastWasHeader) delay += 50;
      log("\u2500\u2500\u2500 " + entry.text + " \u2500\u2500\u2500", "info", delay);
      delay += 100;
      lastWasHeader = true;
    } else {
      lastWasHeader = false;
      var cls = entry.type === "plus" ? "success" :
                entry.type === "minus" ? "warn" :
                entry.type === "star" ? "dim" :
                entry.type === "error" ? "error" : "dim";
      var prefix = entry.type === "plus" ? "[+]" :
                   entry.type === "minus" ? "[-]" :
                   entry.type === "star" ? "[*]" :
                   entry.type === "error" ? "[!]" : "[i]";
      log(prefix + " " + entry.text, cls, delay);
      delay += 60;
    }
  }

  if (totalFinal) {
    log(t("totalFinal", totalFinal), "success", delay + 100);
    saveCounts(totalFinal, "");
    delay += 300;
  }

  log(t("playlistGenerated", "M3U & M3U8"), "success", delay + 50);

  setTimeout(function () {
    btnEl.disabled = false;
  }, delay + 400);
}

btnEl.addEventListener("click", triggerWorkflow);

dlBtnEl.addEventListener("click", function () {
  window.open(
    getPlaylistUrl() + (sourceSelect.value === "worker" ? "?download=1" : ""),
    "_blank",
  );
});

copyBtnEl.addEventListener("click", function () {
  copyToClipboard(copyBtnEl, getPlaylistUrl());
});

function copyToClipboard(btn, url) {
  navigator.clipboard
    .writeText(url)
    .then(function () {
      var orig = btn.innerHTML;
      btn.innerHTML = "&#x2714; " + t("copied");
      btn.style.color = "#34d399";
      btn.style.borderColor = "#34d399";
      setTimeout(function () {
        btn.innerHTML = orig;
        btn.style.color = "";
        btn.style.borderColor = "";
      }, 2000);
    })
    .catch(function () {
      log(t("copyError"), "error");
    });
}

applyLang();
loadLastRun();

// ── Summary toggle button ──────────────────────────────────────────────────
document
  .getElementById("summary-toggle")
  .addEventListener("click", function () {
    fetch(API_URL + "/status", { method: "POST", body: "{}" })
      .then(function (resp) {
        return resp.json();
      })
      .then(function (data) {
        var runs = data.workflow_runs || [];
        for (var i = 0; i < runs.length; i++) {
          if (
            runs[i].status === "completed" &&
            runs[i].conclusion === "success"
          ) {
            fetchSummary(runs[i].id);
            return;
          }
        }
        log("Nenhum run concluido encontrado.", "warn");
      })
      .catch(function () {
        log("Erro ao buscar resumo.", "error");
      });
  });
// ── EPG Tab ──────────────────────────────────────────────────────────────
(function () {
  var epgView = document.getElementById("epg-view");
  var epgGrid = document.getElementById("epg-grid");
  var epgLoading = document.getElementById("epg-loading");
  var logsView = document.getElementById("logs");
  var progressWrapEl = document.getElementById("progress-wrap");
  var tabsEl = document.getElementById("tabs");
  window._currentTab = "logs";

  // EPG data cache
  var epgData = null;
  var playlistTvgIds = null; // Set of tvg-ids from the ALL playlist

  tabsEl.addEventListener("click", function (e) {
    var tab = e.target.closest(".tab");
    if (!tab) return;
    switchTab(tab.dataset.tab);
  });

  function switchTab(tab) {
    window._currentTab = tab;
    tabsEl.querySelectorAll(".tab").forEach(function (b) {
      b.classList.toggle("active", b.dataset.tab === tab);
    });
    var footerLogs = document.getElementById("footer-logs");
    var footerEpg = document.getElementById("footer-epg");
    if (tab === "epg") {
      logsView.style.display = "none";
      progressWrapEl.style.display = "none";
      epgView.style.display = "block";
      footerLogs.style.display = "none";
      footerEpg.style.display = "";
      loadEPG();
    } else {
      epgView.style.display = "none";
      logsView.style.display = "";
      footerLogs.style.display = "";
      footerEpg.style.display = "none";
    }
  }

  window.switchTab = switchTab;

  function loadEPG() {
    if (epgData && playlistTvgIds) {
      renderEPG();
      return;
    }

    epgLoading.style.display = "block";
    epgGrid.innerHTML = "";
    epgLoading.innerHTML =
      '<div class="log dim">[EPG] ' + t("epgLoading") + "</div>";

    var m3uUrl = API_URL + "/playlist/all.m3u8?_=" + Date.now();

    Promise.all([
      fetch(m3uUrl).then(function (r) {
        return r.text();
      }),
      fetch(API_URL + "/e/BR?_=" + Date.now()).then(
        function (r) {
          if (!r.ok) throw new Error("EPG HTTP " + r.status);
          return r.text();
        },
      ),
    ])
      .then(function (results) {
        playlistTvgIds = extractTvgIds(results[0]);
        var n = Object.keys(playlistTvgIds).length;
        if (n > 0) {
          localStorage.setItem("livewatch-last-epg", n);
          refreshFirstLine();
        }
        parseEPG(results[1]);
      })
      .catch(function (e) {
        epgLoading.innerHTML =
          '<div class="log error">[EPG] ' + t("epgError", e.message) + "</div>";
      });
  }

  function extractTvgIds(m3u) {
    var ids = {};
    var lines = m3u.split("\n");
    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      if (line.indexOf("#EXTINF") !== 0) continue;
      var m = line.match(/tvg-id="([^"]+)"/);
      if (m) ids[m[1]] = true;
    }
    return ids;
  }

  function parseEPG(xml) {
    epgLoading.innerHTML =
      '<div class="log dim">[EPG] ' +
      t("epgParsing", (xml.length / 1e6).toFixed(1)) +
      "</div>";

    setTimeout(function () {
      try {
        var parser = new DOMParser();
        var doc = parser.parseFromString(xml, "text/xml");

        var channels = {};
        var chNodes = doc.getElementsByTagName("channel");
        for (var i = 0; i < chNodes.length; i++) {
          var ch = chNodes[i];
          var id = ch.getAttribute("id");
          var dn = ch.getElementsByTagName("display-name")[0];
          var name = dn
            ? formatChannelName(dn.textContent)
            : formatChannelName(id);
          channels[id] = name;
        }

        var programmes = [];
        var progNodes = doc.getElementsByTagName("programme");
        var now = new Date();
        var windowStart = new Date(now.getTime() - 2 * 3600000);
        var windowEnd = new Date(now.getTime() + 12 * 3600000);

        // Diagnostic counters
        var totalProg = 0;
        var matchedProg = 0;
        var inWindow = 0;
        var matchedChannels = {};

        for (var j = 0; j < progNodes.length; j++) {
          var p = progNodes[j];
          var chId = p.getAttribute("channel");
          totalProg++;

          if (!playlistTvgIds[chId]) continue;
          matchedProg++;

          var start = parseXMLTVDate(p.getAttribute("start"));
          var stop = parseXMLTVDate(p.getAttribute("stop"));
          var title = getText(p, "title");
          var desc = getText(p, "desc");

          if (!start || !stop) continue;

          if (stop < windowStart || start > windowEnd) continue;
          inWindow++;

          programmes.push({
            channel: chId,
            start: start,
            stop: stop,
            title: title,
            desc: desc,
          });
          matchedChannels[chId] = true;
        }

        programmes.sort(function (a, b) {
          if (a.channel !== b.channel)
            return a.channel.localeCompare(b.channel);
          return a.start - b.start;
        });

        epgData = {
          channels: channels,
          programmes: programmes,
          diag: {
            totalProg: totalProg,
            matchedProg: matchedProg,
            inWindow: inWindow,
            matchedChannels: Object.keys(matchedChannels).length,
            playlistChannels: Object.keys(playlistTvgIds).length,
          },
        };
        epgLoading.style.display = "none";
        renderEPG();
      } catch (e) {
        epgLoading.innerHTML =
          '<div class="log error">[EPG] ' +
          t("epgParseError", e.message) +
          "</div>";
      }
    }, 50);
  }

  function parseXMLTVDate(str) {
    if (!str) return null;
    var m = str.match(/(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})/);
    if (!m) return null;
    return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]));
  }

  function getText(el, tag) {
    var child = el.getElementsByTagName(tag)[0];
    return child ? child.textContent : "";
  }

  function formatChannelName(raw) {
    var name = raw.replace(/\.br$/i, "");
    name = name.replace(/\./g, " ");
    // Remove location prefix like "Sao Paulo/SP " or "Sao Paulo/SP  "
    var idx = name.search(/\/[A-Z]{2}\s+/);
    if (idx !== -1) {
      name = name.substring(idx).replace(/^\/[A-Z]{2}\s+/, "");
    }
    name = name.replace(/\s+/g, " ").trim();
    return name || raw;
  }

  function renderEPG() {
    if (!epgData) return;

    var programmes = epgData.programmes;
    var channels = epgData.channels;
    var now = new Date();

    // Group by channel
    var grouped = {};
    for (var i = 0; i < programmes.length; i++) {
      var p = programmes[i];
      if (!grouped[p.channel]) grouped[p.channel] = [];
      grouped[p.channel].push(p);
    }

    var chIds = Object.keys(grouped).sort(function (a, b) {
      var na = (channels[a] || a).toLowerCase();
      var nb = (channels[b] || b).toLowerCase();
      return na.localeCompare(nb);
    });

    if (chIds.length === 0) {
      epgGrid.innerHTML =
        '<div class="epg-empty">[EPG] ' + t("epgNoPrograms") + "</div>";
      return;
    }

    var parts = [];
    for (var c = 0; c < chIds.length; c++) {
      var chId = chIds[c];
      var chName = formatChannelName(channels[chId] || chId);
      var progs = grouped[chId];

      // Find current programme for the collapsed preview
      var currentProg = null;
      for (var p = 0; p < progs.length; p++) {
        if (progs[p].start <= now && progs[p].stop >= now) {
          currentProg = progs[p];
          break;
        }
      }

      parts.push('<div class="epg-channel">');
      parts.push(
        '<div class="epg-channel-header" onclick="this.parentElement.classList.toggle(\'open\')">',
      );
      parts.push('<span class="epg-arrow">&#9654;</span> ');
      parts.push('<span class="epg-ch-name">' + escHtml(chName) + "</span>");
      if (currentProg) {
        parts.push(
          '<span class="epg-now">' +
            escHtml(currentProg.title || "") +
            "</span>",
        );
        parts.push(
          '<span class="epg-now-time">' +
            formatTime(currentProg.start) +
            " - " +
            formatTime(currentProg.stop) +
            "</span>",
        );
      }
      parts.push("</div>");

      parts.push('<div class="epg-programs">');
      for (var q = 0; q < progs.length; q++) {
        var prog = progs[q];
        var isCurrent = prog.start <= now && prog.stop >= now;
        var timeStr = formatTime(prog.start) + " - " + formatTime(prog.stop);

        parts.push(
          '<div class="epg-program' + (isCurrent ? " current" : "") + '">',
        );
        parts.push('<span class="epg-time">' + timeStr + "</span>");
        parts.push(
          '<div><div class="epg-title">' +
            escHtml(prog.title || t("epgNoTitle")) +
            "</div>",
        );
        if (prog.desc) {
          parts.push(
            '<div class="epg-desc">' +
              escHtml(prog.desc.substring(0, 120)) +
              "</div>",
          );
        }
        parts.push("</div></div>");
      }
      parts.push("</div>");
      parts.push("</div>");
    }

    // parts.push(
    //   '<div class="epg-footer">' +
    //     t("epgFooterChannels", chIds.length) +
    //     "</div>",
    // );
    epgGrid.innerHTML = parts.join("");
  }

  function formatTime(d) {
    var h = d.getHours().toString().padStart(2, "0");
    var m = d.getMinutes().toString().padStart(2, "0");
    return h + ":" + m;
  }

  function escHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  // ── EPG Footer actions ──────────────────────────────────────────────────
  var epgCountrySelect = document.getElementById("epg-country-select");
  var epgRefreshBtn = document.getElementById("btn-epg-refresh");
  var epgCopyBtn = document.getElementById("btn-epg-copy");
  var epgDlBtn = document.getElementById("btn-epg-download");

  function getEpgUrl() {
    var country = epgCountrySelect.value || "BR";
    return API_URL + "/e/" + country;
  }

  epgRefreshBtn.addEventListener("click", function () {
    epgData = null;
    playlistTvgIds = null;
    loadEPG();
  });

  epgDlBtn.addEventListener("click", function () {
    window.open(getEpgUrl() + "?download=1", "_blank");
  });

  epgCopyBtn.addEventListener("click", function () {
    navigator.clipboard.writeText(getEpgUrl()).then(function () {
      var orig = epgCopyBtn.innerHTML;
      epgCopyBtn.innerHTML = "&#x2714; " + t("copied");
      epgCopyBtn.style.color = "#34d399";
      epgCopyBtn.style.borderColor = "#34d399";
      setTimeout(function () {
        epgCopyBtn.innerHTML = orig;
        epgCopyBtn.style.color = "";
        epgCopyBtn.style.borderColor = "";
      }, 2000);
    }).catch(function () {
      log(t("copyError"), "error");
    });
  });
})();

var WORKER_URL = "https://livewatch-trigger.otaviozanonn.workers.dev";
var BASE_RAW = "https://raw.githubusercontent.com/otaviozanon/LiveWatch/main/";

var PLAYLISTS = {
  brasil: { file: "LiveWatch-PlaylistBR.m3u8" },
  global: { file: "LiveWatch-PlaylistWorld.m3u8" },
};
var profileSelect = null;

var T = {
  pt: {
    systemReady: "Sistema pronto.",
    dispatching: "Disparando workflow...",
    errorDispatch: "Erro ao disparar: {0}",
    workflowStarted: "Workflow iniciado.",
    fail: "Falha: {0}",
    waitingStart: "Aguardando inicio...",
    running: "Executando...",
    completed: "Concluido",
    playlistUpdated: "Playlist atualizada.",
    workflowFailed: "Workflow FALHOU.",
    summary: "Resumo:",
    divider: "---------------------",
    listsExtracted: "Listas extraidas: {0}",
    listStats: "  {0} | {1} linhas -> {2} entradas",
    totalFiltered: "Total de canais filtrados: {0}",
    totalFinal: "Total final: {0} canais",
    playlistGenerated: "{0} gerado.",
    timeout: "Tempo limite atingido.",
    timeoutShort: "Tempo limite",
    failed: "Falhou",
    btnUpdate: "ATUALIZAR",
    btnDownload: "DOWNLOAD",
    btnCopy: "COPIAR URL",
    copied: "COPIADO",
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
    btnUpdate: "UPDATE",
    btnDownload: "DOWNLOAD",
    btnCopy: "COPY URL",
    copied: "COPIED",
  },
};

var lang = localStorage.getItem("livewatch-lang") || "pt";
var currentProfile = localStorage.getItem("livewatch-profile") || "brasil";

function t(key) {
  var args = Array.prototype.slice.call(arguments, 1);
  var msg = (T[lang] && T[lang][key]) || (T.en[key] || key);
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
var dlBtn = document.getElementById("btn-download");
var updatedEl = document.getElementById("last-updated");
profileSelect = document.getElementById("profile-select");

var progressTimer = null;
var progressVal = 0;

function getPlaylistUrl() {
  return BASE_RAW + PLAYLISTS[currentProfile].file;
}

function applyLang() {
  document.querySelectorAll(".lang-btn").forEach(function (b) {
    b.classList.toggle("active", b.dataset.lang === lang);
  });
  btnEl.innerHTML = "&#x21BB; " + t("btnUpdate");
  dlBtn.innerHTML = "&#x21E9; " + t("btnDownload");
  copyBtn.innerHTML = "&#x2398; " + t("btnCopy");
  logsEl.innerHTML = '<div class="log dim">[LiveWatch] ' + t("systemReady") + "</div>";
  localStorage.setItem("livewatch-lang", lang);
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

function log(msg, cls) {
  cls = cls || "dim";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.textContent = "[LiveWatch] " + msg;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
  return div;
}

function updateClock(d) {
  if (!d) { updatedEl.textContent = "---"; return; }
  updatedEl.textContent = d.toLocaleString(lang === "pt" ? "pt-BR" : "en-US");
}

function loadLastRun() {
  fetch(getPlaylistUrl(), { method: "HEAD", cache: "no-cache" })
    .then(function (resp) {
      var lm = resp.headers.get("Last-Modified");
      if (lm) updateClock(new Date(lm));
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
  log(t("dispatching") + " (" + currentProfile + ")", "action");

  fetch(WORKER_URL + "/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile: currentProfile }),
  })
    .then(function (resp) { return resp.json(); })
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

    fetch(WORKER_URL + "/status", { method: "POST", body: "{}" })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var run = (data.workflow_runs || [])[0];
        if (!run) { setTimeout(tick, delay); return; }

        if (run.status === "in_progress") {
          progressLabel.textContent = t("running");
        }

        if (run.status === "completed") {
          if (run.conclusion === "success") {
            completeProgress(t("completed"));
            var ts = new Date(run.updated_at || run.created_at);
            updateClock(ts);
            fetchSummary(run.id);
          } else {
            completeProgress(t("failed"));
            log(t("workflowFailed"), "error");
            log("https://github.com/otaviozanon/LiveWatch/actions/runs/" + run.id, "dim");
            btnEl.disabled = false;
          }
        } else {
          setTimeout(tick, delay);
        }
      })
      .catch(function () { setTimeout(tick, delay); });
  }

  setTimeout(tick, 2500);
}

function fetchSummary(runId) {
  fetch(WORKER_URL + "/logs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runId: runId }),
  })
    .then(function (resp) { return resp.ok ? resp.text() : null; })
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

function renderSummary(text) {
  var lines = text.split("\n");
  var files = [];
  var stats = {};
  var totals = {};
  var seen = {};

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var idx = line.indexOf("[LiveWatch]");
    if (idx === -1) continue;
    var msg = line.substring(idx + 12).trim();
    var clean = msg.replace(/^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*/, "");
    if (seen[clean]) continue;
    seen[clean] = true;
    var m = clean;

    var em = m.match(/Extraindo lista \d+\/\d+: (.+)/);
    if (em) {
      var fname = em[1].replace(/\.m3u8?$/i, "");
      if (files.indexOf(fname) === -1) files.push(fname);
    }

    var sm = m.match(/Encontrados: (\d+) linhas -> (\d+) entradas/);
    if (sm && files.length > 0) {
      stats[files[files.length - 1]] = { lines: sm[1], entries: sm[2] };
    }

    var tm = m.match(/Total canais \(pos-filtro\): (.+)/);
    if (tm) totals.filtered = tm[1];

    var dm = m.match(/Total final: (.+) canais/);
    if (dm) totals.final = dm[1];
  }

  log(t("summary"), "white");
  log(t("divider"), "dim");

  if (files.length > 0) {
    log(t("listsExtracted", files.join(" | ")), "info");
  }

  for (var k = 0; k < files.length; k++) {
    var f = files[k];
    if (stats[f]) {
      log(t("listStats", f, stats[f].lines, stats[f].entries), "dim");
    }
  }

  if (totals.filtered) {
    log(t("totalFiltered", totals.filtered), "warn");
  }
  if (totals.final) {
    log(t("totalFinal", totals.final), "success");
  }

  log(t("playlistGenerated", PLAYLISTS[currentProfile].file), "success");
  btnEl.disabled = false;
}

btnEl.addEventListener("click", triggerWorkflow);
dlBtn.addEventListener("click", function () {
  window.open(getPlaylistUrl(), "_blank");
});

var copyBtn = document.getElementById("btn-copy");
copyBtn.addEventListener("click", function () {
  var url = getPlaylistUrl();
  navigator.clipboard.writeText(url).then(function () {
    var orig = copyBtn.innerHTML;
    copyBtn.innerHTML = "&#x2714; COPIADO";
    copyBtn.style.color = "#34d399";
    copyBtn.style.borderColor = "#34d399";
    setTimeout(function () {
      copyBtn.innerHTML = orig;
      copyBtn.style.color = "";
      copyBtn.style.borderColor = "";
    }, 2000);
  }).catch(function () {
    log("Erro ao copiar URL.", "error");
  });
});

applyLang();
loadLastRun();

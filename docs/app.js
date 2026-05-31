var WORKER_URL = "https://livewatch-trigger.otaviozanonn.workers.dev";
var PLAYLIST_URL = "https://raw.githubusercontent.com/otaviozanon/LiveWatch/main/playlist.m3u8";

var logsEl = document.getElementById("logs");
var progressWrap = document.getElementById("progress-wrap");
var progressFill = document.getElementById("progress-fill");
var progressLabel = document.getElementById("progress-label");
var btnEl = document.getElementById("btn-update");
var dlBtn = document.getElementById("btn-download");
var updatedEl = document.getElementById("last-updated");

var progressTimer = null;
var progressVal = 0;

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
  updatedEl.textContent = d.toLocaleString("pt-BR");
}

function loadLastRun() {
  fetch(WORKER_URL + "/status", { method: "POST", body: "{}" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      var runs = data.workflow_runs || [];
      for (var i = 0; i < runs.length; i++) {
        if (runs[i].conclusion === "success" && runs[i].status === "completed") {
          updateClock(new Date(runs[i].updated_at));
          return;
        }
      }
    })
    .catch(function () {});
}

function showProgress(label) {
  progressWrap.style.display = "block";
  progressLabel.textContent = label || "Processando...";
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
  log("Disparando workflow...", "action");

  fetch(WORKER_URL + "/trigger", { method: "POST" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) {
        log("Erro ao disparar: " + data.error, "error");
        btnEl.disabled = false;

        return;
      }
      log("Workflow iniciado.", "success");
      showProgress("Aguardando inicio...");
      pollLogs();
    })
    .catch(function (e) {
      log("Falha: " + e.message, "error");
      btnEl.disabled = false;
      dlBtn.disabled = false;
    });
}

function pollLogs() {
  var maxAttempts = 180;
  var delay = 3000;
  var attempt = 0;
  var lastStatus = "";

  function tick() {
    attempt++;
    if (attempt > maxAttempts) {
      completeProgress("Tempo limite");
      log("Timeout.", "warn");
      btnEl.disabled = false;
      dlBtn.disabled = false;
      return;
    }

    fetch(WORKER_URL + "/status", { method: "POST", body: "{}" })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var run = (data.workflow_runs || [])[0];
        if (!run) { setTimeout(tick, delay); return; }

        if (lastStatus !== run.status) {
          lastStatus = run.status;
          if (run.status === "in_progress") {
            progressLabel.textContent = "Executando...";
          }
        }

        if (run.status === "completed") {
          if (run.conclusion === "success") {
            completeProgress("Concluido");
            var ts = new Date(run.updated_at || run.created_at);
            updateClock(ts);
            fetchSummary(run.id);
          } else {
            completeProgress("Falhou");
            log("Workflow FALHOU.", "error");
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
        log("Playlist atualizada.", "success");
        btnEl.disabled = false;

        return;
      }
      renderSummary(text);
    })
    .catch(function () {
      log("Playlist atualizada.", "success");
      btnEl.disabled = false;
      dlBtn.disabled = false;
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

  log("Resumo:", "white");
  log("---------------------", "dim");

  if (files.length > 0) {
    log("Listas extraidas: " + files.join(" | "), "info");
  }

  for (var k = 0; k < files.length; k++) {
    var f = files[k];
    if (stats[f]) {
      log("  " + f + " | " + stats[f].lines + " linhas -> " + stats[f].entries + " entradas", "dim");
    }
  }

  if (totals.filtered) {
    log("Total de canais filtrados: " + totals.filtered, "warn");
  }
  if (totals.final) {
    log("Total final: " + totals.final + " canais", "success");
  }

  log("LiveWatch-Playlist.m3u8 gerado.", "success");
  btnEl.disabled = false;
  dlBtn.disabled = false;
}

btnEl.addEventListener("click", triggerWorkflow);
dlBtn.addEventListener("click", function () {
  window.open(PLAYLIST_URL, "_blank");
});
loadLastRun();

var WORKER_URL = "https://livewatch-trigger.otaviozanonn.workers.dev";
var PLAYLIST_URL = "https://raw.githubusercontent.com/otaviozanon/LiveWatch/main/playlist.m3u8";

var logsEl = document.getElementById("logs");
var btnEl = document.getElementById("btn-update");
var dlBtn = document.getElementById("btn-download");
var updatedEl = document.getElementById("last-updated");

var lastClickTime = null;
var dimLines = [];

function log(msg, cls) {
  cls = cls || "dim";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.textContent = msg;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
  return div;
}

function logAnimated(msg, cls, delay, cb) {
  cls = cls || "dim";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.style.opacity = "0";
  div.style.transform = "translateY(4px)";
  div.style.transition = "opacity 0.3s, transform 0.3s";
  div.textContent = msg;
  logsEl.appendChild(div);
  setTimeout(function () {
    div.style.opacity = "1";
    div.style.transform = "translateY(0)";
  }, delay || 30);
  logsEl.scrollTop = logsEl.scrollHeight;
  if (cb) setTimeout(cb, (delay || 30) + 320);
  return div;
}

function updateClock(d) {
  if (!d) { updatedEl.textContent = "---"; return; }
  updatedEl.textContent = d.toLocaleString("pt-BR");
}

function loadLastModified() {
  fetch(PLAYLIST_URL, { method: "HEAD", cache: "no-cache" })
    .then(function (resp) {
      var lm = resp.headers.get("Last-Modified");
      if (lm) updateClock(new Date(lm));
    })
    .catch(function () {});
}

function triggerWorkflow() {
  btnEl.disabled = true;
  dlBtn.disabled = true;
  lastClickTime = new Date();
  updateClock(lastClickTime);
  log("");

  logAnimated("  Disparando workflow...", "action", 0);
  log("");

  fetch(WORKER_URL + "/trigger", { method: "POST" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) {
        log("  Erro: " + data.error, "error");
        btnEl.disabled = false;
        dlBtn.disabled = false;
        return;
      }
      log("  Workflow iniciado!", "success");
      pollLogs();
    })
    .catch(function (e) {
      log("  Falha: " + e.message, "error");
      btnEl.disabled = false;
      dlBtn.disabled = false;
    });
}

function pollLogs() {
  var maxAttempts = 180;
  var delay = 3000;
  var attempt = 0;
  var startTime = Date.now();
  var lastStatus = "";

  function tick() {
    attempt++;
    if (attempt > maxAttempts) {
      log("  Tempo limite atingido.", "warn");
      btnEl.disabled = false;
      dlBtn.disabled = false;
      return;
    }

    fetch(WORKER_URL + "/status", { method: "POST", body: "{}" })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var run = (data.workflow_runs || [])[0];
        if (!run) { setTimeout(tick, delay); return; }

        if (lastStatus !== run.status && attempt > 1) {
          lastStatus = run.status;
          log("  " + run.status, "dim");
        }

        if (run.status === "completed") {
          var elapsed = Math.round((Date.now() - startTime) / 1000);
          if (run.conclusion === "success") {
            var ts = new Date(run.updated_at || run.created_at);
            updateClock(ts);
            fetchSummary(run.id, elapsed);
          } else {
            log("  FALHOU! Detalhes:", "error");
            log("  https://github.com/otaviozanon/LiveWatch/actions/runs/" + run.id, "dim");
            btnEl.disabled = false;
            dlBtn.disabled = false;
          }
        } else {
          setTimeout(tick, delay);
        }
      })
      .catch(function () { setTimeout(tick, delay); });
  }

  setTimeout(tick, 2500);
}

function fetchSummary(runId, elapsed) {
  fetch(WORKER_URL + "/logs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runId: runId }),
  })
    .then(function (resp) { return resp.ok ? resp.text() : null; })
    .then(function (text) {
      if (!text) {
        log("  Concluido em " + elapsed + "s.", "success");
        btnEl.disabled = false;
        dlBtn.disabled = false;
        return;
      }
      renderSummary(text, elapsed);
    })
    .catch(function () {
      log("  Concluido em " + elapsed + "s.", "success");
      btnEl.disabled = false;
      dlBtn.disabled = false;
    });
}

function renderSummary(text, elapsed) {
  var lines = text.split("\n");
  var seen = {};
  var entries = [];

  for (var i = 0; i < lines.length; i++) {
    var line = lines[i];
    var idx = line.indexOf("[LiveWatch]");
    if (idx === -1) continue;
    var msg = line.substring(idx + 12).trim();
    var key = msg.replace(/^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*/, "");
    if (seen[key]) continue;
    seen[key] = true;
    entries.push(key);
  }

  var delay = 0;
  log("");
  log("  Resumo da execucao:", "white");

  for (var j = 0; j < entries.length; j++) {
    var m = entries[j];
    if (m.indexOf("ERRO") !== -1) {
      logAnimated("    " + m, "error", delay);
    } else if (m.indexOf("Extraindo lista") !== -1) {
      delay += 100;
      logAnimated("    " + m, "info", delay);
    } else if (m.indexOf("Encontrados:") !== -1) {
      logAnimated("      " + m, "dim", delay);
    } else if (m.indexOf("Total canais (pos-filtro)") !== -1) {
      delay += 60;
      logAnimated("    " + m, "warn", delay);
    } else if (m.indexOf("Removendo duplicados") !== -1) {
      delay += 40;
      logAnimated("    " + m, "warn", delay);
    } else if (m.indexOf("Renomeando conflitos") !== -1) {
      delay += 40;
      logAnimated("    " + m, "warn", delay);
    } else if (m.indexOf("Total final:") !== -1) {
      delay += 60;
      logAnimated("    " + m, "success", delay);
    } else if (m.indexOf("playlist.m3u8 gerada") !== -1) {
      logAnimated("    " + m, "success", delay + 40);
    } else if (m.indexOf("Playlist salva") !== -1) {
      logAnimated("    " + m, "success", delay + 40);
    }
  }

  setTimeout(function () {
    log("");
    log("  Concluido em " + elapsed + "s. Playlist atualizada.", "success");
    btnEl.disabled = false;
    dlBtn.disabled = false;
  }, delay + 500);
}

btnEl.addEventListener("click", triggerWorkflow);
dlBtn.addEventListener("click", function () {
  window.open(PLAYLIST_URL, "_blank");
});
loadLastModified();

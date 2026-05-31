var WORKER_URL = "https://livewatch-trigger.otaviozanonn.workers.dev";
var PLAYLIST_URL = "https://raw.githubusercontent.com/otaviozanon/LiveWatch/main/playlist.m3u8";

var logsEl = document.getElementById("logs");
var btnEl = document.getElementById("btn-update");
var dlBtn = document.getElementById("btn-download");
var updatedEl = document.getElementById("last-updated");

var ICONS = {
  play: "\u25B6",
  check: "\u2714",
  spin: "\u21BB",
  error: "\u2718",
  file: "\u{1F4C4}",
  filter: "\u{1F50D}",
  dedup: "\u{1F5D1}",
  done: "\u{1F389}",
  clock: "\u{1F552}",
  bullet: "\u25CF",
};

function log(msg, cls) {
  cls = cls || "info";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.textContent = msg;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
  return div;
}

function logAnimated(msg, cls, delay, cb) {
  cls = cls || "info";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.style.opacity = "0";
  div.style.transform = "translateY(6px)";
  div.style.transition = "opacity 0.25s, transform 0.25s";
  div.textContent = msg;
  logsEl.appendChild(div);
  setTimeout(function () {
    div.style.opacity = "1";
    div.style.transform = "translateY(0)";
  }, delay || 50);
  logsEl.scrollTop = logsEl.scrollHeight;
  if (cb) setTimeout(cb, (delay || 50) + 280);
  return div;
}

function updateLastModified() {
  fetch(PLAYLIST_URL, { method: "HEAD", cache: "no-cache" })
    .then(function (resp) {
      var lm = resp.headers.get("Last-Modified");
      if (lm) {
        var d = new Date(lm);
        updatedEl.textContent = d.toLocaleString("pt-BR");
        updatedEl.className = "";
      } else {
        updatedEl.textContent = "N/A";
      }
    })
    .catch(function () {
      updatedEl.textContent = "Erro";
    });
}

function triggerWorkflow() {
  btnEl.disabled = true;
  dlBtn.disabled = true;
  log("");
  log(ICONS.spin + " Disparando workflow...", "action");

  fetch(WORKER_URL + "/trigger", { method: "POST" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) {
        log(ICONS.error + " Erro: " + data.error, "error");
        btnEl.disabled = false;
        dlBtn.disabled = false;
        return;
      }
      log(ICONS.check + " Workflow iniciado!", "success");
      pollLogs();
    })
    .catch(function (e) {
      log(ICONS.error + " Falha: " + e.message, "error");
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
      log(ICONS.clock + " Timeout.", "warn");
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
          log(ICONS.bullet + " Status: " + run.status, "dim");
        }

        if (run.status === "completed") {
          if (run.conclusion === "success") {
            fetchSummary(run.id);
          } else {
            log(ICONS.error + " Action FALHOU! " +
              "https://github.com/otaviozanon/LiveWatch/actions/runs/" + run.id, "error");
            btnEl.disabled = false;
            dlBtn.disabled = false;
          }
          updateLastModified();
        } else {
          setTimeout(tick, delay);
        }
      })
      .catch(function () { setTimeout(tick, delay); });
  }

  setTimeout(tick, 2000);
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
        log(ICONS.check + " Concluido com sucesso.", "success");
        btnEl.disabled = false;
        dlBtn.disabled = false;
        return;
      }
      renderSummary(text);
    })
    .catch(function () {
      log(ICONS.check + " Concluido com sucesso.", "success");
      btnEl.disabled = false;
      dlBtn.disabled = false;
    });
}

function renderSummary(text) {
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
  log("", "dim");
  log(ICONS.file + " Resumo:", "info");

  for (var j = 0; j < entries.length; j++) {
    var m = entries[j];
    if (m.indexOf("ERRO") !== -1) {
      logAnimated("  " + ICONS.error + " " + m, "error", delay);
    } else if (m.indexOf("Extraindo lista") !== -1) {
      delay += 120;
      logAnimated("  " + ICONS.play + " " + m, "info", delay);
    } else if (m.indexOf("Encontrados:") !== -1) {
      logAnimated("    " + m, "dim", delay);
    } else if (m.indexOf("Total canais (pos-filtro)") !== -1) {
      logAnimated("  " + ICONS.filter + " " + m, "warn", delay + 80);
    } else if (m.indexOf("Removendo duplicados") !== -1) {
      logAnimated("  " + ICONS.dedup + " " + m, "warn", delay + 80);
    } else if (m.indexOf("Renomeando conflitos") !== -1) {
      logAnimated("  " + ICONS.dedup + " " + m, "warn", delay + 80);
    } else if (m.indexOf("Total final:") !== -1) {
      delay += 80;
      logAnimated("  " + ICONS.check + " " + m, "success", delay);
    } else if (m.indexOf("playlist.m3u8 gerada") !== -1) {
      logAnimated("  " + ICONS.check + " " + m, "success", delay + 80);
    } else if (m.indexOf("Playlist salva") !== -1) {
      logAnimated("  " + ICONS.done + " " + m, "success", delay + 80);
    }
  }

  setTimeout(function () {
    log("", "dim");
    log(ICONS.done + " Pronto! " + entries.length + " etapas concluidas.", "success");
    btnEl.disabled = false;
    dlBtn.disabled = false;
  }, delay + 400);
}

btnEl.addEventListener("click", triggerWorkflow);
dlBtn.addEventListener("click", function () {
  window.open(PLAYLIST_URL, "_blank");
});
updateLastModified();

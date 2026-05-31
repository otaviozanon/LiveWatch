var WORKER_URL = "https://livewatch-trigger.otaviozanonn.workers.dev";
var PLAYLIST_URL = "https://raw.githubusercontent.com/otaviozanon/LiveWatch/main/playlist.m3u8";

var logsEl = document.getElementById("logs");
var btnEl = document.getElementById("btn-update");
var dlBtn = document.getElementById("btn-download");
var updatedEl = document.getElementById("last-updated");

function log(msg, cls) {
  cls = cls || "info";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.textContent = "[LiveWatch] " + msg;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
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
  log("Disparando workflow...", "action");

  fetch(WORKER_URL + "/trigger", { method: "POST" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) {
        log("Erro ao disparar: " + data.error, "error");
        btnEl.disabled = false;
        dlBtn.disabled = false;
        return;
      }
      log("Workflow iniciado. Aguardando inicio da action...", "success");
      pollLogs();
    })
    .catch(function (e) {
      log("Falha ao conectar: " + e.message, "error");
      btnEl.disabled = false;
      dlBtn.disabled = false;
    });
}

function pollLogs() {
  var maxAttempts = 120;
  var delay = 3000;
  var attempt = 0;
  var lastStatus = "";
  var startedAt = Date.now();

  function tick() {
    attempt++;
    if (attempt > maxAttempts) {
      log("Timeout — a action pode ainda estar rodando.", "warn");
      btnEl.disabled = false;
      dlBtn.disabled = false;
      return;
    }

    fetch(WORKER_URL + "/status", { method: "POST", body: "{}" })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var run = (data.workflow_runs || [])[0];
        if (!run) {
          setTimeout(tick, delay);
          return;
        }

        if (lastStatus !== run.status) {
          lastStatus = run.status;
          log("Status: " + run.status + " | Run #" + run.id, "dim");
        }

        if (run.status === "completed") {
          var elapsed = Math.round((Date.now() - startedAt) / 1000);
          if (run.conclusion === "success") {
            log("Action concluida com SUCESSO em " + elapsed + "s.", "success");
            fetchSummary(run.id);
          } else {
            log("Action FALHOU! Verifique: https://github.com/otaviozanon/LiveWatch/actions/runs/" + run.id, "error");
          }
          updateLastModified();
          btnEl.disabled = false;
          dlBtn.disabled = false;
        } else {
          setTimeout(tick, delay);
        }
      })
      .catch(function (e) {
        log("Erro no polling: " + e.message, "error");
        setTimeout(tick, delay);
      });
  }

  setTimeout(tick, delay);
}

function fetchSummary(runId) {
  fetch(WORKER_URL + "/logs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ runId: runId }),
  })
    .then(function (resp) {
      if (!resp.ok) return;
      return resp.text();
    })
    .then(function (text) {
      if (!text) return;
      var lines = text.split("\n");
      var liveLines = [];
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (line.indexOf("LiveWatch") !== -1) {
          liveLines.push(line);
        }
      }
      if (liveLines.length > 0) {
        log("--- Resumo da execucao ---", "dim");
        for (var j = 0; j < liveLines.length; j++) {
          var m = liveLines[j];
          if (m.indexOf("ERRO") !== -1 || m.indexOf("Falha") !== -1) {
            log(m, "error");
          } else if (m.indexOf("Removendo") !== -1 || m.indexOf("Renomeando") !== -1 || m.indexOf("Total") !== -1) {
            log(m, "warn");
          } else if (m.indexOf("gerada") !== -1 || m.indexOf("salva") !== -1) {
            log(m, "success");
          } else if (m.indexOf("Extraindo") !== -1 || m.indexOf("Encontrados") !== -1) {
            log(m, "info");
          } else {
            log(m, "dim");
          }
        }
      }
    })
    .catch(function () {});
}

btnEl.addEventListener("click", triggerWorkflow);
dlBtn.addEventListener("click", function () {
  window.open(PLAYLIST_URL, "_blank");
});
updateLastModified();

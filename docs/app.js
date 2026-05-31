var WORKER_URL = "https://REPLACE_ME.workers.dev/trigger";
var GH_OWNER = "otaviozanon";
var GH_REPO = "LiveWatch";

var logsEl = document.getElementById("logs");
var btnEl = document.getElementById("btn-update");

function log(msg, cls) {
  cls = cls || "info";
  var div = document.createElement("div");
  div.className = "log " + cls;
  div.textContent = "[LiveWatch] " + msg;
  logsEl.appendChild(div);
  logsEl.scrollTop = logsEl.scrollHeight;
}

function triggerWorkflow() {
  btnEl.disabled = true;
  log("Disparando workflow...", "action");

  fetch(WORKER_URL, { method: "POST" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) {
      if (!data.ok) {
        log("Erro ao disparar: " + data.error, "error");
        btnEl.disabled = false;
        return;
      }
      log("Workflow iniciado. Aguardando inicio da action...", "success");
      pollLogs();
    })
    .catch(function (e) {
      log("Falha: " + e.message, "error");
      btnEl.disabled = false;
    });
}

function pollLogs() {
  var found = false;
  var maxAttempts = 120;
  var delay = 3000;
  var attempt = 0;

  function tick() {
    attempt++;
    if (attempt > maxAttempts) {
      log("Timeout — a action pode ainda estar rodando.", "warn");
      btnEl.disabled = false;
      return;
    }

    fetch("https://api.github.com/repos/" + GH_OWNER + "/" + GH_REPO + "/actions/runs?per_page=3")
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        var run = data.workflow_runs[0];
        if (!run) {
          setTimeout(tick, delay);
          return;
        }

        if (!found) {
          log("Run ID: #" + run.id + " — Status: " + run.status, "dim");
          found = true;
        }

        if (run.status === "completed") {
          fetchAndDisplayLogs(run.id, function () {
            log("Concluido. Sistema pronto para proxima acao.", "success");
            btnEl.disabled = false;
          });
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

function fetchAndDisplayLogs(runId, cb) {
  fetch("https://api.github.com/repos/" + GH_OWNER + "/" + GH_REPO + "/actions/runs/" + runId + "/logs")
    .then(function (resp) {
      if (!resp.ok) {
        log("Nao foi possivel buscar logs (talvez ainda nao estejam disponiveis).", "warn");
        if (cb) cb();
        return;
      }
      return resp.text();
    })
    .then(function (text) {
      if (!text) return;
      var lines = text.split("\n");
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (!line.trim()) continue;
        var idx = line.indexOf("[LiveWatch]");
        if (idx === -1) continue;
        var msg = line.substring(idx + 12).trim();
        if (msg.indexOf("ERRO") !== -1 || msg.indexOf("Falha") !== -1) {
          log(msg, "error");
        } else if (msg.indexOf("Removendo") !== -1 || msg.indexOf("Renomeando") !== -1 || msg.indexOf("Total") !== -1) {
          log(msg, "warn");
        } else if (msg.indexOf("gerada") !== -1 || msg.indexOf("salva") !== -1 || msg.indexOf("Concluido") !== -1) {
          log(msg, "success");
        } else if (msg.indexOf("Extraindo") !== -1 || msg.indexOf("Encontrados") !== -1) {
          log(msg, "info");
        } else {
          log(msg, "dim");
        }
      }
      if (cb) cb();
    })
    .catch(function (e) {
      log("Erro ao buscar logs: " + e.message, "error");
      if (cb) cb();
    });
}

btnEl.addEventListener("click", triggerWorkflow);

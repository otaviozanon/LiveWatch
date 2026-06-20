var WORKER_URL = "https://livewatch-trigger.otaviozanonn.workers.dev";
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
    copyError: "Erro ao copiar URL.",
    sourceWorker: "Link curto",
    sourceRaw: "Raw GitHub",
    profileBrasil: "Brasil",
    profileGlobal: "Global",
    profileIptvorg: "IPTV-ORG",
    profileAll: "Todos",
    headerTitle: "LiveWatch &mdash; Lista IPTV",
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
    copyError: "Error copying URL.",
    sourceWorker: "Short link",
    sourceRaw: "Raw GitHub",
    profileBrasil: "Brazil",
    profileGlobal: "Global",
    profileIptvorg: "IPTV-ORG",
    profileAll: "All",
    headerTitle: "LiveWatch &mdash; IPTV List",
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
  return WORKER_URL + "/playlist/" + currentProfile + "." + format;
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
  profileSelect.options[3].text = t("profileAll");
  document.getElementById("header-title").innerHTML = t("headerTitle");
  logsEl.innerHTML =
    '<div class="log dim">[LiveWatch] ' + t("systemReady") + "</div>";
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
  if (!d) {
    updatedEl.textContent = "---";
    return;
  }
  updatedEl.textContent = d.toLocaleString(lang === "pt" ? "pt-BR" : "en-US");
}

function loadLastRun() {
  fetch(WORKER_URL + "/file-time", {
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
  log(t("dispatching") + " (" + currentProfile + ")", "action");

  fetch(WORKER_URL + "/trigger", {
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
  fetch(WORKER_URL + "/logs", {
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
  var files = [];
  var stats = {};
  var totals = {};
  var seen = {};
  var currentPerfil = null;

  for (var i = 0; i < lines.length; i++) {
    var line = stripAnsi(lines[i]);
    var idx = line.indexOf("[LiveWatch]");
    if (idx === -1) continue;
    var msg = line.substring(idx + 12).trim();
    var clean = msg.replace(/^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s*/, "");
    if (!clean) continue;
    if (seen[clean]) continue;
    seen[clean] = true;
    var m = clean;

    var pm = m.match(/====== Perfil: (.+) ======/);
    if (pm) {
      currentPerfil = pm[1];
      if (files.indexOf(currentPerfil) === -1) files.push(currentPerfil);
    }

    var em = m.match(/Extraindo lista \d+\/\d+: (.+)/);
    if (em) {
      var fname = em[1].replace(/\.m3u8?$/i, "");
      if (files.indexOf(fname) === -1) files.push(fname);
    }

    var sm = m.match(/Encontrados:\s*(\d+)\s+linhas\s*->\s*(\d+)\s+entradas/);
    if (sm && files.length > 0) {
      stats[files[files.length - 1]] = { lines: sm[1], entries: sm[2] };
    }

    var jm = m.match(/Baixando JSON: (.+)/);
    if (jm) {
      var jname = jm[1] + (currentPerfil ? " (" + currentPerfil + ")" : "");
      if (files.indexOf(jname) === -1) files.push(jname);
    }

    var jsm = m.match(/Streams com match para \w+:\s*(\d+)/);
    if (jsm && files.length > 0) {
      stats[files[files.length - 1]] = { lines: "-", entries: jsm[1] };
    }

    var tm = m.match(/Total (?:canais|final)\s*(?:\(pos-filtro\)|combinados)?\s*:\s*(.+)/);
    if (tm) totals.filtered = tm[1];

    var dm = m.match(/Total final:\s*(.+?)\s+canais/);
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

  log(t("playlistGenerated", "M3U & M3U8"), "success");
  btnEl.disabled = false;
}

btnEl.addEventListener("click", triggerWorkflow);

dlBtnEl.addEventListener("click", function () {
  window.open(getPlaylistUrl() + (sourceSelect.value === "worker" ? "?download=1" : ""), "_blank");
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
    if (tab === "epg") {
      logsView.style.display = "none";
      progressWrapEl.style.display = "none";
      epgView.style.display = "block";
      loadEPG();
    } else {
      epgView.style.display = "none";
      logsView.style.display = "";
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
    epgLoading.innerHTML = '<div class="log dim">[EPG] Carregando playlist e guia...</div>';

    // Fetch ALL playlist M3U to extract which tvg-ids we care about
    var m3uUrl = WORKER_URL + "/playlist/all.m3u8?_=" + Date.now();

    Promise.all([
      fetch(m3uUrl).then(function (r) { return r.text(); }),
      fetch(WORKER_URL + "/epg?source=all&country=BR&_=" + Date.now()).then(function (r) {
        if (!r.ok) throw new Error("EPG HTTP " + r.status);
        return r.text();
      }),
    ])
      .then(function (results) {
        var m3u = results[0];
        var xml = results[1];
        playlistTvgIds = extractTvgIds(m3u);
        // Debug: show first 50 tvg-ids and sample lines
        var sampleTvgIds = Object.keys(playlistTvgIds).slice(0, 5);
        var lines = m3u.split("\n");
        var sampleLines = [];
        for (var i = 0; i < lines.length && sampleLines.length < 3; i++) {
          if (lines[i].indexOf("tvg-id=") !== -1) sampleLines.push(lines[i].substring(0, 200));
        }
        console.log("[EPG] M3U size:", m3u.length, "chars, lines:", lines.length,
          "tvg-ids:", Object.keys(playlistTvgIds).length,
          "sample tvg-ids:", sampleTvgIds,
          "sample lines:", sampleLines);
        parseEPG(xml);
      })
      .catch(function (e) {
        epgLoading.innerHTML = '<div class="log error">[EPG] Erro: ' + e.message + '</div>';
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
    epgLoading.innerHTML = '<div class="log dim">[EPG] Processando ' + (xml.length / 1e6).toFixed(1) + ' MB de XML...</div>';

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
          var name = dn ? formatChannelName(dn.textContent) : formatChannelName(id);
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
          if (a.channel !== b.channel) return a.channel.localeCompare(b.channel);
          return a.start - b.start;
        });

        console.log("[EPG] EPG channels:", Object.keys(channels).length, "total prog:", totalProg,
          "matched:", matchedProg, "in window:", inWindow, "unique channels:", Object.keys(matchedChannels).length);
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
        epgLoading.innerHTML = '<div class="log error">[EPG] Erro ao processar: ' + e.message + '</div>';
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
    // Clean EPG channel IDs/names: remove .br suffix, replace dots with spaces
    var name = raw.replace(/\.br$/i, "");
    name = name.replace(/\./g, " ");
    // Remove location prefix like "Sao Paulo/SP  " -> just the channel name
    var parts = name.split("  ");
    if (parts.length > 1) name = parts[parts.length - 1];
    // Clean up multiple spaces and trim
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
      epgGrid.innerHTML = '<div class="epg-empty">[EPG] Nenhum programa encontrado para os canais da playlist.</div>';
      return;
    }

    var html = "";
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

      html += '<div class="epg-channel">';
      html += '<div class="epg-channel-header" onclick="this.parentElement.classList.toggle(\'open\')">';
      html += '<span class="epg-arrow">&#9654;</span> ';
      html += '<span class="epg-ch-name">' + escHtml(chName) + '</span>';
      if (currentProg) {
        html += '<span class="epg-now">' + escHtml(currentProg.title || "") + '</span>';
        html += '<span class="epg-now-time">' + formatTime(currentProg.start) + ' - ' + formatTime(currentProg.stop) + '</span>';
      }
      html += '</div>';

      html += '<div class="epg-programs">';
      for (var q = 0; q < progs.length; q++) {
        var prog = progs[q];
        var isCurrent = prog.start <= now && prog.stop >= now;
        var timeStr = formatTime(prog.start) + " - " + formatTime(prog.stop);

        html += '<div class="epg-program' + (isCurrent ? " current" : "") + '">';
        html += '<span class="epg-time">' + timeStr + '</span>';
        html += '<div><div class="epg-title">' + escHtml(prog.title || "Sem titulo") + '</div>';
        if (prog.desc) {
          html += '<div class="epg-desc">' + escHtml(prog.desc.substring(0, 120)) + '</div>';
        }
        html += '</div></div>';
      }
      html += '</div>';
      html += '</div>';
    }

    var d = epgData.diag || {};
    html += '<div class="epg-footer">' +
      chIds.length + ' canais com programacao | ' +
      d.matchedChannels + '/' + d.playlistChannels + ' canais da playlist | ' +
      d.inWindow + ' programas de ' + d.totalProg + ' totais' +
      '</div>';
    epgGrid.innerHTML = html;
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
})();

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    // API routes - handle by worker
    const isApi = url.pathname.startsWith("/p/") || url.pathname.startsWith("/e/") ||
                  url.pathname.startsWith("/playlist") || url.pathname.startsWith("/epg") ||
                  url.pathname === "/trigger" || url.pathname === "/logs" ||
                  url.pathname === "/status" || url.pathname === "/file-time";

    if (isApi) {
      if ((request.method === "GET" || request.method === "HEAD") && url.pathname.startsWith("/playlist/")) {
        return handlePlaylist(url, env, corsHeaders, request.method);
      }
      if (request.method === "GET" && url.pathname.startsWith("/p/")) {
        var pUrl = new URL(request.url);
        pUrl.pathname = "/playlist" + pUrl.pathname.substring(2);
        return handlePlaylist(pUrl, env, corsHeaders, "GET");
      }
      if (request.method === "GET" && url.pathname.startsWith("/e/")) {
        return handleEPGShort(url, env, corsHeaders);
      }
      if (request.method === "GET" && url.pathname === "/playlist") {
        return handlePlaylist(url, env, corsHeaders, "GET");
      }
      if (request.method === "GET" && url.pathname.startsWith("/epg")) {
        return handleEPG(url, env, corsHeaders);
      }

      if (request.method === "POST") {
        const gh = { Authorization: `Bearer ${env.GITHUB_PAT}`, Accept: "application/vnd.github+json", "User-Agent": "LiveWatch" };
        if (url.pathname === "/trigger") {
          let body = {}; try { body = await request.json(); } catch (e) {}
          const profile = body.profile || "brasil";
          const apiUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_ID}/dispatches`;
          const resp = await fetch(apiUrl, { method: "POST", headers: gh, body: JSON.stringify({ ref: "main", inputs: { profile } }) });
          if (resp.ok) return json({ ok: true }, corsHeaders);
          return json({ ok: false, error: await resp.text() }, corsHeaders, 502);
        }
        if (url.pathname === "/logs") {
          const body = await request.json();
          const apiUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${body.runId}/logs`;
          const resp = await fetch(apiUrl, { method: "GET", headers: gh, redirect: "follow" });
          if (!resp.ok) return json({ ok: false, error: "Logs not available" }, corsHeaders, resp.status);
          const text = await resp.text();
          return new Response(text, { headers: { ...corsHeaders, "Content-Type": "text/plain; charset=utf-8" } });
        }
        if (url.pathname === "/status") {
          const body = await request.json();
          const apiUrl = body.runId
            ? `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${body.runId}`
            : `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs?per_page=3`;
          const resp = await fetch(apiUrl, { method: "GET", headers: gh });
          const data = await resp.text();
          return new Response(data, { status: resp.status, headers: { ...corsHeaders, "Content-Type": "application/json" } });
        }
        if (url.pathname === "/file-time") {
          const body = await request.json();
          const path = body.path || "";
          const apiUrl = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/commits?path=${encodeURIComponent(path)}&per_page=1`;
          const resp = await fetch(apiUrl, { method: "GET", headers: gh });
          const data = await resp.json();
          const ts = (data[0] && data[0].commit && data[0].commit.committer) ? data[0].commit.committer.date : null;
          return json({ date: ts }, corsHeaders);
        }
        return json({ ok: false, error: "Unknown endpoint" }, corsHeaders, 404);
      }

      return json({ ok: false, error: "Method not allowed" }, corsHeaders, 405);
    }

    // Not an API route - serve static assets
    return env.ASSETS.fetch(request);
  }
};

function json(obj, headers, status) {
  return new Response(JSON.stringify(obj), {
    status: status || 200,
    headers: { ...headers, "Content-Type": "application/json" },
  });
}

const PLAYLIST_NAMES = {
  brasil: { m3u: "LiveWatch-PlaylistBR.m3u", m3u8: "LiveWatch-PlaylistBR.m3u8" },
  global: { m3u: "LiveWatch-PlaylistWorld.m3u", m3u8: "LiveWatch-PlaylistWorld.m3u8" },
  "iptv-org": { m3u: "LiveWatch-PlaylistIPTVORG.m3u", m3u8: "LiveWatch-PlaylistIPTVORG.m3u8" },
  all: { m3u: "LiveWatch-PlaylistAll.m3u", m3u8: "LiveWatch-PlaylistAll.m3u8" },
};
const CONTENT_TYPES = { m3u8: "application/vnd.apple.mpegurl", m3u: "audio/x-mpegurl" };

async function handlePlaylist(url, env, corsHeaders, method) {
  var profile = url.searchParams.get("profile");
  var format = url.searchParams.get("format");
  if (!profile || !format) {
    var pathPart = url.pathname.replace("/playlist/", "");
    var dotIdx = pathPart.lastIndexOf(".");
    if (dotIdx !== -1) { format = pathPart.substring(dotIdx + 1).toLowerCase(); profile = pathPart.substring(0, dotIdx).toLowerCase(); }
  }
  profile = profile || "brasil"; format = format || "m3u8";
  const pf = PLAYLIST_NAMES[profile];
  if (!pf) return new Response("Unknown profile", { status: 400, headers: { ...corsHeaders } });
  const filename = pf[format];
  if (!filename) return new Response("Unknown format", { status: 400, headers: { ...corsHeaders } });
  const rawUrl = `https://raw.githubusercontent.com/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/main/playlists/${format}/${filename}`;
  const resp = await fetch(rawUrl, { method: "GET", headers: { "User-Agent": "LiveWatch" } });
  if (!resp.ok) return new Response("Playlist not found", { status: resp.status, headers: { ...corsHeaders } });
  const body = await resp.text();
  const responseHeaders = { ...corsHeaders, "Content-Type": CONTENT_TYPES[format] || "audio/x-mpegurl", "Cache-Control": "public, max-age=60" };
  if (url.searchParams.get("download") === "1") responseHeaders["Content-Disposition"] = "attachment; filename=\"" + filename + "\"";
  if (method === "HEAD") return new Response(null, { headers: responseHeaders });
  return new Response(body, { headers: responseHeaders });
}

async function handleEPG(url, env, corsHeaders) {
  var country = url.searchParams.get("country") || "BR";
  var source = url.searchParams.get("source") || "all";
  var pathPart = url.pathname.replace("/epg/", "").replace("/epg", "");
  if (pathPart) country = pathPart.toUpperCase();
  return fetchEPG(country, source, env, corsHeaders, url);
}

async function handleEPGShort(url, env, corsHeaders) {
  var country = url.pathname.replace("/e/", "").replace("/e", "").toUpperCase() || "BR";
  var u = new URL(url);
  return fetchEPG(country, "all", env, corsHeaders, u);
}

async function fetchEPG(country, source, env, corsHeaders, url) {
  var allSources = [];
  if (country === "BR") {
    allSources.push("https://epgshare01.online/epgshare01/epg_ripper_BR1.xml.gz");
    allSources.push("https://epgshare01.online/epgshare01/epg_ripper_BR2.xml.gz");
    allSources.push("https://raw.githubusercontent.com/globetvapp/epg/main/Brazil/brazil1.xml.gz");
    allSources.push("https://raw.githubusercontent.com/globetvapp/epg/main/Brazil/brazil2.xml.gz");
    allSources.push("https://raw.githubusercontent.com/globetvapp/epg/main/Brazil/brazil3.xml.gz");
    allSources.push("https://raw.githubusercontent.com/globetvapp/epg/main/Brazil/brazil4.xml.gz");
  } else {
    allSources.push(`https://epgshare01.online/epgshare01/epg_ripper_${country}1.xml.gz`);
    allSources.push(`https://raw.githubusercontent.com/globetvapp/epg/main/${country}/${country.toLowerCase()}1.xml.gz`);
  }
  try {
    var xmlParts = []; var seenChannels = {};
    for (var i = 0; i < allSources.length; i++) {
      try {
        var resp = await fetch(allSources[i], { method: "GET", headers: { "User-Agent": "LiveWatch" } });
        if (!resp.ok) continue;
        var compressed = new Uint8Array(await resp.arrayBuffer());
        var xml = new TextDecoder().decode(compressed); // try plain first
        if (compressed[0] === 0x1f && compressed[1] === 0x8b) {
          // gzip - use simple decompression
          var ds = new DecompressionStream("gzip");
          var writer = ds.writable.getWriter();
          writer.write(compressed);
          writer.close();
          var out = await new Response(ds.readable).arrayBuffer();
          xml = new TextDecoder().decode(new Uint8Array(out));
        }
        if (i === 0) {
          xmlParts.push(xml);
          var chMatch = xml.match(/<channel\s+id="([^"]+)"/g);
          if (chMatch) for (var j = 0; j < chMatch.length; j++) { var idm = chMatch[j].match(/id="([^"]+)"/); if (idm) seenChannels[idm[1]] = true; }
        } else {
          var chRegex = /<channel\s[^>]*>[\s\S]*?<\/channel>/g; var chMatch2;
          while ((chMatch2 = chRegex.exec(xml)) !== null) { var chXml = chMatch2[0]; var chId2 = (chXml.match(/id="([^"]+)"/) || [])[1]; if (chId2 && !seenChannels[chId2]) { seenChannels[chId2] = true; xmlParts.push(chXml); } }
          var progRegex = /<programme\s[^>]*>[\s\S]*?<\/programme>/g; var progMatch;
          while ((progMatch = progRegex.exec(xml)) !== null) xmlParts.push(progMatch[0]);
        }
      } catch (e) {}
    }
    if (xmlParts.length === 0) return new Response("No EPG data available", { status: 502, headers: { ...corsHeaders } });
    var combined = xmlParts[0];
    if (xmlParts.length > 1) combined = combined.replace("</tv>", xmlParts.slice(1).join("\n") + "\n</tv>");
    var headers = { ...corsHeaders, "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=14400" };
    if (url.searchParams.get("download") === "1") headers["Content-Disposition"] = "attachment; filename=\"epg_" + country + ".xml\"";
    return new Response(combined, { headers });
  } catch (e) { return new Response("EPG fetch error: " + e.message, { status: 500, headers: { ...corsHeaders } }); }
}

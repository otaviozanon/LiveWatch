import { unzipSync, strFromU8 } from "fflate";

export default {
  async fetch(request, env) {
    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    };

    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ ok: false, error: "Use POST" }), {
        status: 405,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const url = new URL(request.url);
    const githubHeaders = {
      Authorization: `Bearer ${env.GITHUB_PAT}`,
      Accept: "application/vnd.github+json",
      "User-Agent": "LiveWatch",
    };

    try {
      if (url.pathname === "/trigger") {
        return await handleTrigger(env, githubHeaders, corsHeaders);
      } else if (url.pathname === "/logs") {
        return await handleLogs(request, env, githubHeaders, corsHeaders);
      } else if (url.pathname === "/status") {
        return await handleStatus(request, env, githubHeaders, corsHeaders);
      }
      return new Response(JSON.stringify({ ok: false, error: "Unknown endpoint" }), {
        status: 404,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    } catch (e) {
      return new Response(JSON.stringify({ ok: false, error: e.message }), {
        status: 500,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }
  },
};

async function handleTrigger(request, env, headers, corsHeaders) {
  let body = {};
  try { body = await request.json(); } catch (e) {}
  const profile = body.profile || "brasil";

  const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_ID}/dispatches`;
  const resp = await fetch(url, {
    method: "POST",
    headers,
    body: JSON.stringify({ ref: "main", inputs: { profile: profile } }),
  });

  if (resp.ok) {
    return new Response(JSON.stringify({ ok: true }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
  const err = await resp.text();
  return new Response(JSON.stringify({ ok: false, error: err }), {
    status: 502,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

async function handleLogs(request, env, headers, corsHeaders) {
  const body = await request.json();
  const runId = body.runId;
  const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${runId}/logs`;

  const resp = await fetch(url, {
    method: "GET",
    headers,
    redirect: "follow",
  });

  if (!resp.ok) {
    return new Response(JSON.stringify({ ok: false, error: "Logs not available" }), {
      status: resp.status,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }

  try {
    const buf = new Uint8Array(await resp.arrayBuffer());
    const unzipped = unzipSync(buf);
    const texts = [];
    for (const [name, data] of Object.entries(unzipped)) {
      texts.push(strFromU8(data));
    }
    const combined = texts.join("\n");
    return new Response(combined, {
      headers: { ...corsHeaders, "Content-Type": "text/plain; charset=utf-8" },
    });
  } catch (e) {
    return new Response(await resp.text(), {
      headers: { ...corsHeaders, "Content-Type": "text/plain; charset=utf-8" },
    });
  }
}

async function handleStatus(request, env, headers, corsHeaders) {
  const body = await request.json();
  const runId = body.runId;
  const url = runId
    ? `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs/${runId}`
    : `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/runs?per_page=3`;

  const resp = await fetch(url, { method: "GET", headers });
  const data = await resp.text();
  return new Response(data, {
    status: resp.status,
    headers: { ...corsHeaders, "Content-Type": "application/json" },
  });
}

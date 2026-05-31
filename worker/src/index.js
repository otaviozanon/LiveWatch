export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
        },
      });
    }

    if (request.method !== "POST") {
      return new Response(JSON.stringify({ ok: false, error: "Use POST" }), {
        status: 405,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }

    try {
      const url = `https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}/actions/workflows/${env.WORKFLOW_ID}/dispatches`;
      const resp = await fetch(url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${env.GITHUB_PAT}`,
          Accept: "application/vnd.github+json",
          "User-Agent": "LiveWatch",
        },
        body: JSON.stringify({ ref: "main" }),
      });

      if (resp.ok) {
        return new Response(JSON.stringify({ ok: true }), {
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        });
      } else {
        const err = await resp.text();
        return new Response(JSON.stringify({ ok: false, error: err }), {
          status: 502,
          headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
        });
      }
    } catch (e) {
      return new Response(JSON.stringify({ ok: false, error: e.message }), {
        status: 500,
        headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" },
      });
    }
  },
};

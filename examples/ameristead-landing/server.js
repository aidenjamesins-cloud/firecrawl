// Local preview: serves public/ and /api/subscribe with no dependencies.  node server.js  ->  http://localhost:8080
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";
import { handleLead } from "./lib/lead.js";

const root = join(fileURLToPath(new URL(".", import.meta.url)), "public");
const types = { ".html": "text/html; charset=utf-8", ".css": "text/css", ".js": "text/javascript", ".png": "image/png", ".svg": "image/svg+xml", ".json": "application/json" };
const port = Number(process.env.PORT || 8080);

createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  if (url.pathname === "/api/subscribe") {
    if (req.method !== "POST") { res.writeHead(405).end(); return; }
    let raw = ""; for await (const c of req) { raw += c; if (raw.length > 20000) break; }
    let body = null; try { body = JSON.parse(raw); } catch {}
    const meta = { submittedAt: new Date().toISOString(), ip: req.socket.remoteAddress, userAgent: req.headers["user-agent"] || "" };
    const [status, json] = await handleLead(body, meta, process.env);
    res.writeHead(status, { "Content-Type": "application/json" }).end(JSON.stringify(json));
    return;
  }
  const path = normalize(url.pathname === "/" ? "/index.html" : url.pathname).replace(/^(\.\.[/\\])+/, "");
  try {
    const data = await readFile(join(root, path));
    res.writeHead(200, { "Content-Type": types[extname(path)] || "application/octet-stream" }).end(data);
  } catch { res.writeHead(404).end("Not found"); }
}).listen(port, () => console.log(`Preview on http://localhost:${port}`));

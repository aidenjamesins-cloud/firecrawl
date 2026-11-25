// Serverless endpoint (Vercel style: export default (req, res)). Netlify/others: wrap handleLead the same way.
import { handleLead } from "../lib/lead.js";

export default async function handler(req, res) {
  if (req.method !== "POST") { res.setHeader("Allow", "POST"); return res.status(405).json({ ok: false, error: "POST only." }); }
  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch { body = null; } }
  const meta = {
    submittedAt: new Date().toISOString(),
    ip: (req.headers["x-forwarded-for"] || "").split(",")[0].trim() || req.socket?.remoteAddress || "",
    userAgent: req.headers["user-agent"] || "",
  };
  const [status, json] = await handleLead(body, meta, process.env);
  res.status(status).json(json);
}

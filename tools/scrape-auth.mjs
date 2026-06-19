// Authenticated claude.ai conversation puller. Drives whatever Chromium/Electron
// is exposing CDP on :9222 (here: the Claude desktop app, which holds the live
// session). Fetches the AUTHENTICATED tree endpoint (rendering_mode=raw) which —
// unlike the public share snapshot — retains thinking blocks + full tool inputs.
import puppeteer from 'puppeteer-core';
import { writeFileSync } from 'node:fs';

const CONV = process.argv[2];
const OUT  = process.argv[3] || `output/auth-${CONV}.json`;
if (!CONV) { console.error('usage: scrape-auth.mjs <conversation_uuid> [out.json]'); process.exit(1); }

const browser = await puppeteer.connect({ browserURL: process.env.CDP || 'http://127.0.0.1:9444', defaultViewport: null });

// Prefer an existing claude.ai page (correct session partition); else open one.
const pages = await browser.pages();
let page = pages.find(p => { try { return new URL(p.url()).hostname.endsWith('claude.ai'); } catch { return false; } });
if (!page) {
  page = await browser.newPage();
  await page.goto('https://claude.ai/', { waitUntil: 'domcontentloaded', timeout: 60000 });
  await new Promise(r => setTimeout(r, 2000));
}
console.error('using page:', page.url());

const result = await page.evaluate(async (conv) => {
  const out = { tried: [] };
  const orgsRes = await fetch('/api/organizations', { credentials: 'include' });
  out.orgsStatus = orgsRes.status;
  let orgs = [];
  try { orgs = await orgsRes.json(); } catch (e) { out.orgsErr = String(e); }
  out.orgs = Array.isArray(orgs) ? orgs.map(o => ({ uuid: o.uuid, name: o.name })) : orgs;
  const candidates = Array.isArray(orgs) ? orgs.map(o => o.uuid) : [];
  for (const org of candidates) {
    const url = `/api/organizations/${org}/chat_conversations/${conv}?tree=True&rendering_mode=messages&render_all_tools=true`;
    const r = await fetch(url, { credentials: 'include' });
    out.tried.push({ org, status: r.status });
    if (r.ok) {
      out.org = org; out.convStatus = r.status;
      const txt = await r.text();
      try { out.conv = JSON.parse(txt); } catch (e) { out.convText = txt.slice(0, 800); out.convErr = String(e); }
      break;
    }
  }
  return out;
}, CONV);

writeFileSync(OUT, JSON.stringify(result, null, 2));

const conv = result.conv;
let thinking = 0, text = 0, tools = 0, toolInputs = 0;
if (conv && Array.isArray(conv.chat_messages)) {
  for (const m of conv.chat_messages) for (const c of (m.content || [])) {
    if (c.type === 'thinking') thinking++;
    else if (c.type === 'text') text++;
    else if (c.type === 'tool_use') { tools++; if (c.input && Object.keys(c.input).length) toolInputs++; }
  }
}
console.log('orgsStatus', result.orgsStatus, '| tried', JSON.stringify(result.tried), '| convStatus', result.convStatus);
console.log('messages', conv && conv.chat_messages ? conv.chat_messages.length : '-',
            '| text', text, '| THINKING', thinking, '| tool_use', tools, '(with inputs', toolInputs + ')');
console.log('out', OUT);
await browser.disconnect();

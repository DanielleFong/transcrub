// Bulk-pull every claude.ai conversation WITH thinking + full tool inputs via the
// authenticated endpoint. Resumable (skips already-pulled), polite 400ms delay.
// Reads output/_conversation-list.json (run list-convs.mjs first).
import puppeteer from 'puppeteer-core';
import { writeFileSync, existsSync, readFileSync, mkdirSync } from 'node:fs';

const LIMIT = process.argv[2] ? Number(process.argv[2]) : Infinity; // optional: cap to N most-recent
mkdirSync('output/full', { recursive: true });
const list = JSON.parse(readFileSync('output/_conversation-list.json', 'utf8'));
const org = list.org;
let items = list.items;
items.sort((a,b)=>(b.updated_at||'').localeCompare(a.updated_at||''));
const FROM=process.env.FROM, TO=process.env.TO;
if (FROM && TO) {
  items = items.filter(c=>{
    const cd=(c.created_at||'').slice(0,10), ud=(c.updated_at||'').slice(0,10);
    return (cd>=FROM&&cd<=TO)||(ud>=FROM&&ud<=TO);
  });
  console.log(`window ${FROM}..${TO}: ${items.length} conversations`);
} else if (Number.isFinite(LIMIT)) items = items.slice(0, LIMIT);

const b = await puppeteer.connect({ browserURL: 'http://127.0.0.1:9444', defaultViewport: null });
const pages = await b.pages();
let page = pages.find(p=>{try{return new URL(p.url()).hostname.endsWith('claude.ai')}catch{return false}}) || await b.newPage();
if(!/claude\.ai/.test(page.url())) await page.goto('https://claude.ai/new',{waitUntil:'domcontentloaded'});

let done=0, skip=0, fail=0, tk=0, tl=0;
for (const c of items) {
  const out = `output/full/${c.uuid}.json`;
  if (existsSync(out)) { skip++; continue; }
  try {
    const r = await page.evaluate(async (org,uuid)=>{
      const u=`/api/organizations/${org}/chat_conversations/${uuid}?tree=True&rendering_mode=messages&render_all_tools=true`;
      const res=await fetch(u,{credentials:'include'});
      return {status:res.status, json: res.ok? await res.json(): null};
    }, org, c.uuid);
    if (r.status!==200 || !r.json) { fail++; console.log(`  FAIL ${r.status} ${c.uuid}`); }
    else {
      writeFileSync(out, JSON.stringify(r.json));
      let th=0,to=0; for(const m of (r.json.chat_messages||[])) for(const blk of (m.content||[])){ if(blk.type==='thinking')th++; if(blk.type==='tool_use')to++; }
      tk+=th; tl+=to; done++;
      if (done%25===0) console.log(`  ${done} pulled (${skip} skip, ${fail} fail) | thinking so far ${tk}, tools ${tl}`);
    }
  } catch(e){ fail++; console.log(`  ERR ${c.uuid}: ${String(e).slice(0,80)}`); }
  await new Promise(r=>setTimeout(r,400));
}
console.log(`DONE: ${done} pulled, ${skip} skipped, ${fail} failed | total thinking ${tk}, tool_use ${tl}`);
await b.disconnect();

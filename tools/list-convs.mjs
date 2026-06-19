import puppeteer from 'puppeteer-core';
import { writeFileSync } from 'node:fs';
const b=await puppeteer.connect({browserURL:'http://127.0.0.1:9444',defaultViewport:null});
const pages=await b.pages();
let page=pages.find(p=>{try{return new URL(p.url()).hostname.endsWith('claude.ai')}catch{return false}})||await b.newPage();
if(!/claude\.ai/.test(page.url())) await page.goto('https://claude.ai/new',{waitUntil:'domcontentloaded'});
const out=await page.evaluate(async ()=>{
  const orgs=await (await fetch('/api/organizations',{credentials:'include'})).json();
  const org=orgs[0].uuid;
  let all=[],offset=0;
  for(let i=0;i<40;i++){
    const r=await fetch(`/api/organizations/${org}/chat_conversations?limit=100&offset=${offset}`,{credentials:'include'});
    if(!r.ok){all.push({_err:r.status});break;}
    const batch=await r.json();
    if(!batch.length)break;
    all=all.concat(batch); offset+=batch.length;
    if(batch.length<100)break;
  }
  return {org, total:all.length, items:all.map(c=>({uuid:c.uuid,name:c.name,updated_at:c.updated_at}))};
});
writeFileSync('output/_conversation-list.json',JSON.stringify(out,null,2));
console.log('org',out.org,'| total conversations:',out.total);
out.items.slice(0,15).forEach(c=>console.log('  ',(c.updated_at||'').slice(0,10),(c.name||'(untitled)').slice(0,64)));
console.log('  ...');
await b.disconnect();

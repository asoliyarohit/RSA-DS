const { chromium } = require('/opt/node-tools/node_modules/playwright');
(async()=>{const b=await chromium.launch();let fails=0;
for (const scheme of ['light','dark']){
 const c=await b.newContext({viewport:{width:375,height:800},colorScheme:scheme});const p=await c.newPage();let errs=[];
 p.on('pageerror',e=>errs.push(String(e)));p.on('console',m=>{if(m.type()==='error')errs.push('console:'+m.text())});
 await p.goto('file://'+process.cwd()+'/index.html');
 const ids=await p.$$eval('.chapter',a=>a.map(x=>x.id));
 for(const id of ids){errs=[];
  await p.evaluate(h=>{location.hash=h},id);await p.waitForTimeout(150);
  const r=await p.evaluate(async()=>{
   const ch=document.querySelector('.chapter.on');if(!ch)return{err:'no chapter on'};
   let clicks=0;
   for(const bt of ch.querySelectorAll('[data-next]')){for(let i=0;i<12&&!bt.disabled;i++){bt.click();clicks++}}
   for(const q of ch.querySelectorAll('.quiz .q')){const bs=q.querySelectorAll('button');if(bs.length){bs[0].click();clicks++}}
   for(const d of ch.querySelectorAll('.drill')){const g=d.querySelector('.go'),s=d.querySelector('.sh'),n=d.querySelector('.nx');if(g){g.click();s&&s.click();n&&n.click()}}
   const ov=document.documentElement.scrollWidth-innerWidth;
   const wide=[...ch.querySelectorAll('*')].filter(e=>{const r=e.getBoundingClientRect();return r.right>innerWidth+1&&!e.closest('.tw')&&!e.closest('svg')&&getComputedStyle(e).position!=='fixed'}).length;
   return{ov,wide,clicks,quizzes:ch.querySelectorAll('.quiz').length,txt:/undefined|NaN/.test(ch.innerText)}});
  const bad=errs.length||r.err||r.ov>0||r.txt;
  if(bad){fails++;console.log(scheme,id,JSON.stringify(r),errs.slice(0,3))}
 }
 console.log(scheme,'chapters tested',ids.length);await c.close()}
console.log('FAILS',fails);await b.close()})();

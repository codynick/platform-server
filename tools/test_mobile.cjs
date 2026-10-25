const fs=require('fs'),path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..');
const local=!process.env.BASE_URL,base=process.env.BASE_URL||'http://ide.local';
const sourceDir=path.join(root,'upstream/components/ide/code');
const output=path.join(root,'test-output');fs.mkdirSync(output,{recursive:true});
function fixture(){
  let source=fs.readFileSync(path.join(sourceDir,'index.php'),'utf8');
  const start=source.search(/<!doctype html>/i);
  if(start<0)throw Error('Missing IDE HTML');
  source=source.slice(start);
  source=source.replace(/<\?=\s*json_encode\(basename\(ACTIVE_SCRIPT_FILE\)\)\s*\?>/g,'"active_script.py"')
    .replace(/<\?=\s*\(int\)[\s\S]*?\?>/g,'1000')
    .replace(/<\?=\s*htmlspecialchars\(IDE_TITLE\)\s*\?>/g,'CodyNick IDE')
    .replace(/<\?=\s*htmlspecialchars\(IDE_LOGO_URL\)\s*\?>/g,'/assets/logo.png')
    .replace(/<\?=\s*htmlspecialchars\(defined\('LOG_FILE'\)[\s\S]*?\?>/g,'/workspace/log.log')
    .replace(/<\?php[\s\S]*?\?>/g,'');
  if(source.includes('<?'))throw Error('Unrendered PHP fixture expression');
  return source;
}
(async()=>{
  const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
  try{
    const page=await browser.newPage();let runs=0,stops=0;
    page.on('pageerror',error=>console.error('Browser script:',error.message));
    await page.route('https://cdnjs.cloudflare.com/**',route=>route.abort());
    if(local)await page.route(base+'/**',route=>{
      const url=new URL(route.request().url());
      if(url.searchParams.has('action')){
        const action=url.searchParams.get('action');
        if(action==='run')runs++;if(action==='stop')stops++;
        const body={ok:true,tree:[],content:action==='read'?'import time\nprint("MOBILE_UI_OK",flush=True)\ntime.sleep(30)\n':'',modified:1,offset:0,fileId:'test',reset:false};
        return route.fulfill({contentType:'application/json',body:JSON.stringify(body)});
      }
      if(url.pathname==='/code/'||url.pathname==='/code/index.php')return route.fulfill({contentType:'text/html',body:fixture()});
      const filename=url.pathname.startsWith('/code/')?path.join(sourceDir,path.basename(url.pathname)):path.join(root,'upstream/components/ide',url.pathname.slice(1));
      if(fs.existsSync(filename)&&fs.statSync(filename).isFile())return route.fulfill({path:filename});
      return route.fulfill({status:404,body:'Not found'});
    });
    if(!local){
      await page.goto(base+'/login');
      await page.fill('#username','alice');await page.fill('#password','OnlyForEphemeralCI123');
      await Promise.all([page.waitForURL(base+'/'),page.click('button[type=submit]')]);
    }
    await page.setViewportSize({width:1280,height:800});await page.goto(base+'/code/');
    await page.waitForFunction(()=>typeof openFile==='function'&&document.querySelector('.mobile-run-label'));
    await page.evaluate(async()=>{try{await api('create',{path:'mobile_test.py',type:'file'});}catch(e){if(!e.message.includes('already exists'))throw e;}await api('save',{path:'mobile_test.py',content:'import time\nprint("MOBILE_UI_OK",flush=True)\ntime.sleep(30)\n'});await openFile('mobile_test.py','mobile_test.py');});
    const desktop=await page.evaluate(()=>{
      const selectors=['.app','.sidebar','.main','.toolbar','#runBtn','#stopBtn','.editor-wrap'];
      const boxes=()=>selectors.map(s=>{const r=document.querySelector(s).getBoundingClientRect();return[r.x,r.y,r.width,r.height]});
      const before=boxes(),link=document.querySelector('link[href^="mobile.css"]');
      link.disabled=true;document.querySelector('#mobileFilesToggle').style.display='none';document.querySelector('.mobile-run-label').style.display='none';
      const baseline=boxes();link.disabled=false;document.querySelector('#mobileFilesToggle').style.display='';document.querySelector('.mobile-run-label').style.display='';
      return {before,baseline,grid:getComputedStyle(document.querySelector('.app')).gridTemplateColumns};
    });
    if(JSON.stringify(desktop.before)!==JSON.stringify(desktop.baseline)||!desktop.grid.startsWith('330px'))throw Error('Desktop layout changed');
    await page.screenshot({path:path.join(output,'ide-desktop.png')});
    for(const [name,width,height]of[['small',320,640],['phone',390,844],['landscape',740,360]]){
      await page.setViewportSize({width,height});
      await page.click('#mobileFilesToggle');
      if(await page.getAttribute('#mobileFilesToggle','aria-expanded')!=='true')throw Error('Files drawer did not open');
      await page.evaluate(()=>openFile('mobile_test.py','mobile_test.py'));
      await page.waitForFunction(()=>document.querySelector('#mobileFilesToggle').getAttribute('aria-expanded')==='false');
      const check=await page.evaluate(()=>({overflow:document.documentElement.scrollWidth>innerWidth,inert:document.querySelector('.main').inert,buttons:['runBtn','stopBtn'].map(id=>{const r=document.getElementById(id).getBoundingClientRect();return r.x>=0&&r.right<=innerWidth&&r.y>=0&&r.bottom<=innerHeight&&r.height>=40;})}));
      if(check.overflow||check.inert||check.buttons.some(v=>!v))throw Error('Mobile controls clipped: '+JSON.stringify(check));
      await page.screenshot({path:path.join(output,'ide-'+name+'.png')});
    }
    await page.click('#runBtn');
    if(!local)await page.waitForFunction(()=>document.querySelector('#terminalBody').textContent.includes('MOBILE_UI_OK'));
    await page.click('#stopBtn');await page.waitForFunction(()=>document.querySelector('#status').textContent.startsWith('Stopped.'));
    if(local&&(runs!==1||stops!==1))throw Error('Run/Stop handlers not reached');
    await page.click('#mobileFilesToggle');await page.keyboard.press('Escape');
    if(await page.getAttribute('#mobileFilesToggle','aria-expanded')!=='false')throw Error('Escape did not close Files');
    await page.click('#mobileFilesToggle');await page.setViewportSize({width:1280,height:800});
    await page.waitForFunction(()=>!document.querySelector('.main').inert&&!document.body.classList.contains('mobile-files-open'));
    console.log('Desktop geometry unchanged; phone/landscape Files, Run and Stop passed'+(local?' (mock APIs)':' (real server)'));
  }finally{await Promise.race([browser.close(),new Promise(r=>setTimeout(r,5000))]);}
})().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)});

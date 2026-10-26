const fs=require('fs'),path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),ide=path.join(root,'upstream/components/ide');
const base=process.env.BASE_URL||'http://blocks.local',local=!process.env.BASE_URL;
let html=fs.readFileSync(path.join(ide,'blocks/index.php'),'utf8');html=html.slice(html.search(/<!doctype html>/i));
const packages=fs.readdirSync(path.join(ide,'blocks/blocks')).filter(n=>n.endsWith('.json')).map(n=>JSON.parse(fs.readFileSync(path.join(ide,'blocks/blocks',n),'utf8')));
const designs=fs.readdirSync(path.join(root,'upstream/components/examples/blockly')).filter(name=>/^0[1-4]_.*\.codynick$/.test(name)).map(file=>{const workspace=JSON.parse(fs.readFileSync(path.join(root,'upstream/components/examples/blockly',file),'utf8'));const name='Demo '+Number(file.slice(0,2))+' - '+workspace.codynick_design.name;workspace.codynick_design.name=name;return {name,workspace};});
html=html.replace(/<\?= json_encode\(\$BLOCK_PACKAGES,[\s\S]*?\?>/,JSON.stringify(packages)).replace(/<\?= json_encode\(\$BLOCK_WARNINGS,[\s\S]*?\?>/,'[]').replace(/<\?=[\s\S]*?\?>/g,'CodyNick');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('dialog',dialog=>dialog.accept());
  if(local)await page.route(base+'/**',route=>{
   const url=new URL(route.request().url());
   if(url.pathname.endsWith('designs.php')){const action=url.searchParams.get('action');return route.fulfill({json:action==='list'?{ok:true,designs:designs.map(({name})=>({name}))}:{ok:true,...designs.find(d=>d.name===url.searchParams.get('name'))}});}
   if(url.searchParams.has('api'))return route.fulfill({json:{ok:true,workspace:{blocks:{languageVersion:0,blocks:[]}}}});
   if(url.pathname.endsWith('stage.php'))return route.fulfill({json:{ok:true,state:{x:0,y:0,direction:90,size:100,visible:true,speech:'',backdrop:'white',keys:[]}}});
   if(url.pathname==='/blocks/')return route.fulfill({contentType:'text/html',body:html});
   const file=path.join(ide,url.pathname.slice(1));return fs.existsSync(file)&&fs.statSync(file).isFile()?route.fulfill({path:file}):route.fulfill({status:404,body:''});
  });
  if(!local){await page.goto(base+'/login');await page.fill('#username','alice');await page.fill('#password','OnlyForEphemeralCI123');await Promise.all([page.waitForURL(base+'/'),page.click('button[type=submit]')]);}
  await page.setViewportSize({width:1440,height:960});await page.goto(base+'/blocks/');await page.waitForFunction(()=>document.querySelector('#workspaceStatus').textContent==='Loaded');
  for(const file of ['01_temperature_monitor','02_temperature_traffic_light','03_parking_assistant','04_joystick_status']){
   await page.getByRole('button',{name:'Load',exact:true}).click();
   const named=designs.find(d=>d.name.startsWith('Demo '+Number(file.slice(0,2))+' - '));
   await page.selectOption('#designList',named.name);await page.click('#designLoadConfirm');
   await page.waitForFunction(name=>document.querySelector('#designName').value===name,named.name);
   const result=await page.evaluate(()=>{workspace.zoomToFit();return {code:generatePython(),mode:document.querySelector('#executionTarget').value,saved:currentWorkspaceJson()};});
   if(result.mode!=='simulator'||!result.code.includes('Simulator(required_gadgets='))throw Error('Not simulator mode: '+file);
   if(result.code.includes('Unsupported')||result.code.includes('cody = CN()'))throw Error('Invalid generated code: '+file);
   fs.writeFileSync(path.join(root,'test-output',file+'.py'),result.code);
   await page.screenshot({path:path.join(root,'test-output',file+'.png')});
  }
  if(errors.length)throw Error(errors.join('\n'));
  console.log('All four pre-installed designs open via Load, select Simulator, serialize and generate Python'+(local?' (mock API)':' (real saved-design API)'));
 }finally{await Promise.race([browser.close(),new Promise(r=>setTimeout(r,5000))]);}
})().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)});

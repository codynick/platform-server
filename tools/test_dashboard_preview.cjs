const fs=require('fs'),path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const root=path.resolve(__dirname,'..'),ide=path.join(root,'upstream/components/ide');
const base=process.env.BASE_URL||'http://blocks.local',local=!process.env.BASE_URL;
let html=fs.readFileSync(path.join(ide,'blocks/index.php'),'utf8');
html=html.slice(html.search(/<!doctype html>/i));
const packages=fs.readdirSync(path.join(ide,'blocks/blocks')).filter(n=>n.endsWith('.json')).map(n=>JSON.parse(fs.readFileSync(path.join(ide,'blocks/blocks',n),'utf8')));
html=html.replace(/<\?= json_encode\(\$BLOCK_PACKAGES,[\s\S]*?\?>/,JSON.stringify(packages)).replace(/<\?= json_encode\(\$BLOCK_WARNINGS,[\s\S]*?\?>/,'[]').replace(/<\?=[\s\S]*?\?>/g,'CodyNick');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  if(local)await page.route(base+'/**',route=>{
   const url=new URL(route.request().url());
   if(url.searchParams.has('api'))return route.fulfill({json:{ok:true,workspace:{blocks:{languageVersion:0,blocks:[]}}}});
   if(url.pathname.endsWith('stage.php'))return route.fulfill({json:{ok:true,state:{x:0,y:0,direction:90,size:100,visible:true,speech:'',backdrop:'white',keys:[]}}});
   if(url.pathname==='/blocks/')return route.fulfill({contentType:'text/html',body:html});
   const file=path.join(ide,url.pathname.slice(1));
   return fs.existsSync(file)&&fs.statSync(file).isFile()?route.fulfill({path:file}):route.fulfill({status:404,body:''});
  });
  if(!local){await page.goto(base+'/login');await page.fill('#username','alice');await page.fill('#password','OnlyForEphemeralCI123');await Promise.all([page.waitForURL(base+'/'),page.click('button[type=submit]')]);}
  await page.setViewportSize({width:1440,height:960});await page.goto(base+'/blocks/');
  await page.waitForFunction(()=>document.querySelector('#workspaceStatus').textContent==='Loaded');
  const design=JSON.parse(fs.readFileSync(path.join(root,'upstream/components/examples/blockly/dashboard_counter.codynick'),'utf8'));
  const code=await page.evaluate(design=>{Blockly.serialization.workspaces.load(design,workspace);selectToolboxMode('dashboard');workspace.zoomToFit();return generatePython();},design);
  if(!code.includes('import Dashboard')||code.includes('cody = CN()')||code.includes('cody = Simulator('))throw Error('Dashboard-only program opened hardware');
  await page.selectOption('#executionTarget','simulator');
  await page.evaluate(()=>ExecutionTarget.preflight(workspace,dynamicBlockSpecs));
  if(await page.getAttribute('a[href="/dashboard/"]','target')!=='_blank')throw Error('Dashboard link missing');
  const snapshot=await page.evaluate(()=>currentWorkspaceJson());
  await page.evaluate(data=>Blockly.serialization.workspaces.load(data,workspace),snapshot);
  if(!(await page.evaluate(()=>generatePython())).includes('_dashboard_append("history"'))throw Error('Dashboard design did not round-trip');
  for(const name of ['Setup','Info','Gauge','Graph']) if(!await page.getByRole('treeitem',{name,exact:true}).count()) throw Error('Missing Dashboard folder: '+name);
  await page.getByRole('treeitem',{name:'Info',exact:true}).click();
  await page.evaluate(()=>{
   const legacy=workspace.newBlock('dash_create');legacy.setFieldValue('gauge','TYPE');legacy.setFieldValue('legacy','NAME');
   if(!DashboardBlocks.statement(legacy,()=> '0').includes('"gauge"'))throw Error('Legacy creation block broken');legacy.dispose();
   selectToolboxMode('hardware');
   if(buildToolbox().contents.some(c=>c.name==='Dashboard'))throw Error('Dashboard remains in Hardware');
   selectToolboxMode('dashboard');
  });
  await page.getByRole('treeitem',{name:'Info',exact:true}).click();
  await page.screenshot({path:path.join(root,'test-output/dashboard-blocks.png')});
  fs.writeFileSync(path.join(root,'test-output/dashboard-generated.py'),code);
  if(!local){
    await page.evaluate(()=>runProgram());
    let cards=[];
    for(let attempt=0;attempt<80;attempt++){
      cards=await page.evaluate(async()=>(await(await fetch('/dashboard/cards.php?action=state')).json()).cards);
      const graph=cards.find(c=>c.title==='History');
      if(graph&&JSON.parse(graph.value).length>=2)break;
      await new Promise(resolve=>setTimeout(resolve,250));
    }
    const graph=cards.find(c=>c.title==='History');
    if(!graph||JSON.parse(graph.value).length<2)throw Error('Dashboard graph did not receive samples: '+JSON.stringify(cards));
    const info=cards.find(c=>c.title==='Elapsed seconds');
    if(!info||Number(info.font_size)!==32||info.horizontal_alignment!=='center'||info.vertical_alignment!=='center')throw Error('Dashboard defaults did not reach database: '+JSON.stringify(cards));
    await page.evaluate(()=>postJson('?api=stop',{}));
    const after=await page.evaluate(async()=>(await(await fetch('/dashboard/cards.php?action=state')).json()).cards);
    if(after.length!==2)throw Error('Stop removed dashboard widgets');
    const other=await browser.newPage();await other.goto(base+'/login');await other.fill('#username','bob');await other.fill('#password','OnlyForEphemeralCI123');await Promise.all([other.waitForURL(base+'/'),other.click('button[type=submit]')]);
    const bob=await other.evaluate(async()=>(await(await fetch('/dashboard/cards.php?action=state')).json()).cards);
    if(bob.some(c=>c.title==='Elapsed seconds'||c.title==='History'))throw Error('Dashboard crossed account boundaries');await other.close();
  }
  if(errors.length)throw Error(errors.join('\n'));
  console.log('Dashboard folders, compatibility, defaults and generated Python passed'+(local?' (mock APIs)':' with real Run/Stop, MySQL and per-account isolation'));
 }finally{await Promise.race([browser.close(),new Promise(r=>setTimeout(r,5000))]);}
})().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)});

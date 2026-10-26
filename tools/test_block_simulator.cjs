const fs=require('fs'),path=require('path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const base=process.env.BASE_URL||'http://127.0.0.1';
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  page.on('pageerror',error=>console.error('Blockly browser:',error.message));
  await page.goto(base+'/login');await page.fill('#username','alice');await page.fill('#password','OnlyForEphemeralCI123');
  await Promise.all([page.waitForURL(base+'/'),page.click('button[type=submit]')]);
  await page.goto(base+'/blocks/');await page.waitForFunction(()=>typeof ExecutionTarget!=='undefined'&&typeof workspace!=='undefined'&&['Loaded','Saved','New workspace'].includes(document.querySelector('#workspaceStatus').textContent));
  await page.evaluate(()=>{
   Blockly.serialization.workspaces.load({blocks:{languageVersion:0,blocks:[]}},workspace);
   const xml=Blockly.utils.xml.textToDom(`<xml xmlns="https://developers.google.com/blockly/xml"><block type="cn_event_start"><statement name="DO"><block type="cn_rgb_matrix_set"><field name="led">0</field><field name="color">#00FF00</field><next><block type="cn_led_matrix_display_text"><field name="text">HELLO</field><field name="speed">'medium'</field></block></next></block></statement></block></xml>`);
   Blockly.Xml.domToWorkspace(xml,workspace);
  });
  if(!(await page.evaluate(()=>generatePython())).includes('cody = CN()'))throw Error('Legacy designs must default to Hardware');
  await page.selectOption('#executionTarget','simulator');
  let code=await page.evaluate(()=>generatePython());
  if(!code.includes('Simulator(required_gadgets=')||code.includes('cody = CN()'))throw Error('Simulator code opened hardware');
  if(await page.getAttribute('a[href="/simulator/"]','target')!=='_blank')throw Error('Simulator link missing');
  await page.evaluate(()=>saveWorkspaceNow(true));
  await page.reload();await page.waitForFunction(()=>document.querySelector('#executionTarget')?.value==='simulator');
  // Named designs and downloaded/uploaded workspace data use the same serializer.
  await page.evaluate(()=>{const snapshot=currentWorkspaceJson();if(snapshot.codynick_execution.target!=='simulator')throw Error('Mode not serialized');Blockly.serialization.workspaces.load({blocks:{languageVersion:0,blocks:[]}},workspace);if(document.querySelector('#executionTarget').value!=='hardware')throw Error('Legacy mode not Hardware');Blockly.serialization.workspaces.load(snapshot,workspace);});
  await page.evaluate(async()=>{
   await fetch('/code/?action=stop',{method:'POST',body:new URLSearchParams()});
   const state=await (await fetch('/simulation/state')).json();
   const scene={...state.scene,gadgets:{cjp:{x:40,y:40}}};
   await fetch('/simulation/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'scene',scene})});
   await runProgram();
  });
  await page.waitForFunction(()=>document.body.textContent.includes('then re-run the app'));
  const missing=await page.evaluate(async()=>(await (await fetch('/simulation/state')).json()));
  if(missing.connected||!missing.error.includes('Add LED matrix'))throw Error('Missing gadget locked the simulation space');
  await page.evaluate(async()=>{const state=await(await fetch('/simulation/state')).json();state.scene.gadgets.matrix={x:400,y:40};const r=await fetch('/simulation/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'scene',scene:state.scene})});if(!r.ok)throw Error('Cannot add missing gadget');await runProgram();});
  await page.waitForFunction(async()=>{const s=await(await fetch('/simulation/state')).json();return s.connected&&s.leds[0]==='#00FF00'&&s.matrix.text==='HELLO';});
  await page.evaluate(()=>stopProgram());
  await page.waitForFunction(async()=>!(await(await fetch('/simulation/state')).json()).connected);
  await page.evaluate(()=>runProgram());
  await page.waitForFunction(async()=>(await(await fetch('/simulation/state')).json()).connected);
  await page.evaluate(()=>stopProgram());
  await page.evaluate(()=>{const b=workspace.newBlock('cn_rfid_readuid');b.initSvg();b.render();const result=ExecutionTarget.initialization([b]);if(!result.includes('not supported'))throw Error('Unsupported gadget was not rejected');b.dispose();});
  fs.mkdirSync('test-output',{recursive:true});await page.screenshot({path:'test-output/block-simulator.png',fullPage:true});
  console.log('Blockly simulator generation, saved mode, missing gadget recovery, LED/matrix output and immediate Stop/Run passed');
 }finally{await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);}
})().then(()=>process.exit(0)).catch(e=>{console.error(e);process.exit(1)});

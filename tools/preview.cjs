const fs = require('fs');
const path = require('path');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const root = path.resolve(__dirname, '..');
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage();
    const html = '<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+fs.readFileSync(path.join(root,'multi.css'),'utf8')+'</style></head><body><header><strong>CodyNick</strong><span>student1</span><small>Multi-user 0.1.0</small></header><main><h1>Your Tools</h1><nav>'+['Python IDE','Block Coding','Gadget Simulator','Dashboard','Guide'].map(s=>'<a href="#">'+s+'</a>').join('')+'</nav></main></body></html>';
    for (const [name,width,height] of [['desktop',1280,800],['mobile',390,844]]) {
      await page.setViewportSize({width,height});
      await page.setContent(html);
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error('Horizontal overflow');
      await page.screenshot({path:path.join(root,'test-output',name+'.png'),fullPage:true});
    }
    console.log('Desktop/mobile menu layout passed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

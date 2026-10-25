const fs = require('fs');
const path = require('path');
const {execFileSync} = require('child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const root = path.resolve(__dirname, '..');
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage();
    const pages = {menu: execFileSync('python',['-c','import install; print(install.page("student1"))'],{cwd:root,encoding:'utf8'}),login: execFileSync('python',['-c','import gateway; print(gateway.login_page())'],{cwd:root,encoding:'utf8'})};
    for (const [kind,content] of Object.entries(pages)) {
    const html = content.replace('<link rel="stylesheet" href="/assets/multi.css">','<style>'+fs.readFileSync(path.join(root,'multi.css'),'utf8')+'</style>');
    for (const [name,width,height] of [['desktop',1280,800],['mobile',390,844]]) {
      await page.setViewportSize({width,height});
      await page.setContent(html);
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error('Horizontal overflow');
      await page.screenshot({path:path.join(root,'test-output',kind+'-'+name+'.png'),fullPage:true});
    }
    }
    console.log('Desktop/mobile menu layout passed');
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});

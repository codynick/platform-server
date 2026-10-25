const fs = require('fs');
const path = require('path');
const {execFileSync} = require('child_process');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const root = path.resolve(__dirname, '..');
  const browser = await chromium.launch({channel:'msedge',headless:true});
  try {
    const page = await browser.newPage();
    const pages = {menu: execFileSync('python',['-c','import install; print(install.page("teacher","admin"))'],{cwd:root,encoding:'utf8'}),login: execFileSync('python',['-c','import gateway; print(gateway.login_page())'],{cwd:root,encoding:'utf8'}),users:execFileSync('python',['-c','import views; print(views.users_page("teacher",{"teacher":{"slot":0,"role":"admin"},"student1":{"slot":1,"role":"student"}},"test"))'],{cwd:root,encoding:'utf8'})};
    pages.password=execFileSync('python',['-c','import views; print(views.password_page("student1","student1","test"))'],{cwd:root,encoding:'utf8'});
    pages.reset=execFileSync('python',['-c','import views; print(views.password_page("teacher","student1","test",reset=True))'],{cwd:root,encoding:'utf8'});
    let current = '';
    await page.route('http://preview.local/**',route=> {
      const url=new URL(route.request().url());
      if(url.pathname==='/assets/logo.png')return route.fulfill({contentType:'image/png',body:fs.readFileSync(path.join(root,'upstream/components/ide/assets/logo.png'))});
      if(url.pathname==='/favicon.ico')return route.fulfill({contentType:'image/x-icon',body:fs.readFileSync(path.join(root,'upstream/components/ide/assets/favicon.ico'))});
      return route.fulfill({contentType:'text/html',body:current});
    });
    for (const [kind,content] of Object.entries(pages)) {
    const html = content.replace('<link rel="stylesheet" href="/assets/multi.css">','<style>'+fs.readFileSync(path.join(root,'multi.css'),'utf8')+'</style>');
    for (const [name,width,height] of [['desktop',1280,800],['mobile',390,844]]) {
      await page.setViewportSize({width,height});
      current = html;
      await page.goto('http://preview.local/');
      await page.waitForFunction(()=>Array.from(document.images).every(image=>image.complete&&image.naturalWidth>0));
      if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth)) throw Error('Horizontal overflow');
      await page.screenshot({path:path.join(root,'test-output',kind+'-'+name+'.png'),fullPage:true});
    }
    }
    console.log('Desktop/mobile panel, login, Users and logo rendering passed');
  } finally {await Promise.race([browser.close(),new Promise(resolve=>setTimeout(resolve,5000))]);}
})().then(()=>process.exit(0)).catch(error=>{console.error(error);process.exit(1);});

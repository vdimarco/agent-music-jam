/* Optional real Chromium checks. Install Playwright in a scratch directory; no app build needed. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'), artifacts=path.join(root,'work','browser-check');
fs.mkdirSync(artifacts,{recursive:true});
(async()=>{
  const service=spawn(process.env.PYTHON||'python',[path.join(root,'run.py')],{stdio:['ignore','pipe','inherit']});
  let browser;
  try{
    const url=await new Promise((resolve,reject)=>{let out='';service.stdout.on('data',b=>{out+=b;if(out.includes('\n'))resolve(out.trim());});service.on('error',reject);service.on('exit',code=>reject(Error('Service exited: '+code)));});
    browser=await chromium.launch({executablePath:process.env.CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
    const page=await browser.newPage({viewport:{width:1440,height:1280}}),errors=[];
    page.on('pageerror',e=>errors.push(e.message));
    await page.goto(url);await page.getByText('Ready. Press Play').waitFor();
    await page.locator('#play').click();await page.waitForTimeout(4000);
    assert.equal((await page.evaluate(()=>window.jamDiagnostics())).playing,true);
    assert.equal(await page.locator('.beat-lights .lit').count(),1);
    assert.equal(await page.locator('#keys-instrument').isVisible(),true);
    await page.getByRole('button',{name:'Less busy drums',exact:true}).click();await page.waitForTimeout(9000);
    assert.match(await page.locator('#changes').innerText(),/Drums bar 5/);
    await page.locator('[data-role=keys] summary').click();
    await page.locator('#keys-instrument').selectOption('organ');
    await page.locator('#human-instrument').selectOption('pluck');
    await page.locator('#human-tone').focus();await page.keyboard.press('End');
    await page.getByRole('button',{name:'Play D4',exact:true}).scrollIntoViewIfNeeded();
    const box=await page.getByRole('button',{name:'Play D4',exact:true}).boundingBox();
    await page.mouse.move(box.x+box.width/2,box.y+box.height-20);await page.mouse.down();await page.waitForTimeout(300);await page.mouse.up();
    assert.match(await page.locator('#phrase-status').innerText(),/1 notes/);
    for(const kind of ['mute','solo']){
      const button=page.locator(`[data-role=bass] .${kind}`);
      await button.click();assert.equal(await button.getAttribute('aria-pressed'),'true');await page.waitForTimeout(150);await button.click();
    }
    await page.locator('#undo-role').selectOption('drums');await page.locator('#undo').click();await page.waitForTimeout(8000);
    const metrics=await page.evaluate(()=>window.jamDiagnostics());assert.equal(metrics.metrics.late,0);
    await page.locator('#stop').click();await page.waitForTimeout(250);
    assert.equal((await page.evaluate(()=>window.jamDiagnostics())).voices,0);
    assert.equal(await page.locator('.beat-lights .lit').count(),0);
    assert.equal(await page.locator('#timing').innerText(),'Audio clock ready');
    await page.locator('#export').click();
    for(const [format,filename] of [['wav','take.wav'],['midi','take.mid']]){
      const pending=page.waitForEvent('download');await page.locator('#'+format+'-export').click();await (await pending).saveAs(path.join(artifacts,filename));
    }
    assert.equal(fs.readFileSync(path.join(artifacts,'take.wav')).subarray(0,4).toString(),'RIFF');
    assert.equal(fs.readFileSync(path.join(artifacts,'take.mid')).subarray(0,4).toString(),'MThd');
    await page.locator('.close').click();
    const save=page.waitForEvent('download');await page.locator('#save').click();await (await save).saveAs(path.join(artifacts,'session.json'));
    await page.locator('#restore-file').setInputFiles(path.join(artifacts,'session.json'));await page.waitForTimeout(900);
    assert.equal(await page.locator('#human-instrument').inputValue(),'pluck');assert.equal(await page.locator('#human-tone').inputValue(),'1');
    assert.equal(await page.locator('#keys-instrument').inputValue(),'organ');
    await page.locator('[data-role=keys] summary').click();await page.screenshot({path:path.join(artifacts,'desktop.png'),fullPage:true});
    await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(artifacts,'mobile.png'),fullPage:true});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(artifacts,'results.json'),JSON.stringify({metrics,errors,restore:true,midi:true,wav:true,mobileOverflow:false},null,2));
    console.log(JSON.stringify({passed:true,metrics:metrics.metrics,artifacts}));
  }finally{await browser?.close();service.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});

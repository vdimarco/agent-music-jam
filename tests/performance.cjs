/* Real browser coverage for performance layout, persistent takes and overwrite guards. */
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),artifacts=path.join(root,'work','performance-check');fs.mkdirSync(artifacts,{recursive:true});
(async()=>{
 const service=spawn(process.env.PYTHON||'python',[path.join(root,'run.py')],{stdio:['ignore','pipe','inherit']});let browser;
 try{
  const url=await new Promise((resolve,reject)=>{let output='';service.stdout.on('data',b=>{output+=b;if(output.includes('\n'))resolve(output.trim());});service.on('error',reject);});
  browser=await chromium.launch({executablePath:process.env.CHROMIUM||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--autoplay-policy=no-user-gesture-required']});
  const page=await browser.newPage({viewport:{width:1440,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(url);await page.getByText('Ready. Press Play').waitFor();
  await page.locator('#performance-mode').click();assert.equal(await page.locator('#performance-mode').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('#musicians').isVisible(),false);
  await page.locator('#show-band').click();assert.equal(await page.locator('#keys-instrument').isVisible(),true);await page.locator('#show-band').click();
  const keyboard=await page.locator('#keyboard').boundingBox();assert.ok(keyboard.y+keyboard.height<=900,'Keyboard fits desktop performance view');
  await page.locator('#play').click();await page.waitForTimeout(2200);
  assert.notEqual(await page.locator('#take-timer').innerText(),'00:00');assert.match(await page.locator('#take-state').innerText(),/Recording/);
  assert.equal(await page.locator('.chord[aria-current=true]').count(),1);assert.match(await page.locator('.chord.current strong').innerText(),/Dm9/);
  await page.locator('[data-prompt="Make the drums less busy"]').click();await page.waitForFunction(()=>document.querySelector('#arrangement').textContent.includes('confirmed'),{},{timeout:12000});
  assert.match(await page.locator('#arrangement').innerText(),/Drums · bar \d+ confirmed/);
  await page.locator('#stop').click();await page.waitForFunction(()=>document.querySelector('#timing').textContent==='Audio clock ready');const samples=(await page.evaluate(()=>window.jamDiagnostics())).samples;
  await page.locator('#play').click();await page.locator('#protect-take').waitFor();await page.locator('#protect-cancel').click();
  assert.equal((await page.evaluate(()=>window.jamDiagnostics())).playing,false);assert.equal((await page.evaluate(()=>window.jamDiagnostics())).samples,samples);
  await page.locator('#play').click();await page.locator('#protect-save').click();await page.waitForFunction(()=>window.jamDiagnostics().playing);
  await page.waitForTimeout(1300);await page.locator('#stop').click();
  await page.locator('#open-takes').click();await page.locator('#take-list li').waitFor();assert.equal(await page.locator('#take-list li').count(),1);
  for(const [format,magic] of [['WAV','RIFF'],['MIDI','MThd']]){const pending=page.waitForEvent('download');await page.locator('#take-list').getByRole('button',{name:`Download ${format}`,exact:true}).click();const dest=path.join(artifacts,format.toLowerCase());await (await pending).saveAs(dest);assert.equal(fs.readFileSync(dest).subarray(0,4).toString(),magic);}
  await page.getByRole('button',{name:'Close saved takes',exact:true}).click();
  // A new session must also protect the current recording.
  await page.locator('#new').click();await page.locator('#protect-take').waitFor();await page.locator('#protect-cancel').click();assert.equal((await page.evaluate(()=>window.jamDiagnostics())).samples>0,true);
  // Fill the real store to its declared capacity and ensure failure preserves audio.
  await page.evaluate(()=>new Promise((resolve,reject)=>{const request=indexedDB.open('agent-music-jam-takes',1);request.onsuccess=()=>{const db=request.result,tx=db.transaction('takes','readwrite'),store=tx.objectStore('takes'),all=store.getAll();all.onsuccess=()=>{for(let i=1;i<10;i++)store.add({...all.result[0],id:'capacity-test-'+i});};tx.oncomplete=()=>{db.close();resolve();};tx.onerror=()=>reject(tx.error);};}));
  await page.locator('#play').click();await page.locator('#protect-save').click();await page.waitForFunction(()=>document.querySelector('#protect-error').textContent.includes('full'));
  assert.equal((await page.evaluate(()=>window.jamDiagnostics())).playing,false);assert.ok((await page.evaluate(()=>window.jamDiagnostics())).samples>0);
  await page.locator('#protect-cancel').click();await page.locator('#play').click();await page.locator('#protect-discard').click();await page.waitForFunction(()=>window.jamDiagnostics().playing);await page.waitForTimeout(1000);await page.locator('#stop').click();
  // Downloading MIDI alone must not mark the audio as backed up.
  await page.locator('#export').click();let pending=page.waitForEvent('download');await page.locator('#midi-export').click();await pending;await page.getByRole('button',{name:'Close export',exact:true}).click();await page.locator('#play').click();await page.locator('#protect-take').waitFor();await page.locator('#protect-cancel').click();
  // WAV export permits a reload; the take library survives that reload.
  await page.locator('#export').click();pending=page.waitForEvent('download');await page.locator('#wav-export').click();await pending;await page.reload();await page.locator('#chords .chord').first().waitFor();
  await page.locator('#open-takes').click();await page.waitForFunction(()=>document.querySelectorAll('#take-list li').length===10);await page.getByRole('button',{name:'Close saved takes',exact:true}).click();
  await page.locator('#performance-mode').click();await page.screenshot({path:path.join(artifacts,'desktop.png'),fullPage:false});
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(artifacts,'mobile.png'),fullPage:true});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  const mobileKeyboard=await page.locator('#keyboard').boundingBox();assert.ok(mobileKeyboard.y+mobileKeyboard.height<=844,`Mobile keyboard bottom ${mobileKeyboard.y+mobileKeyboard.height}`);
  assert.deepEqual(errors,[]);fs.writeFileSync(path.join(artifacts,'results.json'),JSON.stringify({passed:true,errors,takePersistence:true,capacityProtection:true,overwriteCancel:true,saveAndContinue:true,discard:true,midiDoesNotProtectWav:true,timeline:true,desktopKeyboardFits:true,mobileKeyboardFits:true},null,2));console.log('Performance, timeline and take protection checks passed.');
 }finally{await browser?.close();service.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});

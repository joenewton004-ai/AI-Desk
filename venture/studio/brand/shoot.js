const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:2560,height:2400}});
await p.goto('file://'+__dirname+'/brand.html');
await (await p.$('#avatar')).screenshot({path:__dirname+'/profile_800.png'});
await (await p.$('#banner')).screenshot({path:__dirname+'/banner_2560x1440.png'});
await b.close()})();

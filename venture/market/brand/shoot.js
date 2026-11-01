const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:3360,height:2000}});
await p.goto('file://'+__dirname+'/brand.html');
await (await p.$('#icon')).screenshot({path:__dirname+'/shop_icon_1000.png'});
await (await p.$('#banner')).screenshot({path:__dirname+'/banner_3360x840.png'});
await b.close()})();

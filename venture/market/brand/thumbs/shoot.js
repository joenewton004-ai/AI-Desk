const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:2000,height:1500}});
await p.goto('file://'+__dirname+'/thumbs.html');
for(const id of ['p01','p02','b01']){await (await p.$('#'+id)).screenshot({path:__dirname+'/'+id+'_thumb.png'});}
await b.close()})();

import {test,expect} from '@playwright/test';

test('dashboard retains stale evidence, retries one panel and collapses freshness',async({page},info)=>{
 let targeted=0;
 const e={service:'contract-fixture',method:'reviewed-fixture',source_as_of:'2026-10-13T10:00:00Z',received_at:'2026-10-14T08:00:00Z',units:'INR; percent',synthetic:true,status:'historical',evidence_id:'fixture-evidence'};
 await page.route('**/api/v1/auth/me',r=>r.fulfill({json:{id:'fixture',email:'fixture@example.test',role:'researcher'}}));
 await page.route('**/api/v1/market/source-status',r=>r.fulfill({json:{services:{cmmkt:{discovery:'unavailable'},bhavcopy:{discovery:'available'}},cache_policy:{stale_seconds:900}}}));
 await page.route('**/api/v1/market/overview*',r=>{
  const cap=new URL(r.request().url()).searchParams.get('capability');
  if(cap){targeted++;return r.fulfill({json:{synthetic:true,status:'available',sections:{[cap]:{...e,status:'delayed',value:[{symbol:'ALPHA',price:120,change_percent:2}]}}}});}
  return r.fulfill({json:{synthetic:true,status:'partial',sections:{L02:{...e,value:{index:'NIFTY 50',close:24000,change_percent:1.2,open:23900,high:24100,low:23800}},L01:{...e,value:[{symbol:'ALPHA',price:100,change_percent:1}],status:'stale',availability:'stale_cache',cache_age_seconds:75,refresh_error:'UPSTREAM_TIMEOUT'},L05:{...e,value:null,status:'failed',availability:'source_failed',message:'Current losers source unavailable'},L08:{...e,value:{source_cache:{gainers:{available:false,lastCrawled:'2026-10-14T08:00:00Z'}}}}}}});
 });
 await page.goto('/dashboard');
 await expect(page.getByText('Last verified observation · cached 75 seconds ago.')).toBeVisible();
 await expect(page.getByText('Current losers source unavailable')).toBeVisible();
 await expect(page.getByText('cmmkt discovery: unavailable')).toBeVisible();
 const gainers=page.locator('article').filter({has:page.getByRole('heading',{name:'Top gainers',exact:true})});
 await gainers.getByRole('button',{name:'Retry source'}).click();
 await expect(gainers.getByRole('cell',{name:'120',exact:true})).toBeVisible();
 expect(targeted).toBe(1);
 await expect(page.getByRole('heading',{name:'Source freshness',exact:true})).not.toBeVisible();
 await page.getByText('Source freshness and cache metadata',{exact:true}).click();
 await expect(page.getByText('No',{exact:true})).toBeVisible();
 await page.screenshot({path:`test-results/${info.project.name}-recovery-dashboard.png`,fullPage:true});
});

test('HTML gateway failure ends loading and displays actionable retry guidance',async({page})=>{
 await page.route('**/api/v1/auth/me',r=>r.fulfill({json:{id:'fixture',email:'fixture@example.test',role:'researcher'}}));
 await page.route('**/api/v1/market/overview*',r=>r.fulfill({status:502,contentType:'text/html',body:'<html><h1>Bad Gateway</h1></html>'}));
 await page.goto('/dashboard');
 await expect(page.getByRole('alert')).toContainText('HTTP 502');
 await expect(page.getByText('Source request failed. No observations were returned.')).toHaveCount(4);
 await expect(page.getByRole('status')).toHaveCount(0);
 await expect(page.getByText('Unexpected token')).toHaveCount(0);
});

import {test,expect} from '@playwright/test';

test('all returned fields and rows render; one failed instrument panel preserves others',async({page},info)=>{
 const evidence={service:'fixture',method:'display-regression',status:'historical',source_as_of:'2026-10-09T10:00:00Z',received_at:'2026-10-11T08:00:00Z',units:'test observations',synthetic:true};
 await page.route('**/api/v1/auth/me',route=>route.fulfill({json:{id:'display-test',email:'display@example.test',role:'researcher'}}));
 await page.route('**/api/v1/market/overview*',route=>route.fulfill({json:{synthetic:true,sections:{L02:{...evidence,value:Array.from({length:101},(_,i)=>({symbol:`ROW${i}`,a:1,b:2,c:3,d:4,e:5,f:6,g:7,eighth_field:'visible',...(i===100?{last_row_field:'last observation'}:{})}))}}}}));
 await page.goto('/dashboard');
 await expect(page.getByRole('columnheader',{name:'eighth field'})).toBeVisible();
 await expect(page.getByRole('cell',{name:'ROW100',exact:true})).toHaveCount(1);
 await expect(page.getByRole('columnheader',{name:'last row field'})).toBeVisible();
 await page.screenshot({path:`test-results/${info.project.name}-refreshed-dashboard.png`,fullPage:true});
 await page.route('**/api/v1/instruments/TCS/quote',route=>route.fulfill({status:503,json:{message:'Quote source timed out',error_code:'UPSTREAM_TIMEOUT'}}));
 await page.route('**/api/v1/instruments/TCS/history*',route=>route.fulfill({json:{...evidence,value:[{date:'2026-10-09',close:123,volume:456}]}}));
 await page.route('**/api/v1/instruments/TCS/range',route=>route.fulfill({json:{...evidence,value:{range:{high:150,low:80},flags:['dated','verified']}}}));
 await page.goto('/instruments/TCS');
 await expect(page.getByRole('alert')).toContainText('Quote source timed out');
 await expect(page.getByRole('cell',{name:'123',exact:true})).toBeVisible();
 await expect(page.getByText('[object Object]',{exact:true})).toHaveCount(0);
 await page.screenshot({path:`test-results/${info.project.name}-refreshed-instrument.png`,fullPage:true});
});

import {test,expect} from '@playwright/test';
test('allowlisted administrator can inspect telemetry and roles',async({page,request},testInfo)=>{
 const credentials={email:'admin@example.test',password:'strong-test-password',acknowledged:true};
 let result=await request.post('/api/v1/auth/register',{data:credentials});if(result.status()===409)result=await request.post('/api/v1/auth/login',{data:credentials});
 expect(result.ok()).toBeTruthy();const auth=await result.json();expect(auth.user.role).toBe('administrator');
 await page.addInitScript(token=>sessionStorage.setItem('marketmind-token',token),auth.access_token);await page.goto('/admin/mcp');
 await expect(page.getByRole('heading',{name:'MCP observability'})).toBeVisible();await expect(page.getByRole('heading',{name:'Workspace users'})).toBeVisible();
 await page.screenshot({path:`test-results/${testInfo.project.name}-admin.png`,fullPage:true});
});

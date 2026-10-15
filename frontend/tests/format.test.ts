import {expect,test,vi,afterEach} from 'vitest';
import {api,dateLabel,numberLabel} from '../src/api';
test('AT-002 missing numbers are not fabricated',()=>{expect(numberLabel(null)).toBe('Unavailable');});
test('source dates display in IST',()=>{expect(dateLabel('2026-10-09T10:00:00+00:00')).toContain('IST');expect(dateLabel(null)).toBe('Not supplied');});
afterEach(()=>vi.unstubAllGlobals());
test('HTML proxy errors show actionable messages instead of JSON syntax errors',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html><h1>Bad Gateway</h1></html>',{status:502})));
 await expect(api('/market/overview')).rejects.toThrow('API gateway returned HTTP 502');
});
test('successful HTML is rejected as an unexpected response',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('<html>SPA fallback</html>',{status:200})));
 await expect(api('/market/overview')).rejects.toThrow('unexpected non-JSON');
});
test('structured API errors preserve trace identifiers',async()=>{
 vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({message:'Source timed out',error_code:'UPSTREAM_TIMEOUT',request_id:'trace-123'}),{status:504})));
 await expect(api('/market/overview')).rejects.toThrow('trace-123');
});
test('cache booleans and timestamps render as readable values',()=>{
 expect(numberLabel(true)).toBe('Yes');expect(numberLabel(false)).toBe('No');
 expect(numberLabel('2026-10-11T09:16:16.76658502Z')).toContain('IST');
});

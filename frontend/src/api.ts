export type Evidence={service:string;method:string;instrument?:string;value:unknown;units?:string;currency?:string;source_as_of:string|null;source_precision?:string;received_at:string;status:string;data_delay_label?:string;evidence_id?:string;synthetic?:boolean;message?:string;warnings?:string[];historical_fallback?:boolean;availability?:string;cache_age_seconds?:number;refresh_error?:string};
export type Metric={symbol:string;return_percent:string|null;max_drawdown_percent:string|null;annualized_volatility_percent:string|null;moving_average_20:string|null;volume_ratio:string|null;sample_size:number;original_sample_size:number;missing_sessions:string[];timeline:{date:string;normalized:string}[];source_as_of:string;evidence_ids:string[]};
export type Analysis={sample_size:number;sessions:string[];metrics:Metric[];observations:Evidence[];warnings:string[];methodology:string;portfolio?:Record<string,unknown>|null;synthetic?:boolean};
export type Run={id:string;state:string;params:Scope;created_at:string;report_id:string;result:{final:{summary:string;disclaimer:string;claims:unknown[]};metrics:Analysis;evidence:Evidence[];warnings:string[];tools_called:unknown[];synthetic:boolean}};
export type Scope={symbols:string[];start:string;end:string;query:string;index:string;source:string};
let accessToken=typeof sessionStorage==='undefined'?'':sessionStorage.getItem('marketmind-token')||'';
export function setToken(value:string){accessToken=value;if(value)sessionStorage.setItem('marketmind-token',value);else sessionStorage.removeItem('marketmind-token');}
export async function api<T>(path:string,body?:unknown,method?:string):Promise<T>{
 const response=await fetch('/api/v1'+path,{method:method|| (body?'POST':'GET'),headers:{'Content-Type':'application/json',Authorization:'Bearer '+accessToken},...(body?{body:JSON.stringify(body)}:{})});
 const text=await response.text();
 let result;
 try{result=JSON.parse(text);}catch{throw new Error(response.ok?'The API returned an unexpected non-JSON response. Refresh and check backend logs.':`The API gateway returned HTTP ${response.status}. The backend may be restarting or a source request timed out. Please retry.`);}
 if(!response.ok){throw new Error(`${result.message||'Request failed'} (${result.error_code||response.status}${result.request_id?'; trace '+result.request_id:''})${result.details?.length?' — '+result.details.map((d:{message:string})=>d.message).join('; '):''}`);}
 return result as T;
}
export async function exportReport(id:string){
 const response=await fetch('/api/v1/reports/'+id+'/export',{headers:{Authorization:'Bearer '+accessToken}});
 if(!response.ok)throw new Error('Report export failed');
 const url=URL.createObjectURL(await response.blob());const a=document.createElement('a');a.href=url;a.download=`marketmind-${id}.html`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
export const dateLabel=(stamp:string|null)=>stamp?new Intl.DateTimeFormat('en-IN',{timeZone:'Asia/Kolkata',dateStyle:'medium',timeStyle:'short'}).format(new Date(stamp))+' IST':'Not supplied';
export const numberLabel=(value:unknown)=>value==null?'Unavailable':typeof value==='boolean'?(value?'Yes':'No'):typeof value==='string'&&value.includes('T')&&/^\d{4}-\d{2}-\d{2}T/.test(value)&&Number.isFinite(Date.parse(value))?dateLabel(value):value===''?'Not supplied':Number.isFinite(Number(value))?new Intl.NumberFormat('en-IN',{maximumFractionDigits:4}).format(Number(value)):String(value);

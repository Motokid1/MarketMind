"""FR-002,003,015,016,017: reviewed metadata registry and bounded SDK gateway."""
import asyncio
import copy
import hashlib
import json
import random
import time
import contextvars
import httpx
from datetime import datetime, timezone
from pathlib import Path
from jsonschema import validate, Draft202012Validator
from mcp import ClientSession
from mcp.types import PaginatedRequestParams
from mcp.client.streamable_http import streamable_http_client
from .core import DomainError, settings, now
from .db import Session, Invocation, Registry

ENDPOINTS={'bhavcopy':'https://mcp.nseindia.in/bhavcopy/cm/mcp','cmmkt':'https://mcp.nseindia.in/cmmkt/mcp'}
CAPABILITIES={'B01':'Symbol search','B02':'OHLCV history','B03':'Closing quote on date','B04':'Returns','B05':'Volume trends','B06':'Bulk quotes','B07':'Historical gainers','B08':'Historical losers','B09':'Multi-stock compare','B10':'52-week range','B11':'Historical breadth','L01':'Current gainers','L02':'Index data','L03':'SME listings','L04':'Current quote','L05':'Current losers','L06':'Equity listings','L07':'Bond listings','L08':'Freshness'}
call_budget=contextvars.ContextVar('call_budget',default=None)

def source_params(params):
    # Free-form user questions are private run data, never shared cache metadata.
    allowed={'symbol','symbols','start','end','index','q','segment','months','limit','direction'}
    return {k:v for k,v in params.items() if k in allowed}
def spend():
    budget=call_budget.get()
    if budget is not None:
        if budget['used']>=12:
            raise DomainError('TOOL_BUDGET','Run reached the 12-call safety limit',429)
        budget['used']+=1
def transient(error):
    if isinstance(error,BaseExceptionGroup):
        return all(transient(e) for e in error.exceptions)
    return isinstance(error,(TimeoutError,OSError,httpx.TransportError)) or isinstance(error,httpx.HTTPStatusError) and error.response.status_code in (429,502,503,504)
def schema_hash(schema):
    return hashlib.sha256(json.dumps(schema,sort_keys=True).encode()).hexdigest()

def error_tag(error):
    if isinstance(error,BaseExceptionGroup):
        return error_tag(error.exceptions[0])
    if isinstance(error,httpx.HTTPStatusError):
        return 'UPSTREAM_HTTP_'+str(error.response.status_code)
    return getattr(error,'code','UPSTREAM_TIMEOUT' if isinstance(error,TimeoutError) else 'SOURCE_FAILED')

class RegistryStore:
    def __init__(self):
        self.tools={}
        self.alerts=[]
        self.bindings={}
    def sync(self, service, discovered):
        seen=set()
        for tool in discovered:
            key=service+':'+tool['name']
            seen.add(key)
            previous=self.tools.get(key)
            digest=schema_hash(tool['inputSchema'])
            same=previous and previous['schema_hash']==digest
            self.tools[key]={**copy.deepcopy(tool),'id':key,'service':service,'schema_hash':digest,'enabled':bool(same and previous['enabled']),'capability':previous.get('capability') if same else None,'args':previous.get('args',{}) if same else {},'response':previous.get('response',{}) if same else {},'validated_at':now().isoformat(),'status':'APPROVED' if same and previous['enabled'] else 'UNMAPPED'}
            if previous and not same:
                self.tools[key]['status']='SCHEMA_CHANGED'
                self.alerts.append({'id':key,'reason':'Schema changed; disabled pending manual review'})
        for key, tool in self.tools.items():
            if tool['service']==service and key not in seen:
                tool.update(enabled=False,status='REMOVED')
    def approve(self, key, capability, args, digest, response=None):
        tool=self.tools.get(key)
        if not tool or digest!=tool['schema_hash'] or capability not in CAPABILITIES or tool['service']!=('bhavcopy' if capability.startswith('B') else 'cmmkt'):
            raise DomainError('INVALID_MAPPING','Discovered method, capability and exact schema hash required')
        props=tool['inputSchema'].get('properties',{})
        if any(v not in props for v in args.values()) or set(tool['inputSchema'].get('required',[]))-set(args.values()):
            raise DomainError('INVALID_MAPPING','Map every required discovered argument; unknown fields rejected')
        Draft202012Validator.check_schema(tool['inputSchema'])
        tool.update(enabled=True,capability=capability,args=args,response=response or {},status='APPROVED')
    def select(self, capability):
        if capability in self.bindings:
            binding=self.bindings[capability]
            tool=self.tools.get(binding['id'])
            if tool and tool['enabled'] and tool['schema_hash']==binding['schema_hash']:
                return {**tool,**binding}
            raise DomainError('SCHEMA_CHANGED','Approved capability schema unavailable; method disabled',503)
        matches=[t for t in self.tools.values() if t['enabled'] and t['capability']==capability]
        if len(matches)!=1:
            raise DomainError('SOURCE_UNAVAILABLE',f'{CAPABILITIES[capability]} has no unique approved method',503,True)
        return matches[0]

class Gateway:
    def __init__(self, transport=None):
        self.registry=RegistryStore()
        self.transport=transport
        self.cache={}
        self.verified={}
        self.source_status={s:{'discovery':'not_checked','last_error':None} for s in ENDPOINTS}
        self.capability_status={}
        self.failures={}
        self.breakers={}
        self.semaphores={s:asyncio.Semaphore(settings.concurrency) for s in ENDPOINTS}
    async def sync(self):
        results={}
        for service,url in ENDPOINTS.items():
            try:
                async with asyncio.timeout(settings.timeout):
                    async with streamable_http_client(url) as (read,write,_):
                        async with ClientSession(read,write) as session:
                            await session.initialize()
                            tools=[]
                            cursor=None
                            while True:
                                page=await session.list_tools(params=PaginatedRequestParams(cursor=cursor) if cursor else None)
                                tools.extend(t.model_dump(by_alias=True) for t in page.tools)
                                cursor=page.nextCursor
                                if not cursor:
                                    break
                self.registry.sync(service,tools)
                results[service]='discovered'
                self.source_status[service]={'discovery':'available','checked_at':now().isoformat(),'last_error':None}
            except Exception as exc:
                for tool in self.registry.tools.values():
                    if tool['service']==service:
                        tool.update(enabled=False,status='DISCOVERY_FAILED')
                results[service]='BLOCKED'
                self.source_status[service]={'discovery':'unavailable','checked_at':now().isoformat(),'last_error':error_tag(exc)}
        self.load_reviewed_bindings()
        self.persist_registry()
        return results
    def load_reviewed_bindings(self):
        path=Path(__file__).resolve().parents[1]/'specs/generated/reviewed-bindings.json'
        if not path.exists():
            return
        for binding in json.loads(path.read_text()):
            tool=self.registry.tools.get(binding['id'])
            if tool and tool['status'] not in ('SCHEMA_CHANGED','REMOVED','DISCOVERY_FAILED') and tool['schema_hash']==binding['schema_hash']:
                self.registry.approve(binding['id'],binding['capability'],binding['args'],binding['schema_hash'])
                self.registry.bindings[binding['capability']]=binding
        with Session() as db:
            for row in db.query(Registry).all():
                for binding in (row.reviewed_config or {}).get('bindings',[]):
                    tool=self.registry.tools.get(binding['id'])
                    if tool and tool['schema_hash']==binding['schema_hash'] and tool['status'] not in ('SCHEMA_CHANGED','REMOVED','DISCOVERY_FAILED'):
                        self.registry.approve(binding['id'],binding['capability'],binding['args'],binding['schema_hash'],binding.get('response'))
                        self.registry.bindings[binding['capability']]=binding
    def persist_registry(self):
        with Session() as db:
            for t in self.registry.tools.values():
                row=db.get(Registry,t['id']) or Registry(id=t['id'])
                row.service=t['service']; row.method=t['name']; row.schema_hash=t['schema_hash']; row.input_schema=t['inputSchema']; row.capability=t['capability']; row.enabled=t['enabled']; row.validated_at=now()
                row.reviewed_config={'bindings':[b for b in self.registry.bindings.values() if b['id']==t['id']]}
                db.add(row)
            db.commit()
    async def invoke(self, tool, arguments):
        spend()
        if self.transport:
            return await self.transport(tool,arguments)
        url=ENDPOINTS[tool['service']]
        async with httpx.AsyncClient(follow_redirects=False,timeout=settings.timeout) as client:
          async with streamable_http_client(url,http_client=client) as (read,write,_):
            async with ClientSession(read,write) as session:
                await session.initialize()
                result=await session.call_tool(tool['name'],arguments)
                if result.isError:
                    raise DomainError('UPSTREAM_ERROR','MCP tool returned an error',502,True)
                if result.structuredContent is not None:
                    return result.structuredContent
                texts=[c.text for c in result.content if c.type=='text']
                if len(texts)!=1 or len(texts[0].encode())>1_000_000:
                    raise DomainError('PROTOCOL_ERROR','Expected bounded structured JSON tool data',502)
                return json.loads(texts[0])
    def stale(self, tool, key, reason, run_id=None):
        entry=self.verified.get(key)
        if not entry or time.monotonic()-entry[0]>settings.stale_ttl:
            return None
        result=copy.deepcopy(entry[1])
        result.update(status='stale',availability='stale_cache',cache_age_seconds=round(time.monotonic()-entry[0],2),refresh_error=reason)
        result['warnings']=[*result.get('warnings',[]),'Last verified observation retained during a source outage. Not refreshed current data.']
        self.record(tool,run_id,0,'stale_cache',result,reason)
        self.capability_status[result['capability']]={'status':'stale_cache','checked_at':now().isoformat(),'last_error':reason}
        return result

    async def call(self, capability, params, run_id=None, refresh=False):
        discovery_failed=False
        try:
            tool=self.registry.select(capability)
        except DomainError:
            binding=self.registry.bindings.get(capability,{})
            previous=self.registry.tools.get(binding.get('id'))
            if not previous or previous['status']!='DISCOVERY_FAILED' or previous['schema_hash']!=binding.get('schema_hash'):
                raise
            tool={**previous,**binding}
            discovery_failed=True
        params={**tool.get('defaults',{}),**params}
        arguments={target:params[source] for source,target in tool['args'].items() if source in params}
        try:
            validate(arguments,tool['inputSchema'])
        except Exception:
            raise DomainError('INVALID_TOOL_INPUT','Parameters do not match discovered tool schema')
        key=tool['schema_hash']+tool['id']+json.dumps({'arguments':arguments,'normalization_scope':source_params(params)},sort_keys=True)
        if discovery_failed:
            cached=self.stale(tool,key,'DISCOVERY_FAILED',run_id)
            if cached:
                return cached
            raise DomainError('SOURCE_UNAVAILABLE','Discovery unavailable and no eligible verified observation retained',503,True)
        if not refresh and key in self.cache and time.monotonic()-self.cache[key][0]<settings.ttl:
            cached=copy.deepcopy(self.cache[key][1])
            cached['cache_age_seconds']=round(time.monotonic()-self.cache[key][0],2)
            cached['status']=freshness(cached['source_as_of'],tool['service'],cached.get('market_status'))
            self.record(tool,run_id,0,'cache',cached)
            return cached
        service=tool['service']
        if time.monotonic()<self.breakers.get(service,0):
            cached=self.stale(tool,key,'CIRCUIT_OPEN',run_id)
            if cached:
                return cached
            raise DomainError('CIRCUIT_OPEN','Source temporarily unavailable',503,True)
        began=time.monotonic()
        try:
            async with self.semaphores[service]:
                for attempt in range(settings.retries+1):
                    try:
                        async with asyncio.timeout(settings.timeout):
                            payload=await self.invoke(tool,arguments)
                        break
                    except Exception as exc:
                        if not transient(exc) or attempt==settings.retries:
                            raise
                        await asyncio.sleep(.15*2**attempt+random.random()*.1)
            if len(json.dumps(payload).encode())>1_000_000:
                raise DomainError('RESPONSE_TOO_LARGE','Source response exceeds allowed size',502)
            raw_hash=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
            if tool.get('parser'):
                from .nse_adapters import adapt
                payload=adapt(tool,payload,params)
            output=normalize(tool,payload,params)
            output['raw_ref']='sha256:'+raw_hash
            output['capability']=capability
            output['availability']='missing_timestamp' if not output['source_as_of'] else 'missing_value' if output['value'] is None else 'empty' if output['value']==[] else 'available'
            if output['value'] is None:
                cached=self.stale(tool,key,output['availability'],run_id)
                if cached:
                    return cached
            self.cache[key]=(time.monotonic(),copy.deepcopy(output))
            if output['value'] is not None and not output['missing_fields']:
                self.verified[key]=(time.monotonic(),copy.deepcopy(output))
            for store in (self.cache,self.verified):
                expired=[k for k,(stamp,_) in store.items() if time.monotonic()-stamp>max(settings.ttl,settings.stale_ttl)]
                for k in expired:
                    del store[k]
                while len(store)>256:
                    del store[min(store,key=lambda k:store[k][0])]
            keys=set(self.cache)|set(self.verified)
            while len(keys)>256:
                oldest=min(keys,key=lambda k:min(store[k][0] for store in (self.cache,self.verified) if k in store))
                self.cache.pop(oldest,None);self.verified.pop(oldest,None);keys.remove(oldest)
            self.capability_status[capability]={'status':output['availability'],'checked_at':now().isoformat(),'last_error':None,'source_as_of':output['source_as_of']}
            self.failures[service]=0
            self.record(tool,run_id,int((time.monotonic()-began)*1000),'ok',output)
            return output
        except Exception as exc:
            self.failures[service]=self.failures.get(service,0)+1
            if self.failures[service]>=3:
                self.breakers[service]=time.monotonic()+30
            self.record(tool,run_id,int((time.monotonic()-began)*1000),'error',None,type(exc).__name__)
            reason=error_tag(exc)
            self.capability_status[capability]={'status':'source_failed','checked_at':now().isoformat(),'last_error':reason}
            if transient(exc) or isinstance(exc,DomainError) and exc.retryable:
                cached=self.stale(tool,key,reason,run_id)
                if cached:
                    return cached
            if isinstance(exc,DomainError):
                raise
            raise DomainError('UPSTREAM_TIMEOUT' if isinstance(exc,TimeoutError) else 'SOURCE_FAILED','Source unavailable; no values fabricated',504 if isinstance(exc,TimeoutError) else 503,True)
    def record(self,tool,run_id,ms,status,output,error=None):
        with Session() as db:
            db.add(Invocation(run_id=run_id,service=tool['service'],method=tool['name'],schema_hash=tool['schema_hash'],duration_ms=ms,status=status,error_code=error,evidence_ref=output['evidence_id'] if output else None,source_as_of=output['source_as_of'] if output else None))
            db.commit()
    async def history(self,params,run_id=None):
        chunks=[]; warnings=[]; cursor=params['end']; seen=set()
        for _ in range(12):
            if cursor in seen:
                warnings.append('Repeated history cursor rejected');break
            seen.add(cursor)
            try:
                chunk=await self.call('B02',{**params,'end':cursor},run_id)
            except DomainError as exc:
                if not chunks:
                    raise
                warnings.append(f'History incomplete: {exc.code}');break
            chunks.append(chunk)
            next_date=chunk.get('next_end_date')
            if not next_date or next_date<params['start']:
                break
            cursor=next_date
        else:
            warnings.append('History chunk limit reached; available range only')
        output=copy.deepcopy(chunks[0])
        output['value']=sorted([row for c in chunks for row in (c['value'] or [])],key=lambda r:r['date']) if any(c['value'] is not None for c in chunks) else None
        output['query_params']=source_params(params)
        output['input_evidence_ids']=[c['evidence_id'] for c in chunks]
        output['evidence_id']=hashlib.sha256(''.join(output['input_evidence_ids']).encode()).hexdigest()
        output['raw_ref']='sha256:'+output['evidence_id']
        output['warnings']=warnings
        output['coverage_status']='partial' if warnings else 'available'
        return output

def freshness(as_of,service,market_status=None):
    if not as_of:
        return 'missing'
    if service=='bhavcopy' or market_status=='closed':
        return 'historical' if service=='bhavcopy' else 'closed'
    stamp=datetime.fromisoformat(as_of.replace('Z','+00:00'))
    return 'stale' if (now()-stamp).total_seconds()>settings.freshness else 'delayed'

def normalize(tool,payload,params):
    mapping=tool.get('response',{})
    def get(field,default=None):
        value=payload
        for part in mapping.get(field,field).split('.'):
            value=value.get(part) if isinstance(value,dict) else None
        return default if value is None else value
    as_of=get('source_as_of')
    if as_of:
        try:
            stamp=datetime.fromisoformat(as_of.replace('Z','+00:00'))
            if stamp.tzinfo is None or stamp>now():
                raise ValueError()
            as_of=stamp.astimezone(timezone.utc).isoformat()
        except (ValueError,TypeError):
            raise DomainError('INVALID_SOURCE_TIME','Source timestamp must be timezone aware and not future',502)
    value=get('value') if as_of else None
    units=get('units')
    if value is not None and not units:
        value=None
    status=freshness(as_of,tool['service'],get('market_status'))
    digest=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    return {'service':tool['service'],'method':tool['name'],'instrument':params.get('symbol',params.get('index')),'value':value,'message':('Source did not supply a verifiable as-of timestamp; values withheld.' if not as_of else 'Source did not supply a value with units.' if value is None else None),'units':units,'currency':get('currency'),'source_as_of':as_of,'source_precision':get('source_precision'),'received_at':now().isoformat(),'data_delay_label':'Synthetic fixture — not NSE data' if tool.get('synthetic') else ('Previous final session' if tool['service']=='bhavcopy' else 'Indicative 1–3 minute delay'),'evidence_id':digest,'missing_fields':[k for k,v in {'source_as_of':as_of,'value':value,'units':units}.items() if v is None],'raw_ref':'sha256:'+digest,'status':status,'market_status':get('market_status'),'query_params':source_params(params),'schema_hash':tool['schema_hash'],'synthetic':tool.get('synthetic',False),'next_end_date':get('next_end_date')}

gateway=Gateway()





"""API-001: authenticated versioned API with reproducible derived reports."""
import asyncio
import time
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import timedelta
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from sqlalchemy import select, delete, text
from .core import settings, Credentials, Scope, Portfolio, DomainError, now
from .db import get_db, User, Run, Report, Audit, Observation, Metric, Invocation
from .auth import hash_password, check_password, token, identity, admin
from .gateway import gateway, CAPABILITIES
from .mock import install_mock
from .analytics import compare, portfolio, VERSION
from .workflow import execute, DISCLAIMER

@asynccontextmanager
async def lifespan(app):
    recovery=None
    if settings.mock:
        install_mock(gateway)
    else:
        discovered=await gateway.sync()
        if 'BLOCKED' in discovered.values():
            recovery=asyncio.create_task(recover_discovery())
    try:
        yield
    finally:
        if recovery:
            recovery.cancel()
            with suppress(asyncio.CancelledError):
                await recovery

async def recover_discovery():
    # A transient startup outage must not leave the registry empty until restart.
    # Every retry still discovers actual schemas and validates reviewed hashes.
    await asyncio.sleep(5)
    while True:
        results=await gateway.sync()
        if 'BLOCKED' not in results.values():
            return
        await asyncio.sleep(60)

app=FastAPI(title='MarketMind AI',version='1.0.0',lifespan=lifespan)
@app.middleware('http')
async def request_id(request,call_next):
    request.state.request_id=str(uuid.uuid4())
    response=await call_next(request)
    response.headers['X-Request-ID']=request.state.request_id
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Cache-Control']='no-store'
    return response
def error_response(request,code,message,status,retryable=False,details=None):
    return JSONResponse({'request_id':getattr(request.state,'request_id',str(uuid.uuid4())),'error_code':code,'message':message,'retryable':retryable,'details':details},status_code=status)
@app.exception_handler(DomainError)
async def domain_error(request,exc):
    return error_response(request,exc.code,exc.message,exc.status,exc.retryable)
@app.exception_handler(RequestValidationError)
async def validation_error(request,exc):
    return error_response(request,'VALIDATION_ERROR','Check the submitted fields',422,details=[{'field':'.'.join(map(str,e['loc'])),'message':e['msg']} for e in exc.errors()])
@app.exception_handler(ValidationError)
async def parameter_error(request,exc):
    return error_response(request,'VALIDATION_ERROR','Invalid symbol or date window',422)
@app.exception_handler(TimeoutError)
async def deadline_error(request,exc):
    return error_response(request,'DEADLINE_EXCEEDED','Research deadline reached; retry with a smaller scope',504,True)
@app.exception_handler(Exception)
async def unexpected(request,exc):
    return error_response(request,'INTERNAL_ERROR','Request failed; use the trace ID for investigation',500)

login_attempts={}
def throttle(key,limit=10,seconds=60):
    stamp=time.monotonic(); bucket=[s for s in login_attempts.get(key,[]) if stamp-s<seconds]
    if len(bucket)>=limit:
        raise DomainError('RATE_LIMIT','Try again later',429,True)
    login_attempts[key]=bucket+[stamp]

@app.get('/health/live')
def live():
    return {'status':'alive'}
@app.get('/health/ready')
def ready(db=Depends(get_db)):
    try:
        db.execute(text('select 1'))
    except Exception:
        raise DomainError('DATABASE_UNAVAILABLE','Database unavailable',503,True)
    enabled=sum(t['enabled'] for t in gateway.registry.tools.values())
    covered=0
    for capability in CAPABILITIES:
        try:
            gateway.registry.select(capability);covered+=1
        except DomainError:
            pass
    return {'status':'ready' if covered==len(CAPABILITIES) else 'degraded','database':'ready','mcp':'synthetic' if settings.mock else ('available' if covered==len(CAPABILITIES) else 'partial' if enabled else 'unavailable'),'enabled_methods':enabled,'covered_capabilities':covered}
@app.post('/api/v1/auth/register',status_code=201)
def register(body:Credentials,request:Request,db=Depends(get_db)):
    throttle('register:'+request.client.host)
    if not body.acknowledged:
        raise DomainError('TERMS_REQUIRED','Acknowledge educational data use before registering')
    email=body.email.lower()
    if db.scalar(select(User).where(User.email==email)):
        raise DomainError('ACCOUNT_EXISTS','Account already exists',409)
    user=User(email=email,password_hash=hash_password(body.password),role='administrator' if email in settings.admins else 'researcher')
    db.add(user); db.flush(); db.add(Audit(actor_id=user.id,action='register',entity_id=user.id,status='ok')); db.commit()
    return {'access_token':token(user),'token_type':'bearer','user':{'id':user.id,'email':user.email,'role':user.role}}
@app.post('/api/v1/auth/login')
def login(body:Credentials,request:Request,db=Depends(get_db)):
    throttle('login:'+request.client.host)
    user=db.scalar(select(User).where(User.email==body.email.lower()))
    if not user or not user.active or not check_password(body.password,user.password_hash):
        raise DomainError('INVALID_CREDENTIALS','Invalid credentials',401)
    return {'access_token':token(user),'token_type':'bearer','user':{'id':user.id,'email':user.email,'role':user.role}}
@app.get('/api/v1/auth/me')
def me(user=Depends(identity)):
    return {'id':user.id,'email':user.email,'role':user.role}

async def sections(jobs,params,run_id=None,refresh=False):
    async def fetch(cap):
        try:
            return cap,await gateway.call(cap,params,run_id,refresh=True) if refresh else await gateway.call(cap,params,run_id)
        except DomainError as exc:
            return cap,{'status':'failed','availability':'source_failed','retryable':exc.retryable,'error_code':exc.code,'message':exc.message,'value':None,'source_as_of':None,'received_at':now().isoformat()}
    items=dict(await asyncio.gather(*(fetch(cap) for cap in jobs)))
    return {'status':'partial' if any(v['status'] in ('failed','missing','stale') for v in items.values()) else 'available','sections':items,'synthetic':settings.mock}

@app.get('/api/v1/market/overview')
async def overview(index:str='NIFTY 50',as_of:str|None=None,capability:str|None=None,refresh:bool=False,user=Depends(identity)):
    scope=Scope(index=index,**({'end':as_of} if as_of else {}))
    async with asyncio.timeout(110):
        jobs=('B07','B08','B11') if as_of else ('L02','L01','L05','L08')
        if capability and capability not in jobs:
            raise DomainError('INVALID_CAPABILITY','Choose a dashboard capability for the selected mode')
        result=await sections((capability,) if capability else jobs,scope.model_dump(mode='json'),refresh=refresh)
        # A dated index observation can anchor a historical replay when the
        # current movers source lacks timestamps. Never label it current data.
        index_observation=result['sections'].get('L02',{})
        stamp=index_observation.get('source_as_of')
        if not as_of and stamp and index_observation.get('value') is not None:
            from datetime import datetime
            from zoneinfo import ZoneInfo
            session_date=datetime.fromisoformat(stamp.replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Kolkata')).date().isoformat()
            missing=[(current,historical) for current,historical in (('L01','B07'),('L05','B08')) if current in result['sections'] and result['sections'][current].get('value') is None]
            if missing:
                replay=await sections(tuple(h for _,h in missing),{**scope.model_dump(mode='json'),'end':session_date})
                for current,historical in missing:
                    observation=replay['sections'][historical]
                    if observation.get('value') is not None:
                        result['sections'][current]={**observation,'historical_fallback':True,'warnings':[*observation.get('warnings',[]),f'Current movers unavailable. Historical replay for {session_date}; not current-market rankings.']}
        return result

@app.get('/api/v1/market/source-status')
def source_status(user=Depends(identity)):
    return {'synthetic':settings.mock,'services':gateway.source_status,'capabilities':gateway.capability_status,'cache_policy':{'fresh_seconds':settings.ttl,'stale_seconds':settings.stale_ttl,'maximum_entries':256,'storage':'ephemeral process memory; cleared on restart'}}
@app.get('/api/v1/instruments/search')
async def search(q:str='',segment:str='equity',user=Depends(identity)):
    if segment not in ('equity','sme','bond') or len(q)>60:
        raise DomainError('INVALID_SEARCH','Choose equity, SME or bond and a short search')
    cap={'equity':'L06','sme':'L03','bond':'L07'}[segment]
    return await gateway.call(cap,{'q':q,'segment':segment})
@app.get('/api/v1/instruments/{symbol}/quote')
async def quote(symbol:str,as_of:str|None=None,user=Depends(identity)):
    scope=Scope(symbols=[symbol],**({'end':as_of} if as_of else {}))
    return await gateway.call('B03' if as_of else 'L04',{**scope.model_dump(mode='json'),'symbol':scope.symbols[0]})
@app.get('/api/v1/instruments/{symbol}/history')
async def history(symbol:str,start:str,end:str,user=Depends(identity)):
    scope=Scope(symbols=[symbol],start=start,end=end)
    return await gateway.history({**scope.model_dump(mode='json'),'symbol':scope.symbols[0]})
@app.get('/api/v1/instruments/{symbol}/range')
async def yearly(symbol:str,user=Depends(identity)):
    scope=Scope(symbols=[symbol])
    if not settings.mock:
        # Current quote supplies the range together with an exchange timestamp.
        # The standalone historical range response lacks an as-of date.
        quote=await gateway.call('L04',{'symbol':scope.symbols[0]})
        values=quote.get('value')
        return {**quote,'units':'INR','value':{k:values.get(k) for k in ('52_week_high','52_week_low')} if isinstance(values,dict) else None}
    return await gateway.call('B10',{**scope.model_dump(mode='json'),'symbol':scope.symbols[0]})

async def resolved(scope):
    for symbol in scope.symbols:
        obs=await gateway.call('B01',{'q':symbol})
        values=obs['value'] or []
        matches=[x for x in values if x.get('symbol')==symbol]
        if not matches:
            raise DomainError('INVALID_SYMBOL',f'No eligible symbol found: {symbol}')
        if len(matches)>1:
            raise DomainError('AMBIGUOUS_SYMBOL',f'Ambiguous symbol {symbol}; choose segment and ISIN explicitly',409)
        if matches[0].get('segment')!='equity':
            raise DomainError('UNSUPPORTED_SEGMENT','OHLCV research currently requires eligible equities')
async def histories(scope,run_id=None):
    await resolved(scope)
    p=scope.model_dump(mode='json')
    return await asyncio.gather(*(gateway.history({**p,'symbol':s},run_id) for s in scope.symbols))
@app.post('/api/v1/research/comparisons')
async def comparison(body:Scope,user=Depends(identity)):
    if len(body.symbols)<2:
        raise DomainError('INVALID_COMPARISON','Select between two and five equities')
    observations=await histories(body)
    return {**compare(observations),'observations':observations,'synthetic':settings.mock}
@app.post('/api/v1/portfolio/simulate')
async def simulate(body:Portfolio,user=Depends(identity)):
    observations=await histories(body)
    return {**portfolio(observations,body.weights,body.amount),'observations':observations,'disclaimer':DISCLAIMER,'synthetic':settings.mock}

def own_run(db,id,user):
    run=db.scalar(select(Run).where(Run.id==id,Run.owner_id==user.id))
    if not run:
        raise DomainError('NOT_FOUND','Research run not found',404)
    return run
def serialize_run(run,db):
    report=db.scalar(select(Report).where(Report.run_id==run.id))
    return {'id':run.id,'params':run.params,'state':run.state,'created_at':run.created_at,'completed_at':run.completed_at,'result':run.result,'report_id':report.id if report else None}
@app.post('/api/v1/research/runs',status_code=201)
async def research(body:Scope,user=Depends(identity),db=Depends(get_db)):
    throttle('run:'+user.id,limit=6)
    if len(body.symbols)>4:
        raise DomainError('TOOL_BUDGET','Briefing accepts at most four symbols within the 12-call budget')
    # Symbol resolution is also counted against the global run budget.
    warnings=[]
    run=Run(owner_id=user.id,params=body.model_dump(mode='json'))
    db.add(run); db.commit()
    try:
        state=await execute(gateway,run.id,user.id,run.params)
        state['warnings']+=warnings
        if warnings:
            state['status']='partial' if state['evidence_ids'] else 'degraded'
        state['final'].update(status=state['status'],warnings=state['warnings'])
        # Persist metadata and deterministic derived metrics; raw OHLCV stays TTL-only.
        evidence=[{k:v for k,v in o.items() if k!='value'} for o in state['observations']]
        run.result={'final':state['final'],'metrics':state['metrics'],'evidence':evidence,'tools_called':state['tools_called'],'warnings':state['warnings'],'formula_version':VERSION,'synthetic':settings.mock}
        run.state=state['status']; run.completed_at=now()
        for obs in evidence:
            db.merge(Observation(id=run.id+':'+obs['evidence_id'],run_id=run.id,lineage=obs,source_as_of=obs['source_as_of'],fetched_at=obs['received_at']))
        for metric in state['metrics']['metrics']:
            db.add(Metric(run_id=run.id,name=metric['symbol'],value=metric,formula_version=VERSION,input_ids=metric['evidence_ids']))
        db.add(Report(run_id=run.id,owner_id=user.id,retention_until=now()+timedelta(days=settings.retention)))
        db.add(Audit(actor_id=user.id,action='research',entity_id=run.id,status=run.state)); db.commit()
    except Exception:
        run.state='failed'; run.completed_at=now(); db.commit()
        raise
    return serialize_run(run,db)
@app.get('/api/v1/research/runs')
def runs(user=Depends(identity),db=Depends(get_db)):
    return [serialize_run(run,db) for run in db.scalars(select(Run).where(Run.owner_id==user.id).order_by(Run.created_at.desc()).limit(100))]
@app.get('/api/v1/research/runs/{id}')
def run_detail(id:str,user=Depends(identity),db=Depends(get_db)):
    return serialize_run(own_run(db,id,user),db)
@app.get('/api/v1/reports')
def reports(user=Depends(identity),db=Depends(get_db)):
    rows=list(db.scalars(select(Report).where(Report.owner_id==user.id)))
    if user.role=='reviewer':
        rows += [r for r in db.scalars(select(Report)) if user.id in (r.shared_with or [])]
    return [{'id':r.id,'run_id':r.run_id,'generated_at':r.generated_at,'annotations':r.annotations} for r in rows]
def accessible_report(db,id,user):
    report=db.get(Report,id)
    if not report or (report.owner_id!=user.id and not (user.role=='reviewer' and user.id in (report.shared_with or []))):
        raise DomainError('NOT_FOUND','Report not found',404)
    return report
@app.get('/api/v1/reports/{id}')
def report_detail(id:str,user=Depends(identity),db=Depends(get_db)):
    report=accessible_report(db,id,user)
    return serialize_run(db.get(Run,report.run_id),db)
@app.post('/api/v1/reports/{id}/share')
def share(id:str,body:dict,user=Depends(identity),db=Depends(get_db)):
    report=db.scalar(select(Report).where(Report.id==id,Report.owner_id==user.id))
    reviewer=db.get(User,body.get('reviewer_id',''))
    if not report or not reviewer or reviewer.role!='reviewer':
        raise DomainError('INVALID_SHARE','Own report and reviewer identity required')
    report.shared_with=list(set((report.shared_with or [])+[reviewer.id])); db.commit()
    return {'status':'shared'}
@app.post('/api/v1/reports/{id}/annotations')
def annotate(id:str,body:dict,user=Depends(identity),db=Depends(get_db)):
    report=accessible_report(db,id,user)
    note=body.get('text','')
    if user.role!='reviewer' or not isinstance(note,str) or not 1<=len(note)<=1000:
        raise DomainError('INVALID_ANNOTATION','Reviewer and bounded text required')
    report.annotations=(report.annotations or [])+[{'author':user.id,'text':note,'at':now().isoformat()}]; db.commit()
    return {'status':'annotated'}
@app.get('/api/v1/reports/{id}/export',response_class=HTMLResponse)
def export(id:str,user=Depends(identity),db=Depends(get_db)):
    report=accessible_report(db,id,user); run=db.get(Run,report.run_id)
    from .reporting import render_report
    return HTMLResponse(render_report(run),headers={'Content-Disposition':f'attachment; filename="marketmind-{run.id}.html"','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'"})

@app.get('/api/v1/admin/mcp/capabilities')
def capabilities(user=Depends(admin),db=Depends(get_db)):
    invocations=list(db.scalars(select(Invocation).order_by(Invocation.timestamp.desc()).limit(200)))
    return {'capabilities':CAPABILITIES,'tools':list(gateway.registry.tools.values()),'alerts':gateway.registry.alerts,'synthetic':settings.mock,'invocations':[{'id':i.id,'run_id':i.run_id,'service':i.service,'method':i.method,'duration_ms':i.duration_ms,'status':i.status,'schema_hash':i.schema_hash,'error_code':i.error_code,'timestamp':i.timestamp} for i in invocations],'settings':{'timeout':settings.timeout,'retries':settings.retries,'cache_ttl':settings.ttl,'retention_days':settings.retention,'concurrency':settings.concurrency,'max_run_calls':12,'graph_deadline_seconds':60}}
@app.post('/api/v1/admin/mcp/sync')
async def sync(user=Depends(admin)):
    if settings.mock:
        raise DomainError('SYNTHETIC_MODE','Live discovery disabled in synthetic mode',409)
    return await gateway.sync()
@app.post('/api/v1/admin/mcp/approve')
def approve(body:dict,user=Depends(admin),db=Depends(get_db)):
    gateway.registry.approve(body.get('id'),body.get('capability'),body.get('args',{}),body.get('schema_hash'),body.get('response',{}))
    gateway.registry.bindings[body['capability']]={k:body[k] for k in ('id','capability','args','schema_hash','response') if k in body}
    gateway.persist_registry(); db.add(Audit(actor_id=user.id,action='approve_mapping',entity_id=body['id'],status='ok')); db.commit()
    return {'status':'approved'}
@app.get('/api/v1/admin/users')
def users(user=Depends(admin),db=Depends(get_db)):
    return [{'id':u.id,'email':u.email,'role':u.role,'active':u.active} for u in db.scalars(select(User))]
@app.patch('/api/v1/admin/users/{id}')
def manage_user(id:str,body:dict,user=Depends(admin),db=Depends(get_db)):
    target=db.get(User,id)
    if not target or id==user.id or body.get('role',target.role) not in ('researcher','reviewer','administrator'):
        raise DomainError('INVALID_USER','Valid non-self user and role required')
    if body.get('role')=='administrator' and target.email not in settings.admins:
        raise DomainError('ADMIN_ALLOWLIST','Set ADMIN_EMAILS before granting administrator',403)
    target.role=body.get('role',target.role); target.active=bool(body.get('active',target.active)); db.commit()
    return {'status':'updated'}
@app.post('/api/v1/admin/retention/purge')
def purge(user=Depends(admin),db=Depends(get_db)):
    count=0
    for report in db.scalars(select(Report).where(Report.retention_until<now())):
        for model in (Observation,Metric):
            db.execute(delete(model).where(model.run_id==report.run_id))
        db.execute(delete(Report).where(Report.id==report.id))
        db.execute(delete(Run).where(Run.id==report.run_id)); count+=1
    db.execute(delete(Invocation).where(Invocation.timestamp<now()-timedelta(days=settings.retention)))
    db.commit(); gateway.cache.clear()
    return {'deleted_reports':count}

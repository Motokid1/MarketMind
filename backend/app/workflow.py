"""FR-011,013,014: bounded LangGraph with deterministic grounded writer."""
import asyncio
from typing import TypedDict
from langgraph.graph import StateGraph, END
from .core import DomainError
from .analytics import compare, VERSION
from .gateway import call_budget

DISCLAIMER='Educational hypothetical research only. Not investment advice or an order facility. NSE data may be delayed, incomplete or unadjusted. No movement cause is inferred.'
class State(TypedDict,total=False):
    run_id:str
    owner:str
    intent:str
    params:dict
    plan:list
    tools_called:list
    observations:list
    metrics:dict
    evidence_ids:list
    warnings:list
    status:str
    final:dict

def build_graph(gateway):
    async def intent(state):
        # A bounded deterministic intent parser; text cannot select raw methods.
        text=state['params']['query'].lower()
        if any(x in text for x in ('buy ','sell ','place order','execute trade')):
            raise DomainError('OUT_OF_SCOPE','Trading instructions and individualized advice are excluded')
        return {'intent':'historical briefing' if state['params']['source']=='historical' else 'current briefing','tools_called':[],'observations':[],'warnings':[]}
    async def plan(state):
        p=state['params']
        jobs=[{'worker':'history','capability':'B02','symbol':symbol} for symbol in p['symbols']]
        jobs+=([{'worker':'market','capability':c} for c in ('B07','B08','B11')] if p['source']=='historical' else [{'worker':'market','capability':c} for c in ('L02','L01','L05','L08')])
        if len(jobs)>12:
            raise DomainError('TOOL_BUDGET','Plan exceeds 12 calls')
        return {'plan':jobs}
    async def universe(state):
        resolved=[]; warnings=[]; observations=[]; tools=[]
        for symbol in state['params']['symbols']:
            try:
                obs=await gateway.call('B01',{'q':symbol},state['run_id'])
                matches=[r for r in (obs['value'] or []) if r.get('symbol')==symbol]
                if not matches:
                    raise DomainError('INVALID_SYMBOL',f'No eligible symbol found: {symbol}')
                if len(matches)>1:
                    raise DomainError('AMBIGUOUS_SYMBOL',f'Choose a segment and ISIN for {symbol}',409)
                if matches[0].get('segment')!='equity':
                    raise DomainError('UNSUPPORTED_SEGMENT','Historical calculations require eligible equities')
                resolved.append(symbol);observations.append({**obs,'capability':'B01','worker':'universe'})
                tools.append({'service':obs['service'],'method':obs['method'],'schema_hash':obs['schema_hash'],'capability':'B01'})
            except DomainError as exc:
                if exc.code in ('INVALID_SYMBOL','AMBIGUOUS_SYMBOL','UNSUPPORTED_SEGMENT'):
                    raise
                warnings.append(f'{symbol}: symbol resolution unavailable; history omitted')
        return {'params':{**state['params'],'symbols':resolved},'observations':observations,'tools_called':tools,'warnings':warnings}
    async def retrieval(state):
        p=state['params']
        observations=list(state['observations']); warnings=list(state['warnings']); tools=list(state['tools_called'])
        async def worker(job):
            cap=job['capability']
            params={**p,**({'symbol':job['symbol']} if 'symbol' in job else {})}
            try:
                observation=await gateway.history(params,state['run_id']) if cap=='B02' else await gateway.call(cap,params,state['run_id'])
                warnings.extend(observation.get('warnings',[]))
                observations.append({**observation,'capability':cap,'worker':job['worker']})
                tools.append({'service':observation['service'],'method':observation['method'],'schema_hash':observation['schema_hash'],'capability':cap})
            except DomainError as exc:
                warnings.append(f'{cap}: {exc.code} — {exc.message}')
        jobs=[j for j in state['plan'] if j['capability']!='B02' or j.get('symbol') in p['symbols']]
        await asyncio.gather(*(worker(j) for j in jobs))
        return {'observations':sorted(observations,key=lambda o:(o['capability'],o.get('instrument') or '')),'tools_called':tools,'warnings':warnings}
    async def calculation(state):
        histories=[o for o in state['observations'] if o['capability']=='B02' and o['status']!='stale' and o['value'] is not None and not o['missing_fields']]
        return {'metrics':compare(histories),'status':'calculating'}
    async def evidence(state):
        warnings=list(state['warnings'])
        eligible=[]
        for o in state['observations']:
            if o['missing_fields'] or o['value'] is None:
                warnings.append(f"{o['capability']}: missing source evidence; section omitted")
            elif o['status']=='stale':
                warnings.append(f"{o['capability']}: stale quote; current conclusions disabled")
            else:
                eligible.append(o)
        ids={o['evidence_id'] for o in eligible}
        for metric in state['metrics']['metrics']:
            if not set(metric['evidence_ids'])<=ids:
                raise DomainError('UNGROUNDED_METRIC','Calculated number lacks verified evidence',502)
        return {'evidence_ids':sorted(ids),'warnings':warnings,'status':'partial' if warnings else 'complete'}
    async def writer(state):
        # No model credentials required. Every displayed number is a structured claim.
        claims=[]
        by_id={o['evidence_id']:o for o in state['observations']}
        for o in state['observations']:
            if o['evidence_id'] not in state['evidence_ids'] or o['capability'] not in ('B07','B08','B11','L01','L02','L05'):
                continue
            rows=o['value'] if isinstance(o['value'],list) else [o['value']]
            for row in rows:
                if not isinstance(row,dict):
                    continue
                for key in ('close','price','change_percent','volume','advances','declines','unchanged','total_stocks'):
                    if row.get(key) is not None:
                        from .analytics import decimal
                        units='percent' if key=='change_percent' else 'shares' if key=='volume' else 'instruments' if key in ('advances','declines','unchanged','total_stocks') else 'index points' if o['capability']=='L02' else 'INR'
                        claims.append({'symbol':row.get('symbol',row.get('index',o['instrument'])),'metric':o['capability']+'_'+key,'value':str(decimal(row[key])),'units':units,'evidence_ids':[o['evidence_id']],'source_as_of':row.get('source_as_of') or o['source_as_of'],'formula_version':'source observation'})
        for metric in state['metrics']['metrics']:
            for key,unit in [('return_percent','percent'),('max_drawdown_percent','percent'),('annualized_volatility_percent','percent'),('moving_average_20','INR'),('volume_ratio','ratio'),('sample_size','trading sessions')]:
                if metric.get(key) is not None:
                    source=by_id[metric['evidence_ids'][0]]
                    claims.append({'symbol':metric['symbol'],'metric':key,'value':metric[key],'units':unit,'evidence_ids':metric['evidence_ids'],'source_as_of':source['source_as_of'],'formula_version':VERSION})
        return {'final':{'title':'Market research briefing','summary':'Historical observations and deterministic metrics. Causes of price or volume movements are not established by these sources.','claims':claims,'disclaimer':DISCLAIMER}}
    async def compliance(state):
        for claim in state['final']['claims']:
            if not claim['evidence_ids'] or not set(claim['evidence_ids'])<=set(state['evidence_ids']) or not claim['units'] or not claim['source_as_of']:
                raise DomainError('UNGROUNDED_CLAIM','Final claim rejected',502)
        return {'final':{**state['final'],'status':state['status'],'warnings':state['warnings'],'trace_id':state['run_id'],'evidence_ids':state['evidence_ids']}}
    async def publisher(state):
        return {'status':state['status'] if state['evidence_ids'] else 'degraded'}
    graph=StateGraph(State)
    nodes={'intent_parser':intent,'universe_worker':universe,'plan_validator':plan,'market_history_workers':retrieval,'calculation_worker':calculation,'evidence_validator':evidence,'writer':writer,'final_compliance':compliance,'report_publisher':publisher}
    previous=None
    for name,node in nodes.items():
        graph.add_node(name,node)
        if previous:
            graph.add_edge(previous,name)
        else:
            graph.set_entry_point(name)
        previous=name
    graph.add_edge(previous,END)
    return graph.compile()

async def execute(gateway,run_id,owner,params):
    budget=call_budget.set({'used':0})
    try:
        async with asyncio.timeout(60):
            return await build_graph(gateway).ainvoke({'run_id':run_id,'owner':owner,'params':params},config={'recursion_limit':20})
    finally:
        call_budget.reset(budget)

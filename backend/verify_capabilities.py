"""Opt-in, independent live capability evidence; metadata only, not a price archive."""
import argparse
import asyncio
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from app.core import today,now
from app.gateway import Gateway,CAPABILITIES
from app.nse_adapters import adapt

def shape(value):
    if isinstance(value,dict):return {k:shape(v) for k,v in value.items()}
    if isinstance(value,list):return {'count':len(value),'item':shape(value[0]) if value else None}
    if isinstance(value,str):return value if '2026-' in value or '-2026' in value else 'string'
    return type(value).__name__

async def verify(output):
    gateway=Gateway()
    discovery=await gateway.sync()
    end=today()-timedelta(days=1)
    while end.weekday()>4:end-=timedelta(days=1)
    params={'q':'RELIANCE','symbol':'RELIANCE','symbols':['RELIANCE','TCS'],'start':(end-timedelta(days=30)).isoformat(),'end':end.isoformat(),'index':'NIFTY 50','limit':2,'months':1}
    evidence={'at':now().isoformat(),'discovery':discovery,'cases':[],'complete':False}
    for capability in CAPABILITIES:
        case={'capability':capability,'name':CAPABILITIES[capability]}
        try:
            tool=gateway.registry.select(capability)
            arguments={target:{**tool.get('defaults',{}),**params}[source] for source,target in tool['args'].items()}
            async with asyncio.timeout(30):raw=await gateway.invoke(tool,arguments)
            adapted=adapt(tool,raw,params)
            from app.gateway import normalize
            observation=normalize(tool,adapted,params)
            case.update(method=tool['name'],schema_hash=tool['schema_hash'],payload_shape=shape(raw),raw_sha256=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest(),source_as_of=observation['source_as_of'],missing_fields=observation['missing_fields'],status=observation['status'],passed=not observation['missing_fields'])
        except Exception as exc:
            case.update(passed=False,status='BLOCKED',error_code=getattr(exc,'code',type(exc).__name__))
        evidence['cases'].append(case)
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(evidence,indent=2))
        print(json.dumps(case),flush=True)
    evidence['complete']=all(c['passed'] for c in evidence['cases'])
    output.write_text(json.dumps(evidence,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');parser.add_argument('--output',type=Path,default=Path('docs/capability-verification.json'));args=parser.parse_args()
    if not args.live:parser.error('Use --live to authorize bounded NSE calls')
    asyncio.run(verify(args.output))

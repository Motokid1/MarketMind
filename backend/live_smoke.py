"""Explicit opt-in, bounded live smoke. Persist statuses/lineage only, never market prices."""
import argparse
import asyncio
import json
from pathlib import Path
from app.gateway import Gateway, call_budget
from app.core import now
async def run():
    gateway=Gateway()
    discovery=await gateway.sync()
    cases=[('B01',{'q':'RELIANCE'}),('B02',{'symbol':'RELIANCE','start':'2026-09-01','end':'2026-10-09'}),('B11',{'end':'2026-10-09'}),('L04',{'symbol':'RELIANCE'}),('L02',{'index':'NIFTY 50'}),('L06',{'q':'RELI','limit':1})]
    result={'at':now().isoformat(),'discovery':discovery,'quota':6,'cases':[]}
    budget=call_budget.set({'used':0})
    try:
        for cap,params in cases:
            try:
                output=await gateway.call(cap,params)
                result['cases'].append({'capability':cap,'method':output['method'],'status':output['status'],'source_as_of':output['source_as_of'],'missing_fields':output['missing_fields'],'evidence_id':output['evidence_id'],'pass':not output['missing_fields']})
            except Exception as exc:
                result['cases'].append({'capability':cap,'status':'BLOCKED','type':type(exc).__name__,'error_code':getattr(exc,'code',None),'message':getattr(exc,'message',None),'pass':False})
    finally:
        call_budget.reset(budget)
    path=Path(__file__).resolve().parent/'docs/live-smoke.json'
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--live',action='store_true');args=parser.parse_args()
    if not args.live:parser.error('Live NSE calls require explicit --live')
    asyncio.run(run())

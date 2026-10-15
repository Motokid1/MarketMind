"""FR-007,008,009,012: decimal arithmetic, common sessions, no look-ahead."""
from decimal import Decimal, InvalidOperation
from math import sqrt
from statistics import stdev
from .core import DomainError

VERSION='decimal-session-v1'
def decimal(value):
    try:
        value=Decimal(str(value))
        if not value.is_finite():
            raise ValueError()
        return value
    except (InvalidOperation,ValueError):
        raise DomainError('INVALID_NUMERIC','Non-finite or invalid source number',502)
def bars(observation):
    if observation['value'] is None or observation['status']=='missing':
        return []
    output=[]; seen=set()
    for row in observation['value']:
        try:
            from datetime import date
            day=date.fromisoformat(row['date']).isoformat()
            if day in seen:
                raise DomainError('DUPLICATE_SESSION','Duplicate source trading session',502)
            seen.add(day)
            close=decimal(row['close']); volume=decimal(row['volume']) if row.get('volume') is not None else None
            if close<=0 or (volume is not None and volume<0):
                raise DomainError('INVALID_BAR','Prices must be positive and volume nonnegative',502)
            output.append({'date':day,'close':close,'volume':volume})
        except (KeyError,TypeError,ValueError):
            continue
    return sorted(output,key=lambda r:r['date'])
def metrics(series):
    if len(series)<2:
        return {'sample_size':len(series),'return_percent':None,'max_drawdown_percent':None,'annualized_volatility_percent':None,'moving_average_20':None,'volume_ratio':None,'baseline_sessions':0}
    prices=[r['close'] for r in series]
    changes=[prices[i]/prices[i-1]-1 for i in range(1,len(prices))]
    peak=prices[0]; drawdown=Decimal(0)
    for price in prices:
        peak=max(peak,price); drawdown=min(drawdown,price/peak-1)
    baseline=[r['volume'] for r in series[-21:-1]]
    valid_baseline=len(baseline)==20 and all(v is not None for v in baseline)
    mean=sum(baseline)/20 if valid_baseline else None
    return {'sample_size':len(series),'return_percent':str((prices[-1]/prices[0]-1)*100),'max_drawdown_percent':str(drawdown*100),'annualized_volatility_percent':str(stdev([float(r) for r in changes])*sqrt(252)*100) if len(changes)>1 else None,'moving_average_20':str(sum(prices[-20:])/20) if len(prices)>=20 else None,'volume_ratio':str(series[-1]['volume']/mean) if mean and series[-1]['volume'] is not None else None,'baseline_sessions':20 if valid_baseline else 0}
def compare(observations):
    parsed={o['instrument']:bars(o) for o in observations}
    sessions=set.intersection(*(set(r['date'] for r in rows) for rows in parsed.values())) if parsed else set()
    common=sorted(sessions)
    result=[]
    for observation in observations:
        symbol=observation['instrument']; eligible=[r for r in parsed[symbol] if r['date'] in sessions]
        result.append({'symbol':symbol,**metrics(eligible),'original_sample_size':len(parsed[symbol]),'missing_sessions':sorted(set().union(*(set(r['date'] for r in x) for x in parsed.values()))-set(r['date'] for r in parsed[symbol])),'evidence_ids':[observation['evidence_id']],'source_as_of':observation['source_as_of'],'units':'percent; INR for moving average; ratio for volume','formula_version':VERSION,'timeline':[{'date':r['date'],'normalized':str(r['close']/eligible[0]['close']*100)} for r in eligible]})
    return {'sessions':common,'sample_size':len(common),'metrics':result,'warnings':(['Insufficient common sessions'] if len(common)<2 else [])+[w for o in observations for w in o.get('warnings',[])],'methodology':'Inner join on returned trading dates; simple total return; peak-to-trough drawdown; sample volatility × sqrt(252); volume / prior 20 sessions mean. Unadjusted prices unless source says otherwise.'}
def portfolio(observations,weights,amount):
    aligned=compare(observations)
    if aligned['sample_size']<2:
        return {**aligned,'portfolio':None,'warnings':['Insufficient aligned history for risk']}
    # Buy-and-hold normalized wealth, not daily-rebalanced returns.
    curves=[m['timeline'] for m in aligned['metrics']]
    wealth=[sum(decimal(curves[j][i]['normalized'])/100*weights[j] for j in range(len(weights))) for i in range(aligned['sample_size'])]
    series=[{'date':day,'close':v,'volume':None} for day,v in zip(aligned['sessions'],wealth)]
    return {**aligned,'portfolio':{**metrics(series),'initial_amount_inr':str(amount),'final_amount_inr':str(amount*wealth[-1]),'concentration_hhi':str(sum(w*w for w in weights)),'weights':[str(w) for w in weights],'units':'INR; percent; HHI ratio','evidence_ids':[o['evidence_id'] for o in observations]},'methodology':aligned['methodology']+' Portfolio uses initial fractional allocations held throughout; HHI=sum(weight²). No fees or corporate-action adjustment assumed.'}

"""MCP-001 adapters for observed NSE responses. No cache timestamp masquerades as exchange time."""
from datetime import datetime, time
from zoneinfo import ZoneInfo
from .core import now,DomainError
from .analytics import decimal

IST=ZoneInfo('Asia/Kolkata')
def stamp(value):
    if not value or not isinstance(value,str):
        return None
    try:
        return datetime.fromisoformat(value.replace('Z','+00:00')).isoformat() if 'T' in value else None
    except ValueError:
        return None
def source_time(value):
    if not isinstance(value,str):
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S','%d-%b-%Y %H:%M:%S','%d-%b-%Y %H:%M'):
        try:
            return datetime.strptime(value,fmt).replace(tzinfo=IST).isoformat()
        except ValueError:
            pass
    if len(value)==10:
        try:
            # A daily observation has date precision. Time is session-close convention,
            # explicitly labeled separately; never inferred as an exchange tick.
            return datetime.combine(datetime.strptime(value,'%Y-%m-%d').date(),time(15,30),IST).isoformat()
        except ValueError:
            pass
    return stamp(value)
def market_state(as_of):
    if not as_of:
        return None
    current=now().astimezone(IST)
    previous=datetime.fromisoformat(as_of).astimezone(IST)
    outside=current.weekday()>4 or not time(9,15)<=current.time().replace(tzinfo=None)<=time(15,30)
    return 'closed' if outside else ('stale' if previous.date()!=current.date() else 'open')

def exchange_time(value):
    # Date-only observations cannot be promoted to fabricated current tick times.
    candidate=source_time(value) if isinstance(value,str) and len(value)>10 else None
    return candidate if candidate and datetime.fromisoformat(candidate).tzinfo is not None else None
def fields(record, mapping):
    return {target:record.get(source) for target,source in mapping.items()}
def validated_bars(rows,start,end):
    output=[]
    for row in rows:
        day=row.get('date')
        if not day or not start<=day<=end:
            continue
        normalized=fields(row,{'date':'date','open':'open','high':'high','low':'low','close':'close','volume':'volume','series':'series'})
        for key in ('open','high','low','close','volume'):
            if normalized[key] is not None:
                normalized[key]=str(decimal(normalized[key]))
        output.append(normalized)
    return output
def adapt(tool,payload,params):
    parser=tool['parser']; value=None; as_of=None; units=None; currency=None; state=None
    if not isinstance(payload,dict):
        # get_ltp_by_date returns a bare number with no source date. Fail closed.
        return {'value':None,'source_as_of':None,'units':None,'currency':None}
    if payload.get('error'):
        raise DomainError('UPSTREAM_ERROR','NSE returned an error response; no market observations available',502,True)
    if parser=='symbols':
        rows=payload.get('results',[])
        as_of=source_time(max((r.get('last_date') or '' for r in rows),default=''))
        # Lookup results may contain multiple series; preserve candidates to disambiguate.
        value=[{'symbol':r.get('symbol'),'segment':'equity','isin':None,'name':None,'series':r.get('series')} for r in rows]
        units='instruments'
    elif parser=='history':
        rows=payload.get('data',[])
        value=validated_bars(rows,params['start'],params['end'])
        as_of=source_time(max((r.get('date','') for r in value),default=''))
        units='OHLCV';currency='INR'
    elif parser=='historical_movers':
        as_of=source_time(payload.get('date'))
        value=[fields(r,{'symbol':'symbol','close':'close','change_percent':'pct_change','volume':'volume'}) for r in payload.get('stocks',[])]
        units='INR; percent; shares';currency='INR'
    elif parser=='breadth':
        as_of=source_time(payload.get('date'))
        value=fields(payload,{'advances':'advances','declines':'declines','unchanged':'unchanged','total_stocks':'total_stocks'})
        units='instruments'
    elif parser=='quote':
        row=payload.get('stock',{}) or {}
        as_of=exchange_time(row.get('latestTimestamp'))
        value=fields(row,{'symbol':'symbol','price':'lastTradedPrice','open':'openPrice','high':'highPrice','low':'lowPrice','previous_close':'preClosePrice','change':'change','change_percent':'perChange','volume':'volume','52_week_high':'fiftyTwoWeekHigh','52_week_low':'fiftyTwoWeekLow'}) if row else None
        if value is not None:
            for key in value:
                if key!='symbol' and value[key] is not None:value[key]=str(decimal(value[key]))
            if value['price'] is None:value=None
        units='INR; percent; shares';currency='INR';state=market_state(as_of)
    elif parser=='index':
        as_of=exchange_time(payload.get('nseTimestamp'))
        value=fields(payload.get('index',{}),{'index':'indexName','close':'last','change_percent':'percChange','open':'open','high':'high','low':'low'})
        for key in value:
            if key!='index' and value[key] is not None:value[key]=str(decimal(value[key]))
        if value['close'] is None:value=None
        units='index points; percent';state=market_state(as_of)
    elif parser=='listing':
        rows=payload.get('stocks',[])
        # Listing freshness is cache metadata, not a quote timestamp; only identifiers retained.
        as_of=stamp(payload.get('updatedAt'))
        segment={'L03':'sme','L06':'equity','L07':'bond'}[tool['capability']]
        value=[{'symbol':r.get('symbol'),'segment':segment,'isin':r.get('isin'),'name':r.get('name'),'series':r.get('series')} for r in rows if params.get('q','').upper() in r.get('symbol','')]
        units='instrument identifiers'
    elif parser=='freshness':
        entries=payload.get('indices',{})
        as_of=max((stamp(v.get('lastCrawled')) or '' for v in entries.values()),default='') or None
        value={'source_cache':entries,'market_status':'closed' if market_state(as_of)=='closed' else 'unknown'}
        units='cache status';state=market_state(as_of)
    elif parser=='current_movers':
        # Accept exchange-stamped stock records only. Crawl time is insufficient.
        as_of=exchange_time(payload.get('nseTimestamp'))
        rows=payload.get('stocks')
        if isinstance(rows,list) and all(isinstance(row,dict) for row in rows):
            times=[exchange_time(row.get('latestTimestamp')) for row in rows]
            if any(stamp and datetime.fromisoformat(stamp)>now() for stamp in times):
                raise DomainError('INVALID_SOURCE_TIME','Mover observation contains a future source timestamp',502)
            if not as_of and times and all(times):
                as_of=min(times,key=lambda stamp:datetime.fromisoformat(stamp))
            if as_of:
                value=[]
                for row in rows:
                    price=row.get('lastTradedPrice',row.get('price'))
                    change=row.get('perChange',row.get('change_percent'))
                    if not isinstance(row.get('symbol'),str) or price is None or change is None:
                        raise DomainError('OUTPUT_SCHEMA_CHANGED','Movers lack required symbol, price or change fields',502)
                    value.append({'symbol':row['symbol'],'price':str(decimal(price)),'change_percent':str(decimal(change)),'volume':str(decimal(row['volume'])) if row.get('volume') is not None else None,'source_as_of':times[len(value)] or as_of})
        units='INR; percent; shares';state=market_state(as_of)
    return {'value':value,'source_as_of':as_of,'units':units,'currency':currency,'market_status':state,'next_end_date':payload.get('next_end_date'),'source_precision':'session date (15:30 IST close convention)' if tool['service']=='bhavcopy' else 'exchange timestamp' if parser in ('quote','index','current_movers') else 'cache metadata'}

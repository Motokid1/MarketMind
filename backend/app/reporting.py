"""Escaped, readable research exports with linked quantitative evidence."""
import html
import json

def render_report(run):
    result=run.result or {}
    final=result.get('final',{})
    def escape(value):
        return html.escape(str(value),quote=True)
    rows=[]
    for claim in final.get('claims',[]):
        links=' '.join(f'<a href="#evidence-{escape(ref)}">{escape(ref[:12])}</a>' for ref in claim.get('evidence_ids',[]))
        rows.append('<tr>'+''.join(f'<td>{escape(claim.get(key,"Unavailable"))}</td>' for key in ('symbol','metric','value','units','source_as_of','formula_version'))+f'<td>{links}</td></tr>')
    evidence=[]
    for item in result.get('evidence',[]):
        evidence.append(f'<li id="evidence-{escape(item.get("evidence_id",""))}"><strong>{escape(item.get("instrument") or item.get("service"))}</strong> · {escape(item.get("method"))}<br>source_as_of: {escape(item.get("source_as_of"))} · received_at: {escape(item.get("received_at"))}<br>evidence_id: {escape(item.get("evidence_id"))} · {escape(item.get("status"))}</li>')
    warnings=''.join(f'<li>{escape(w)}</li>' for w in result.get('warnings',[]))
    return '<!doctype html><html lang="en"><meta charset="utf-8"><title>MarketMind research report</title><style>body{font:15px system-ui;color:#332b39;background:#fffdfb;max-width:1100px;margin:40px auto;padding:24px}h1,h2,a{color:#62435f}table{border-collapse:collapse;width:100%}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}th{background:#eee7ee}li{margin:14px 0;overflow-wrap:anywhere}pre{white-space:pre-wrap;overflow-wrap:anywhere}.scroll{overflow:auto}</style><h1>MarketMind research report</h1><p>Trace ID: '+escape(run.id)+'</p><p>'+escape(final.get('summary','No verified findings available.'))+'</p><h2>Key findings</h2><div class="scroll"><table><tr><th>Symbol</th><th>Metric</th><th>Value</th><th>Units</th><th>As of</th><th>Formula</th><th>Evidence</th></tr>'+(''.join(rows) or '<tr><td colspan="7">No verified quantitative claims available.</td></tr>')+'</table></div><h2>Coverage and limitations</h2><ul>'+warnings+'</ul><h2>Dated evidence</h2><ul>'+''.join(evidence)+'</ul><p>'+escape(final.get('disclaimer','Educational use only.'))+'</p><details><summary>Complete calculation and provenance record</summary><pre>'+escape(json.dumps(result,indent=2,default=str))+'</pre></details></html>'

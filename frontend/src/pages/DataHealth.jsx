import {useEffect,useState} from 'react'
import {getHealth,getQuality,getRuns,getFeatureImportance} from '../api'
export default function DataHealth(){
 const [h,setH]=useState(null),[q,setQ]=useState(null),[runs,setRuns]=useState([]),[fi,setFi]=useState([])
 useEffect(()=>{Promise.all([getHealth(),getQuality(),getRuns(),getFeatureImportance()]).then(([a,b,c,d])=>{setH(a);setQ(b);setRuns(c);setFi(d)})},[])
 return <div className="page"><div className="page-head"><div><div className="eyebrow">SYSTEM ASSURANCE</div><h1>Data & model health</h1><p>Judge-ready visibility into source connectivity, data quality, ingestion history and the model's strongest features.</p></div></div>
 <div className="health-grid"><div className="health-card"><h3>Source status</h3><Status label="NASA FIRMS" ok={h?.firms_configured} detail={h?.firms_configured?'MAP_KEY configured':'MAP_KEY required'}/><Status label="Satellite STAC" ok={h?.satellite_configured} detail={h?.satellite_configured?'Connected adapter':'Optional: configure endpoint'}/><Status label="Backend API" ok={h?.status==='ok'} detail={h?.status==='ok'?'Operational':'Unavailable'}/><div className="mode-banner">Current data mode: <b>{h?.mode||'—'}</b></div></div>
 <div className="health-card"><h3>Quality checks</h3>{q&&Object.entries(q).filter(([k])=>k!=='missing_critical_fields').map(([k,v])=><div className="quality-row" key={k}><span>{k.replaceAll('_',' ')}</span><b>{typeof v==='object'?JSON.stringify(v):v}</b></div>)}</div>
 <div className="health-card wide"><h3>Model feature importance</h3><div className="importance-list">{fi.map(x=><div key={x.feature}><span>{x.feature}</span><i><em style={{width:`${Math.min(100,x.importance*1000)}%`}}/></i><b>{(x.importance*100).toFixed(2)}%</b></div>)}</div></div>
 <div className="health-card wide"><h3>Ingestion history</h3><div className="run-list">{runs.length?runs.map(r=><div key={r.id}><b>{r.source}</b><span>{r.rows_ingested} new rows</span><span>{r.status}</span><small>{new Date(r.created_at).toLocaleString()}</small></div>):<p>No ingestion runs yet.</p>}</div></div></div></div>
}
function Status({label,ok,detail}){return <div className="status-row"><span className={ok?'status-dot ok':'status-dot'}/><div><b>{label}</b><small>{detail}</small></div><strong>{ok?'READY':'SETUP'}</strong></div>}

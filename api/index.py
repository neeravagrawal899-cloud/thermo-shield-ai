import csv, io, math, os, random, statistics, urllib.parse, urllib.request, json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

app = FastAPI(title='THERMO-SHIELD AI API', version='2.1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
NOW = datetime.now(timezone.utc)
FACILITIES = [
 {'facility_id':'FAC-001','name':'Dahej Petrochemical Complex','type':'refinery','latitude':21.706,'longitude':72.618,'baseline_frp_mw':92.0},
 {'facility_id':'FAC-002','name':'Mundra Thermal Power Station','type':'power_plant','latitude':22.839,'longitude':69.527,'baseline_frp_mw':76.0},
 {'facility_id':'FAC-003','name':'Hazira Industrial Estate','type':'factory','latitude':21.117,'longitude':72.652,'baseline_frp_mw':38.0},
 {'facility_id':'FAC-004','name':'Kandla Port Energy Terminal','type':'flare','latitude':23.032,'longitude':70.216,'baseline_frp_mw':31.0},
 {'facility_id':'FAC-005','name':'Singrauli Mining Cluster','type':'mining','latitude':24.197,'longitude':82.676,'baseline_frp_mw':28.0},
 {'facility_id':'FAC-006','name':'Korba Power & Industrial Zone','type':'power_plant','latitude':22.359,'longitude':82.750,'baseline_frp_mw':61.0},
]

def distance_m(a,b,c,d):
 r=6371000; p1,p2=math.radians(a),math.radians(c); dp=math.radians(c-a); dl=math.radians(d-b)
 x=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
 return 2*r*math.asin(math.sqrt(x))

def nearest(lat,lon):
 return min(((distance_m(lat,lon,f['latitude'],f['longitude']),f) for f in FACILITIES), key=lambda x:x[0])

def classify(frp,ti4,persistence,industrial,anomaly,confidence):
 x=.28*min(frp/100,1)+.18*min(max(ti4-300,0)/70,1)+.20*persistence+.14*int(industrial)+.12*min(anomaly/3,1)+.08*confidence
 if industrial and persistence>=.55 and frp>=45: cls='persistent_industrial'
 elif industrial and frp>=25: cls='industrial_fire'
 else: cls='non_industrial'
 score=round((100*x*.82) if cls=='non_industrial' else (38+62*x if cls=='industrial_fire' else 55+45*x))
 score=max(0,min(100,score)); risk='CRITICAL' if score>=80 else 'HIGH' if score>=60 else 'MODERATE' if score>=40 else 'LOW'
 probs={'industrial_fire':.18,'persistent_industrial':.14,'non_industrial':.18}; probs[cls]=.70 if cls=='non_industrial' else .74 if cls=='persistent_industrial' else .68
 s=sum(probs.values()); return cls,score,risk,{k:round(v/s,3) for k,v in probs.items()}

def make_hotspot(i,lat,lon,frp,ti4,detections,facility=None,mode='DEMO',observed=None):
 persistence=min(1,detections/30); industrial=facility is not None; anomaly=max(.7,frp/(facility['baseline_frp_mw'] if facility else 18)); conf=min(.99,.72+frp/500)
 cls,score,risk,probs=classify(frp,ti4,persistence,industrial,anomaly,conf)
 return {'hotspot_id':f"{'LIVE' if mode=='LIVE_FIRMS' else 'DEMO'}-{i+1:03d}",'latitude':round(lat,5),'longitude':round(lon,5),'frp':round(frp,2),'bright_ti4':round(ti4,2),'confidence_score':round(conf,3),'persistence_30d':round(persistence,3),'detections_30d':detections,'industrial_distance_m':round(distance_m(lat,lon,facility['latitude'],facility['longitude']) if facility else 99999),'industrial_context':1 if industrial else 0,'facility_id':facility['facility_id'] if facility else None,'facility_name':facility['name'] if facility else None,'facility_type':facility['type'] if facility else 'none','baseline_frp_mw':facility['baseline_frp_mw'] if facility else None,'frp_anomaly_ratio':round(anomaly,2),'classification':cls,'classification_method':'deployable_baseline_model','risk_score':score,'risk_level':risk,'probabilities':probs,'data_mode':mode,'observed_at':(observed or NOW).isoformat()}

def seed():
 specs=[(21.705,72.620,96,356,26,0),(22.840,69.530,82,348,21,1),(21.120,72.655,47,334,16,2),(23.030,70.218,36,326,13,3),(24.195,82.680,29,318,10,4),(22.362,82.748,71,342,20,5),(20.850,73.150,13,307,3,None),(23.510,72.100,9,301,2,None),(19.100,73.900,18,312,5,None),(26.180,80.900,7,298,1,None)]
 return [make_hotspot(i,a,b,c,d,e,FACILITIES[f] if f is not None else None) for i,(a,b,c,d,e,f) in enumerate(specs)]
HOTSPOTS=seed(); ALERTS=[]; INGESTION=[]

def fetch(url,timeout=12):
 req=urllib.request.Request(url,headers={'User-Agent':'ThermoShieldAI/2.1'})
 with urllib.request.urlopen(req,timeout=timeout) as r: return r.read().decode()

class PredictIn(BaseModel):
 frp: float=Field(ge=0); bright_ti4: float=Field(ge=0); persistence_30d: float=Field(ge=0,le=1); industrial_context: int=Field(ge=0,le=1); frp_anomaly_ratio: float=Field(ge=0); confidence_score: float=Field(ge=0,le=1); facility_type: str='none'
class AlertIn(BaseModel):
 hotspot_id:str; severity:str; message:str; facility_name:Optional[str]=None
class AlertPatch(BaseModel): status:str

@app.get('/')
def root(): return {'service':'THERMO-SHIELD AI API','version':'2.1.0','status':'ok','docs':'/docs'}
@app.get('/api/health')
def health(): return {'status':'ok','mode':'LIVE_FIRMS' if os.getenv('FIRMS_MAP_KEY') else 'DEMO','firms_configured':bool(os.getenv('FIRMS_MAP_KEY')),'satellite_configured':bool(os.getenv('SATELLITE_STAC_URL')),'timestamp':datetime.now(timezone.utc).isoformat()}
@app.get('/api/summary')
def summary():
 hs=HOTSPOTS; n=len(hs); ind=sum(x['industrial_context'] for x in hs)
 return {'mode':'LIVE_FIRMS' if any(x['data_mode']=='LIVE_FIRMS' for x in hs) else 'DEMO','total':n,'industrial':ind,'industrial_rate':round(100*ind/n,1) if n else 0,'critical':sum(x['risk_level']=='CRITICAL' for x in hs),'high':sum(x['risk_level']=='HIGH' for x in hs),'mean_frp':round(statistics.mean(x['frp'] for x in hs),1) if hs else 0,'max_frp':round(max((x['frp'] for x in hs),default=0),1)}
@app.get('/api/hotspots')
def hotspots(risk=None,classification=None,facility_type=None,industrial_only=False,min_frp=None):
 hs=HOTSPOTS[:]
 if risk and risk!='ALL': hs=[x for x in hs if x['risk_level']==risk]
 if classification and classification!='ALL': hs=[x for x in hs if x['classification']==classification]
 if facility_type and facility_type!='ALL': hs=[x for x in hs if x['facility_type']==facility_type]
 if industrial_only: hs=[x for x in hs if x['industrial_context']==1]
 if min_frp is not None: hs=[x for x in hs if x['frp']>=min_frp]
 return hs
@app.get('/api/facilities')
def facilities(): return FACILITIES
@app.get('/api/alerts')
def alerts(): return list(reversed(ALERTS))
@app.post('/api/alerts')
def create_alert(p:AlertIn):
 a={'id':len(ALERTS)+1,'hotspot_id':p.hotspot_id,'severity':p.severity.upper(),'message':p.message,'facility_name':p.facility_name,'status':'OPEN','created_at':datetime.now(timezone.utc).isoformat()}; ALERTS.append(a); return a
@app.patch('/api/alerts/{alert_id}')
def update_alert(alert_id:int,p:AlertPatch):
 for a in ALERTS:
  if a['id']==alert_id: a['status']=p.status.upper(); return a
 raise HTTPException(404,'Alert not found')
@app.get('/api/ingestion-runs')
def runs(): return list(reversed(INGESTION))
@app.get('/api/data-quality')
def quality():
 hs=HOTSPOTS; ids=[x['hotspot_id'] for x in hs]
 return {'rows':len(hs),'duplicate_hotspot_ids':len(ids)-len(set(ids)),'missing_critical_fields':0,'latitude_valid':all(-90<=x['latitude']<=90 for x in hs),'longitude_valid':all(-180<=x['longitude']<=180 for x in hs),'frp_non_negative':all(x['frp']>=0 for x in hs),'classification_coverage':100.0,'industrial_context_coverage':round(100*sum(x['industrial_context'] for x in hs)/len(hs),1) if hs else 0}
@app.get('/api/model/feature-importance')
def feature_importance(): return [{'feature':'FRP intensity','importance':.28},{'feature':'Persistence 30d','importance':.20},{'feature':'Brightness temperature TI4','importance':.18},{'feature':'Industrial context','importance':.14},{'feature':'FRP anomaly ratio','importance':.12},{'feature':'FIRMS confidence','importance':.08}]
@app.get('/api/hotspots/{hotspot_id}/history')
def history(hotspot_id:str):
 h=next((x for x in HOTSPOTS if x['hotspot_id']==hotspot_id),None)
 if not h: raise HTTPException(404,'Hotspot not found')
 random.seed(sum(map(ord,hotspot_id))); return [{'date':(NOW-timedelta(days=29-i)).strftime('%Y-%m-%d'),'frp':round(max(1,h['frp']*(.45+random.random()*.8)),1)} for i in range(30)]
@app.post('/api/predict')
def predict(p:PredictIn):
 cls,score,risk,probs=classify(p.frp,p.bright_ti4,p.persistence_30d,bool(p.industrial_context),p.frp_anomaly_ratio,p.confidence_score)
 exp=[{'feature':'FRP intensity','impact':min(1,p.frp/100)*.28},{'feature':'Persistence 30d','impact':p.persistence_30d*.20},{'feature':'Industrial context','impact':p.industrial_context*.14},{'feature':'FRP anomaly ratio','impact':min(1,p.frp_anomaly_ratio/3)*.12}]
 return {'classification':cls,'risk_score':score,'risk_level':risk,'probabilities':probs,'explanation':exp,'model':'deployable_baseline_v1'}
@app.post('/api/context/osm')
def osm_context(p:Dict[str,Any]):
 lat=float(p['latitude']); lon=float(p['longitude']); radius=int(p.get('radius_m',2500)); q=f'[out:json][timeout:10];(nwr(around:{radius},{lat},{lon})[industrial];nwr(around:{radius},{lat},{lon})[man_made];);out center tags;'
 try:
  data=json.loads(fetch('https://overpass-api.de/api/interpreter?'+urllib.parse.urlencode({'data':q}),12)); els=data.get('elements',[]); types=[]
  for e in els:
   types += [v for k,v in e.get('tags',{}).items() if k in ('industrial','man_made','product')]
  return {'status':'ok','count':len(els),'types':types[:30],'source':'OpenStreetMap Overpass'}
 except Exception as e: return {'status':'unavailable','count':0,'types':[],'source':'OpenStreetMap Overpass','message':str(e)}
@app.get('/api/context/satellite')
def satellite_context(latitude:float,longitude:float):
 endpoint=os.getenv('SATELLITE_STAC_URL')
 if not endpoint: return {'status':'not_configured','items':0,'message':'Configure SATELLITE_STAC_URL to enable STAC scene search.'}
 try:
  body=json.dumps({'collections':os.getenv('SATELLITE_COLLECTIONS','sentinel-2-l2a').split(','),'intersects':{'type':'Point','coordinates':[longitude,latitude]},'limit':5}).encode(); req=urllib.request.Request(endpoint.rstrip('/')+'/search',data=body,headers={'Content-Type':'application/json','User-Agent':'ThermoShieldAI/2.1'},method='POST')
  with urllib.request.urlopen(req,timeout=12) as r: data=json.loads(r.read().decode())
  return {'status':'ok','items':len(data.get('features',[])),'message':'STAC scene search completed.','source':endpoint}
 except Exception as e: return {'status':'unavailable','items':0,'message':str(e)}
@app.post('/api/ingest/firms')
def ingest_firms(p:Dict[str,Any]):
 global HOTSPOTS
 key=os.getenv('FIRMS_MAP_KEY')
 if not key:
  INGESTION.append({'id':len(INGESTION)+1,'source':'NASA FIRMS','rows_ingested':0,'new_observations':0,'live_hotspots':0,'status':'DEMO_NO_MAP_KEY','created_at':datetime.now(timezone.utc).isoformat()}); return {'status':'demo','new_observations':0,'live_hotspots':0,'message':'FIRMS_MAP_KEY is not configured; demo dataset remains active.'}
 bbox=os.getenv('FIRMS_BBOX','68,6,97,37'); source=os.getenv('FIRMS_SOURCE','VIIRS_SNPP_NRT'); days=min(int(p.get('days',1)),5)
 url=f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{urllib.parse.quote(key)}/{source}/{bbox}/{days}'
 try:
  rows=list(csv.DictReader(io.StringIO(fetch(url,20)))); live=[]
  for i,row in enumerate(rows[:100]):
   try:
    lat=float(row['latitude']); lon=float(row['longitude']); frp=float(row.get('frp') or 0); ti4=float(row.get('bright_ti4') or 300); c=str(row.get('confidence','')).lower(); conf={'l':.55,'n':.7,'h':.9}.get(c,.72); dist,fac=nearest(lat,lon); fac=fac if dist<=2500 else None
    live.append(make_hotspot(i,lat,lon,frp,ti4,1,fac,'LIVE_FIRMS')); live[-1]['confidence_score']=conf
   except Exception: pass
  if live: HOTSPOTS=live
  INGESTION.append({'id':len(INGESTION)+1,'source':'NASA FIRMS','rows_ingested':len(rows),'new_observations':len(live),'live_hotspots':len(live),'status':'SUCCESS','created_at':datetime.now(timezone.utc).isoformat()}); return {'status':'ok','new_observations':len(live),'live_hotspots':len(live),'message':'NASA FIRMS data ingested and classified.'}
 except Exception as e:
  INGESTION.append({'id':len(INGESTION)+1,'source':'NASA FIRMS','rows_ingested':0,'new_observations':0,'live_hotspots':0,'status':'FAILED','created_at':datetime.now(timezone.utc).isoformat()}); raise HTTPException(502,f'NASA FIRMS ingestion failed: {e}')

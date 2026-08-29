import {MapContainer,TileLayer,CircleMarker,Popup,Marker} from 'react-leaflet'
import L from 'leaflet'
const riskColor={CRITICAL:'#ff3b30',HIGH:'#ff8a00',MODERATE:'#f4c542',LOW:'#35c46a'}
const icon=L.divIcon({className:'facility-pin',html:'◆',iconSize:[16,16],iconAnchor:[8,8]})
export default function MapView({hotspots,facilities,onSelect}){
 const center=[21.2,72.83]
 return <MapContainer center={center} zoom={6} className="map"><TileLayer attribution='&copy; OpenStreetMap contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
 {facilities.map(f=><Marker key={f.facility_id} position={[f.latitude,f.longitude]} icon={icon}><Popup><b>{f.name}</b><br/>{f.type}<br/>Baseline FRP: {f.baseline_frp_mw} MW</Popup></Marker>)}
 {hotspots.map(h=><CircleMarker key={h.hotspot_id} center={[h.latitude,h.longitude]} radius={Math.max(5,Math.min(13,h.risk_score/7))} pathOptions={{color:riskColor[h.risk_level]||'#fff',fillColor:riskColor[h.risk_level]||'#fff',fillOpacity:.78,weight:2}} eventHandlers={{click:()=>onSelect(h)}}><Popup><b>{h.hotspot_id}</b><br/>{h.classification.replaceAll('_',' ')}<br/>Risk {h.risk_score}</Popup></CircleMarker>)}
 </MapContainer>
}

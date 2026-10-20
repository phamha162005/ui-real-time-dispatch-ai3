"use strict";
(function(){
 const q=id=>document.getElementById(id);
 const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const references={'KCN Sóng Thần':[10.901,106.745],'Cảng Cát Lái':[10.758,106.790]};
 const coordinatesKey='ui-dispatch-map-coordinates-v1',viewKey='dispatch-map-view-v2';
 let stored={},savedView;try{stored=JSON.parse(localStorage.getItem(coordinatesKey)||'{}')||{};savedView=JSON.parse(localStorage.getItem(viewKey)||'null');}catch(_){}
 let lastGPSView=savedView;
 let map,routeLayer,gpsLayer,trips=[],gps=[],mode='gps',loading=false,epoch=0,selectedVehicle='',fitOnFirstLoad=!savedView,signature='',lastGpsSignature='';
 const key=t=>JSON.stringify([t.id,t.origin,t.destination]);
 function validPoint(p){return Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=90&&Math.abs(p[1])<=180;}
 function parseCoordinate(v){const parts=v.trim().split(',').map(x=>x.trim());if(parts.length!==2||parts.some(x=>x===''))return null;const p=parts.map(Number);return validPoint(p)?p:null;}
 function point(t,side){const p=stored[key(t)]?.[side];return validPoint(p)?p:references[t[side]]||null;}
 function status(r){const age=(Date.now()-new Date(r.source_updated_at).getTime())/60000;return age>5||age<0?'stale':r.speed_kmh===0?'stopped':'moving';}
 const labels={moving:'Di chuyển',stopped:'Dừng',stale:'Dữ liệu cũ'};
 function filteredGPS(records,query,filter){return records.filter(r=>String(r.vehicle_id).toLocaleLowerCase().includes(query.toLocaleLowerCase())&&(filter==='all'||status(r)===filter));}
 function visible(){return filteredGPS(gps,q('mapSearch').value.trim(),q('mapFilter').value);}
 function stamp(value){return new Date(value).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour12:false});}
 function ageLabel(r){const m=Math.floor((Date.now()-new Date(r.source_updated_at).getTime())/60000);return m<0?'Giờ nguồn cần kiểm tra':m===0?'Vừa ghi nhận':m<60?m+' phút trước':Math.floor(m/60)+' giờ '+m%60+' phút trước';}
 function init(){
  if(map)return true;
  if(!window.L){q('mapStatus').textContent='Chưa tải được bản đồ. Vui lòng tải lại trang.';return false;}
  const restored=savedView&&validPoint(savedView.center)&&Number.isFinite(savedView.zoom)&&savedView.zoom>=3&&savedView.zoom<=19;
  map=L.map('dispatchMap',{scrollWheelZoom:false,zoomControl:true,zoomAnimation:false,markerZoomAnimation:false}).setView(restored?savedView.center:[10.84,106.78],restored?savedView.zoom:10);
  let good=false;L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,minZoom:3,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'})
   .on('tileload',()=>{good=true;q('mapStatus').textContent=mode==='gps'?'Vị trí tại lần ghi nhận GPS gần nhất':'A: Điểm lấy · B: Điểm giao';})
   .on('tileerror',()=>{if(!good)q('mapStatus').textContent='Chưa tải được nền bản đồ. Kiểm tra Internet.';}).addTo(map);
  routeLayer=L.featureGroup().addTo(map);gpsLayer=L.featureGroup().addTo(map);
  map.on('moveend',()=>{if(mode!=='gps')return;const c=map.getCenter();lastGPSView={center:[c.lat,c.lng],zoom:map.getZoom()};try{localStorage.setItem(viewKey,JSON.stringify(lastGPSView));}catch(_){}});
  map.on('zoomend',()=>{if(mode==='gps')drawGPS();});
  new ResizeObserver(()=>map.invalidateSize()).observe(q('dispatchMap'));return true;
 }
 const truck='<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M3 5h11v11H3zM15 9h4l3 4v3h-7z"/><circle cx="7" cy="18" r="2" fill="currentColor"/><circle cx="18" cy="18" r="2" fill="currentColor"/></svg>';
 function popup(r){return `<div class="vehicle-popup"><strong>${safe(r.vehicle_id)}</strong><span class="gps-state ${status(r)}">${labels[status(r)]}</span><p>${r.speed_kmh} km/h · ${safe(ageLabel(r))}</p><p>Ghi nhận ${safe(stamp(r.source_updated_at))} (VN)</p><small>${r.ingestion_method==='file'?'Tệp GPS đã nhập':'Lần đọc API đã lưu'} · ${r.latitude}, ${r.longitude}</small></div>`;}
 function focusVehicle(id){
  selectedVehicle=id;const r=gps.find(x=>x.vehicle_id===id);if(!r||!init())return;
  drawList();map.setView([r.latitude,r.longitude],Math.max(14,map.getZoom()),{animate:false});
  L.popup().setLatLng([r.latitude,r.longitude]).setContent(popup(r)).openOn(map);
 }
 function drawList(){
  const rows=visible();q('mapFleetCount').textContent=rows.length+' / '+gps.length+' xe'+(rows.length>100?' · Hiển thị 100 xe đầu':'');
  q('mapVehicleList').innerHTML=rows.length?rows.slice(0,100).map(r=>`<button type="button" class="map-vehicle-row ${selectedVehicle===r.vehicle_id?'selected':''}" data-map-vehicle="${safe(r.vehicle_id)}" aria-pressed="${selectedVehicle===r.vehicle_id}"><span class="map-truck-icon ${status(r)}">${truck}</span><span><b>${safe(r.vehicle_id)}</b><small>${safe(ageLabel(r))}</small></span><span class="vehicle-row-state"><i class="${status(r)}-dot"></i>${labels[status(r)]}<small>${r.speed_kmh} km/h</small></span></button>`).join(''):`<div class="map-empty"><span aria-hidden="true"><svg viewBox="0 0 24 24" width="38" height="38" fill="none" stroke="currentColor" stroke-width="1.4"><circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2"/><path d="M12 1v4m0 14v4M1 12h4m14 0h4"/></svg></span><b>${gps.length?'Không tìm thấy xe':'Chưa có vị trí GPS'}</b><p>${gps.length?'Thử từ khóa hoặc trạng thái khác.':'Kết nối nguồn GPS hoặc nhập tệp để xem xe trên bản đồ.'}</p>${gps.length?'<button class="text-link" type="button" id="mapClearFilter">Xóa bộ lọc</button>':'<a class="text-link" href="#enterprise" data-enterprise-source="GPS">Kết nối GPS →</a>'}</div>`;
 }
 function drawGPS(){
  if(mode!=='gps'||!init())return;gpsLayer.clearLayers();
  // Group icons in the same screen cell to keep dense fleets readable.
  const groups=new Map();for(const r of visible()){
   const p=map.project([r.latitude,r.longitude],map.getZoom()),k=Math.floor(p.x/44)+':'+Math.floor(p.y/44);
   if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r);
  }
  for(const group of groups.values()){
   if(group.length===1){const r=group[0],icon=L.divIcon({className:'fleet-vehicle-pin '+status(r),html:truck,iconSize:[34,34],iconAnchor:[17,17]});
    L.marker([r.latitude,r.longitude],{icon,title:r.vehicle_id}).bindPopup(popup(r)).on('click',()=>{selectedVehicle=r.vehicle_id;drawList();}).addTo(gpsLayer);
   }else{
    const lat=group.reduce((n,r)=>n+r.latitude,0)/group.length,lng=group.reduce((n,r)=>n+r.longitude,0)/group.length;
    const icon=L.divIcon({className:'fleet-cluster',html:'<span>'+group.length+'</span>',iconSize:[40,40]});
    L.marker([lat,lng],{icon,title:group.length+' xe trong khu vực'}).on('click',()=>map.fitBounds(group.map(r=>[r.latitude,r.longitude]),{padding:[60,60],maxZoom:Math.min(19,map.getZoom()+3)})).addTo(gpsLayer);
   }
  }
 }
 function fitGPS(){const rows=visible();if(rows.length&&init())map.fitBounds(rows.map(r=>[r.latitude,r.longitude]),{padding:[45,45],maxZoom:15});}
 async function loadGPS(force=false){
  if(loading)return;loading=true;const generation=epoch,controller=new AbortController(),timer=setTimeout(()=>controller.abort(),12000);
  if(!gps.length)q('mapGpsStatus').textContent='Đang lấy vị trí xe…';
  try{
   const response=await fetch('/api/enterprise/GPS/data',{signal:controller.signal});if(!response.ok)throw Error();
   const result=await response.json();if(generation!==epoch)return;
   gps=(result.records||[]).filter(r=>validPoint([r.latitude,r.longitude]));
   const next=JSON.stringify(gps.map(r=>[r.vehicle_id,r.latitude,r.longitude,r.speed_kmh,r.source_updated_at,status(r),ageLabel(r)]));
   if(next!==lastGpsSignature||force){lastGpsSignature=next;drawList();if(mode==='gps')drawGPS();}
   q('mapGpsStatus').textContent=gps.length?`${gps.length} xe có vị trí${result.total_count>gps.length?' · Tối đa 1.000 xe':''} · Cập nhật kho GPS mỗi 15 giây · Bấm xe để xem thời điểm nguồn.`:'Chưa có dữ liệu GPS. Các điểm lấy/giao vẫn xem được ở tab bên cạnh.';
   if(fitOnFirstLoad&&gps.length&&mode==='gps'&&!q('page-dashboard').hidden){fitOnFirstLoad=false;fitGPS();}
  }catch(_){if(generation===epoch){gps=[];lastGpsSignature='';gpsLayer?.clearLayers();drawList();q('mapGpsStatus').textContent='Không tải được GPS. Bấm ↻ để thử lại.';}}
  finally{clearTimeout(timer);loading=false;}
 }
 function drawRoute(fit=false){
  if(mode!=='route'||!init())return;routeLayer.clearLayers();const t=trips.find(t=>String(t.id)===q('mapTrip').value);
  q('googleDirections').hidden=!t;q('mapCoordinates').hidden=!t;if(!t){q('mapStatus').textContent='Chưa có chuyến xe.';return;}
  const origin=point(t,'origin'),destination=point(t,'destination'),url=new URL('https://www.google.com/maps/dir/');
  url.search=new URLSearchParams({api:'1',origin:origin?origin.join(','):t.origin+', Việt Nam',destination:destination?destination.join(','):t.destination+', Việt Nam',travelmode:'driving'}).toString();q('googleDirections').href=url.href;
  q('mapOrigin').value=origin?.join(', ')||'';q('mapDestination').value=destination?.join(', ')||'';
  q('mapLocationNote').textContent=stored[key(t)]?'Dùng tọa độ đã lưu trên trình duyệt.':origin||destination?'Tọa độ tham chiếu khu vực; có thể chỉnh đúng cổng kho/cảng.':'Chưa xác định tọa độ. Nhập vị trí hoặc mở Google Maps để tìm địa chỉ.';
  [['origin',origin,'A',t.origin],['destination',destination,'B',t.destination]].forEach(([side,p,label,name])=>{if(!p)return;const icon=L.divIcon({className:'map-pin '+side,html:label,iconSize:[32,32],iconAnchor:[16,16]});L.marker(p,{icon,title:name}).bindPopup(`<b>${label==='A'?'Điểm lấy':'Điểm giao'}</b><br>${safe(name)}<br>${safe(t.code)}<br><small>Địa điểm giao nhận, không phải vị trí xe.</small>`).addTo(routeLayer);});
  q('mapStatus').textContent='A: Điểm lấy · B: Điểm giao · Mở Google Maps để xem tuyến đường';
  if(fit){const ps=[origin,destination].filter(Boolean);if(ps.length)map.fitBounds(ps,{padding:[45,45],maxZoom:13});}
 }
 function setMode(next){
  const restoreView=lastGPSView;mode=next;document.querySelectorAll('[data-map-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mapMode===mode)));
  q('mapFleetPanel').hidden=mode!=='gps';q('mapRouteControls').hidden=mode!=='route';q('mapRouteSettings').hidden=mode!=='route';q('mapKey').hidden=mode!=='gps';q('mapGpsStatus').hidden=mode!=='gps';q('mapReload').hidden=mode!=='gps';q('googleDirections').hidden=mode!=='route';
  q('mapFit').textContent=mode==='gps'?'Xem tất cả':'Xem hai điểm';
  if(init()){routeLayer.clearLayers();gpsLayer.clearLayers();map.invalidateSize();}
  if(mode==='gps'){if(restoreView&&validPoint(restoreView.center)&&Number.isFinite(restoreView.zoom))map.setView(restoreView.center,restoreView.zoom,{animate:false});else if(gps.length)fitGPS();drawList();drawGPS();q('mapStatus').textContent='Vị trí tại lần ghi nhận GPS gần nhất';loadGPS();}else drawRoute(true);
 }
 function update(rows){
  trips=rows;const next=JSON.stringify(rows.map(t=>[t.id,t.code,t.origin,t.destination,t.vehicle_id]));
  if(next!==signature){signature=next;const old=q('mapTrip').value;q('mapTrip').innerHTML=rows.map(t=>`<option value="${safe(t.id)}">${safe(t.code)} · ${safe(t.origin)} → ${safe(t.destination)}</option>`).join('');if(rows.some(t=>String(t.id)===old))q('mapTrip').value=old;if(mode==='route')drawRoute();}
  if(!map){init();drawList();loadGPS();}
 }
 document.querySelectorAll('[data-map-mode]').forEach(b=>b.addEventListener('click',()=>setMode(b.dataset.mapMode)));
 q('mapTrip').addEventListener('change',()=>drawRoute(true));
 q('mapFit').addEventListener('click',()=>mode==='gps'?fitGPS():drawRoute(true));
 q('mapReload').addEventListener('click',()=>loadGPS(true));
 for(const id of ['mapSearch','mapFilter'])q(id).addEventListener(id==='mapSearch'?'input':'change',()=>{selectedVehicle='';map?.closePopup();drawList();drawGPS();});
 q('mapVehicleList').addEventListener('click',e=>{const b=e.target.closest('[data-map-vehicle]');if(b)focusVehicle(b.dataset.mapVehicle);if(e.target.closest('#mapClearFilter')){q('mapSearch').value='';q('mapFilter').value='all';drawList();drawGPS();}});
 q('mapExpand').addEventListener('click',()=>{const expanded=q('dispatchMap').closest('.network-card').classList.toggle('map-expanded');q('mapExpand').textContent=expanded?'Thu gọn':'Mở rộng';q('mapExpand').setAttribute('aria-pressed',String(expanded));map?.invalidateSize();});
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&q('mapExpand').getAttribute('aria-pressed')==='true')q('mapExpand').click();});
 q('mapCoordinates').addEventListener('submit',e=>{e.preventDefault();const t=trips.find(t=>String(t.id)===q('mapTrip').value);if(!t)return;const origin=parseCoordinate(q('mapOrigin').value),destination=parseCoordinate(q('mapDestination').value);if(!origin||!destination){q('mapLocationNote').textContent='Nhập vĩ độ, kinh độ hợp lệ, ngăn bằng dấu phẩy.';return;}const next={...stored,[key(t)]:{origin,destination}};try{localStorage.setItem(coordinatesKey,JSON.stringify(next));stored=next;drawRoute(true);}catch(_){q('mapLocationNote').textContent='Không lưu được vị trí trên trình duyệt.';}});
 q('mapClear').addEventListener('click',()=>{const t=trips.find(t=>String(t.id)===q('mapTrip').value);if(!t)return;const next={...stored};delete next[key(t)];try{localStorage.setItem(coordinatesKey,JSON.stringify(next));stored=next;drawRoute(true);}catch(_){q('mapLocationNote').textContent='Không xóa được vị trí đã lưu.';}});
 window.addEventListener('enterpriseDataChanged',()=>loadGPS(true));
 window.addEventListener('demoReset',()=>{epoch++;gps=[];lastGpsSignature='';gpsLayer?.clearLayers();drawList();loadGPS(true);});
 setInterval(()=>{if(mode==='gps'&&!document.hidden&&(!location.hash||location.hash==='#dashboard'))loadGPS();},15000);
 window.DispatchMap={update,setMode,filteredGPS,parseCoordinate,resize:()=>requestAnimationFrame(()=>{map?.invalidateSize();if(mode==='gps'&&fitOnFirstLoad&&gps.length){fitOnFirstLoad=false;fitGPS();}})};
})();

"use strict";
// Street tiles are real. These reference points are not GPS vehicle positions.
(function () {
 const byId=id=>document.getElementById(id);
 const safe=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const references={
  'KCN Sóng Thần':[10.901,106.745],
  'Cảng Cát Lái':[10.758,106.790]
 };
 const storageKey='ui-dispatch-map-coordinates-v1';
 let stored={};try{stored=JSON.parse(localStorage.getItem(storageKey)||'{}')||{};}catch(_){}
 let map,points,tripList=[],signature='',tileOK=false;
 const key=t=>JSON.stringify([t.id,t.origin,t.destination]);
 function parseCoordinate(value){
  const parts=value.trim().split(',').map(x=>x.trim());
  if(parts.length!==2||parts.some(x=>x===''))return null;
  const nums=parts.map(Number);
  return nums.every(Number.isFinite)&&Math.abs(nums[0])<=90&&Math.abs(nums[1])<=180?nums:null;
 }
 function validPoint(p){return Array.isArray(p)&&p.length===2&&p.every(Number.isFinite)&&Math.abs(p[0])<=90&&Math.abs(p[1])<=180;}
 function location(t,side){const custom=stored[key(t)]?.[side];return validPoint(custom)?custom:references[t[side]]||null;}
 function selected(){return tripList.find(t=>String(t.id)===byId('mapTrip').value);}
 function init(){
  if(map)return true;
  if(!window.L){byId('mapStatus').textContent='Không tải được thư viện bản đồ. Hãy tải lại trang.';return false;}
  map=L.map('dispatchMap',{scrollWheelZoom:false}).setView([10.84,106.78],10);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{
   maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors'
  }).on('tileload',()=>{tileOK=true;byId('mapStatus').textContent='Bản đồ đường phố · A: lấy hàng · B: giao hàng';})
   .on('tileerror',()=>{if(!tileOK)byId('mapStatus').textContent='Không tải được nền bản đồ. Kiểm tra Internet hoặc mở Google Maps.';}).addTo(map);
  points=L.featureGroup().addTo(map);
  new ResizeObserver(()=>map.invalidateSize()).observe(byId('dispatchMap'));
  return true;
 }
 function draw(fit=false){
  const t=selected();if(!t)return;
  const origin=location(t,'origin'),destination=location(t,'destination');
  const url=new URL('https://www.google.com/maps/dir/');
  url.search=new URLSearchParams({api:'1',origin:origin?origin.join(','):t.origin+', Việt Nam',destination:destination?destination.join(','):t.destination+', Việt Nam',travelmode:'driving'}).toString();
  byId('googleDirections').href=url.href;
  byId('mapOrigin').value=origin?.join(', ')||'';byId('mapDestination').value=destination?.join(', ')||'';
  byId('mapLocationNote').textContent=stored[key(t)]?'Đang dùng tọa độ bạn đã lưu. Chưa có nguồn GPS phương tiện.':(origin||destination?'Điểm mặc định chỉ tham chiếu khu vực, chưa xác nhận cổng kho/cảng. Nhập tọa độ chính xác khi sử dụng.':'Chưa xác định tọa độ cho tuyến này. Nhập vị trí hoặc mở Google Maps để tìm địa chỉ.');
  if(!init())return;
  points.clearLayers();
  [['origin',origin,'A',t.origin],['destination',destination,'B',t.destination]].forEach(([side,p,label,name])=>{
   if(!p)return;
   const icon=L.divIcon({className:'map-pin '+side,html:label,iconSize:[32,32],iconAnchor:[16,16]});
   L.marker(p,{icon,title:name}).bindPopup(`<b>${safe(label==='A'?'Điểm lấy hàng':'Điểm giao hàng')}</b><br>${safe(name)}<br>${safe(t.code)} · ${safe(t.vehicle_id||'Chưa phân công')}<br>${p[0]}, ${p[1]}<br><small>Điểm địa lý; không phải vị trí xe GPS.</small>`).addTo(points);
  });
  if(fit){if(points.getLayers().length)map.fitBounds(points.getBounds(),{padding:[45,45],maxZoom:13});else map.setView([10.84,106.78],10);}
 }
 function update(trips){
  tripList=trips;
  const next=JSON.stringify(trips.map(t=>[t.id,t.code,t.origin,t.destination,t.vehicle_id]));
  if(next===signature)return;signature=next;
  const previous=byId('mapTrip').value;
  byId('mapTrip').innerHTML=trips.map(t=>`<option value="${safe(t.id)}">${safe(t.code)} · ${safe(t.origin)} → ${safe(t.destination)}</option>`).join('');
  if(trips.some(t=>String(t.id)===previous))byId('mapTrip').value=previous;
  byId('googleDirections').hidden=!trips.length;
  byId('mapCoordinates').hidden=!trips.length;
  byId('mapFit').disabled=!trips.length;
  if(trips.length)draw(!previous||!trips.some(t=>String(t.id)===previous));
  else{points?.clearLayers();byId('mapStatus').textContent='Chưa có chuyến xe.';byId('mapLocationNote').textContent='Thêm chuyến xe để định vị điểm lấy và giao hàng.';}
 }
 byId('mapTrip').addEventListener('change',()=>draw(true));
 byId('mapFit').addEventListener('click',()=>draw(true));
 byId('mapExpand').addEventListener('click',()=>{
  const expanded=byId('dispatchMap').closest('.network-card').classList.toggle('map-expanded');
  byId('mapExpand').textContent=expanded?'Thu gọn':'Mở rộng';byId('mapExpand').setAttribute('aria-pressed',String(expanded));map?.invalidateSize();
 });
 document.addEventListener('keydown',e=>{if(e.key==='Escape'&&byId('mapExpand').getAttribute('aria-pressed')==='true')byId('mapExpand').click();});
 byId('mapCoordinates').addEventListener('submit',e=>{
  e.preventDefault();const t=selected();if(!t)return;
  const origin=parseCoordinate(byId('mapOrigin').value),destination=parseCoordinate(byId('mapDestination').value);
  if(!origin||!destination){byId('mapLocationNote').textContent='Nhập hai số ngăn bằng dấu phẩy. Vĩ độ từ −90 đến 90, kinh độ từ −180 đến 180.';return;}
  const next={...stored,[key(t)]:{origin,destination}};
  try{localStorage.setItem(storageKey,JSON.stringify(next));stored=next;draw(true);}catch(_){byId('mapLocationNote').textContent='Trình duyệt không cho phép lưu vị trí. Kiểm tra cài đặt lưu trữ.';}
 });
 byId('mapClear').addEventListener('click',()=>{
  const t=selected();if(!t)return;const next={...stored};delete next[key(t)];
  try{localStorage.setItem(storageKey,JSON.stringify(next));stored=next;draw(true);}catch(_){byId('mapLocationNote').textContent='Không xóa được vị trí đã lưu trên trình duyệt.';}
 });
 window.DispatchMap={update,resize:()=>requestAnimationFrame(()=>map?.invalidateSize()),parseCoordinate};
})();

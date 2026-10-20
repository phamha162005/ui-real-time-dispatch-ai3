"use strict";
(function(){
 const q=id=>document.getElementById(id);
 const names={code:'Mã chuyến',vehicle_id:'Mã xe / biển số',vehicle_type:'Loại xe',capacity:'Tải trọng (tấn)',load:'Tải hàng (tấn)',origin:'Điểm lấy',destination:'Điểm giao',start_at:'Giờ khởi hành',cutoff:'Cut-off',travel_minutes:'Di chuyển còn lại (phút)',handling_minutes:'Bốc dỡ còn lại (phút)',delay_minutes:'Chậm thêm (phút)',distance_km:'Quãng đường (km)',cost:'Chi phí (VND)',wait_cost_per_hour:'Phí chờ (VND/giờ)',status:'Trạng thái',data_issue:'Chất lượng dữ liệu',eta_manual:'ETA giới hạn (tùy chọn)',note:'Ghi chú',source_updated_at:'Thời điểm nguồn ghi nhận',latitude:'Vĩ độ',longitude:'Kinh độ',speed_kmh:'Tốc độ (km/h)',external_id:'Mã bản ghi nguồn',trip_code:'Mã chuyến liên quan',container_id:'Mã container'};
 let rows=[],batch=null,source='TMS',epoch=0,mappingDirty=false,map,marker,loaded=false;
 const stamp=v=>v?time(v)+' '+date(v)+' (VN)':'—';
 function clearPreview(){batch=null;q('enterprisePreview').innerHTML='';}
 function markDirty(){mappingDirty=true;epoch++;clearPreview();q('enterpriseReadFile').disabled=true;q('enterpriseReadApi').disabled=true;q('enterpriseMappingStatus').textContent='Có thay đổi · Bấm Lưu ghép cột để tiếp tục';}
 function drawConfig(s){
  q('enterpriseRowsPath').value=s.config.rows_path;
  const row=k=>`<label class="mapping-row"><span class="mapping-name">${esc(names[k]||k)}<code>${esc(k)}</code></span><span class="mapping-arrow" aria-hidden="true">←</span><input data-map-field="${esc(k)}" aria-label="Tên cột nguồn cho ${esc(names[k]||k)}" value="${esc(s.config.mapping[k]||k)}" placeholder="Tên cột trong tệp" maxlength="150" required></label>`;
  const primary=['code','vehicle_id','origin','destination','start_at','cutoff','status','source_updated_at'];
  const basic=source==='TMS'?s.fields.filter(k=>primary.includes(k)):s.fields;
  const extra=source==='TMS'?s.fields.filter(k=>!primary.includes(k)):[];
  q('enterpriseMappings').innerHTML=basic.map(row).join('')+(extra.length?`<details class="help-details mapping-more"><summary>Các cột bổ sung (${extra.length})</summary><p>Kiểm tra thêm nếu tệp của bạn khác tệp mẫu.</p>${extra.map(row).join('')}</details>`:'');
  q('enterpriseMappingStatus').textContent='Đã lưu · Có thể xem trước dữ liệu';
  q('enterpriseApiSummary').textContent=s.checks.ready?'Sẵn sàng kiểm tra kết nối.': 'Chưa bật API · Bạn vẫn có thể nhập tệp.';
  const checks={read_enabled:'Đã cho phép đọc API',endpoint_configured:'URL HTTPS đã cấu hình',host_allowed:'Hostname đã cho phép',authentication_configured:'Xác thực đã cấu hình'};
  q('enterpriseChecks').innerHTML=Object.entries(checks).map(([k,v])=>`<div class="enterprise-check ${s.checks[k]?'ok':''}"><b>${s.checks[k]?'✓':'○'}</b><span>${v}</span></div>`).join('');
  q('enterpriseReadApi').disabled=!s.checks.ready;q('enterpriseReadFile').disabled=false;
  q('enterpriseTemplate').href='/api/enterprise/'+source+'/template.csv';
  q('enterpriseTestStatus').textContent=s.last_test?`Lần kiểm tra ${stamp(s.last_test.attempted_at)}: ${s.last_test.message}`:'Chưa kiểm tra kết nối.';
  mappingDirty=false;
 }
 function drawData(result){
  rows=result.records||[];q('enterpriseDataStamp').textContent=rows.length?`${rows.length}/${result.total_count} bản ghi hiển thị · Cập nhật kho dữ liệu ${stamp(result.updated_at)} · Giữ riêng thời điểm nguồn`:'Chưa có dữ liệu nguồn đã được xác nhận';
  if(!rows.length){q('enterpriseData').innerHTML='<div class="no-data">Nhập tệp hoặc đọc API để xem trước, sau đó xác nhận cập nhật.</div>';return;}
  let head,body;
  if(source==='GPS'){
   head='<th>XE</th><th>TỌA ĐỘ</th><th>TỐC ĐỘ</th><th>THỜI ĐIỂM NGUỒN</th><th>ĐỘ MỚI</th><th>BẢN ĐỒ</th>';
   body=rows.map((r,i)=>`<tr><td>${esc(r.vehicle_id)}</td><td>${r.latitude}, ${r.longitude}</td><td>${r.speed_kmh} km/h</td><td>${stamp(r.source_updated_at)}<span class="subcell">${r.ingestion_method==='api'?'Đọc API theo lần bấm':'Nhập tệp'}</span></td><td>${r.age_minutes<0?'Thời điểm nằm trong tương lai':r.age_minutes>5?'Dữ liệu đã cũ · ':'Gần thời điểm hiện tại · '}${Math.abs(r.age_minutes)} phút</td><td><button class="table-btn" data-enterprise-gps="${i}">Xem vị trí</button></td></tr>`).join('');
  }else if(source==='TMS'){
   head='<th>CHUYẾN / XE NGUỒN</th><th>TUYẾN</th><th>TRẠNG THÁI</th><th>CUT-OFF</th><th>THỜI ĐIỂM NGUỒN</th>';
   body=rows.map(r=>`<tr><td>${esc(r.code)}<span class="subcell">${esc(r.vehicle_id||'Chưa có mã xe')}</span></td><td>${esc(r.origin)} → ${esc(r.destination)}</td><td>${esc(statusNames[r.status]||r.status)}</td><td>${stamp(r.cutoff)}<span class="subcell">ETA ước tính tại mốc nguồn: ${stamp(r.source_eta_preview)}</span></td><td>${stamp(r.source_updated_at)}</td></tr>`).join('');
  }else{
   head='<th>MÃ BẢN GHI</th><th>MÃ CHUYẾN</th><th>CONTAINER</th><th>TRẠNG THÁI NGUỒN</th><th>THỜI ĐIỂM NGUỒN</th>';
   body=rows.map(r=>`<tr><td>${esc(r.external_id)}</td><td>${esc(r.trip_code)}</td><td>${esc(r.container_id)}</td><td>${esc(r.status)}</td><td>${stamp(r.source_updated_at)}</td></tr>`).join('');
  }
  q('enterpriseData').innerHTML=`<table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
 }
 async function load(){
  const gen=++epoch;source=q('enterpriseSource').value;clearPreview();q('enterpriseMapCard').hidden=true;
  try{
   const data=await api('/enterprise/status');if(gen!==epoch)return;
   const s=data.find(x=>x.source===source);drawConfig(s);loaded=true;
   const result=await api('/enterprise/'+source+'/data');if(gen===epoch)drawData(result);
  }catch(e){if(gen===epoch)toast(e.message,true);}
 }
 function showPreview(r){
  batch=r;const blocked=r.errors.length>0,fields=r.records.length?Object.keys(r.records[0]):[];
  const cell=(key,value)=>value===null||value===''?'—':key.endsWith('_at')||['cutoff','eta_manual'].includes(key)?stamp(value):String(value);
  q('enterprisePreview').innerHTML=`<article class="card"><div class="card-head"><div><span class="step-label">BƯỚC 3</span><h2>Kiểm tra & lưu ${esc(r.source)}</h2><p>${r.count} dòng · ${r.valid_count} hợp lệ · ${r.errors.length} lỗi</p></div><span class="pill ${blocked?'':'teal'}">${blocked?'Cần sửa dữ liệu':'Sẵn sàng lưu'}</span></div><div class="card-body"><p>${blocked?'Sửa các lỗi bên dưới, sau đó xem trước lại.':'Kiểm tra mã xe, thời gian và đơn vị trước khi lưu.'}</p>${r.errors.length?`<div class="analysis-warning">${r.errors.slice(0,30).map(e=>`<p>${e.row?'Dòng '+e.row+': ':''}${esc(e.message)}</p>`).join('')}</div>`:''}</div>${fields.length?`<div class="table-wrap preview-table"><table><thead><tr>${fields.map(k=>`<th>${esc(names[k]||k)}</th>`).join('')}</tr></thead><tbody>${r.records.slice(0,20).map(row=>`<tr>${fields.map(k=>`<td>${esc(cell(k,row[k]))}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:''}<div class="card-body ops-form"><p class="muted small">Hiển thị tối đa 20 dòng đầu. ${r.valid_count} dòng hợp lệ sẽ được xử lý khi xác nhận.</p><button class="btn primary" id="enterpriseCommit" ${blocked?'disabled':''}>Xác nhận & lưu dữ liệu</button><details class="help-details"><summary>Xem JSON kỹ thuật</summary><pre class="notice-raw">${esc(JSON.stringify(r.records.slice(0,20),null,2))}</pre></details></div></article>`;
  q('enterprisePreview').scrollIntoView({behavior:'smooth',block:'start'});
 }
 q('enterpriseSource').addEventListener('change',load);q('enterpriseRefresh').addEventListener('click',()=>busy(q('enterpriseRefresh'),load));
 q('enterpriseMappingForm').addEventListener('input',markDirty);
 q('enterpriseMappingForm').addEventListener('submit',e=>{e.preventDefault();busy(e.submitter,async()=>{
  const captured=source;
  const mapping=Object.fromEntries([...q('enterpriseMappings').querySelectorAll('[data-map-field]')].map(el=>[el.dataset.mapField,el.value.trim()]));
  await api('/enterprise/'+captured+'/config',{method:'PUT',body:JSON.stringify({mapping,rows_path:q('enterpriseRowsPath').value.trim()})});
  await load();toast('Đã lưu ghép cột. Bạn có thể xem trước dữ liệu.');
 });});
 q('enterpriseReadFile').addEventListener('click',()=>busy(q('enterpriseReadFile'),async()=>{
  if(!loaded||mappingDirty)throw Error('Bấm Lưu ghép cột trước khi xem trước dữ liệu.');
  const file=q('enterpriseFile').files[0];if(!file)throw Error('Chọn tệp CSV hoặc JSON đã được phép sử dụng.');
  if(file.size>2000000)throw Error('Tệp tối đa 2 MB, mỗi lần tối đa 1.000 dòng.');
  const format=file.name.toLowerCase().endsWith('.json')?'json':file.name.toLowerCase().endsWith('.csv')?'csv':null;
  if(!format)throw Error('Chỉ hỗ trợ CSV/JSON. Excel cần xuất CSV UTF-8; PDF cần bước trích xuất riêng.');
  clearPreview();const gen=epoch,captured=source,text=await file.text();const result=await post('/enterprise/'+captured+'/preview-file',{format,text});if(gen===epoch)showPreview(result);
 }));
 q('enterpriseReadApi').addEventListener('click',()=>{
  const captured=source,gen=epoch;
  confirm('Đọc nguồn '+captured,'Bạn đã được doanh nghiệp cấp quyền đọc nguồn này? Dữ liệu sẽ được lấy để xem trước, chưa lưu hoặc gửi lệnh.',async()=>{
   if(gen!==epoch||mappingDirty)throw Error('Nguồn hoặc cách ghép cột đã đổi; kiểm tra lại trước khi đọc.');
   clearPreview();const result=await post('/enterprise/'+captured+'/preview-api',{confirmed:true});if(gen===epoch)showPreview(result);
  });
 });
 document.addEventListener('click',e=>{
  const button=e.target.closest('button');if(!button)return;
  if(button.id==='enterpriseCommit'&&batch){
   const selected=batch,gen=epoch;
   confirm('Cập nhật dữ liệu '+selected.source,`Cập nhật ${selected.valid_count} bản ghi vào khu vực doanh nghiệp? Dữ liệu cũ hơn hoặc cùng dấu thời gian được bỏ qua; không ghi đè chuyến mẫu hoặc gửi lệnh.`,async()=>{
    if(gen!==epoch||mappingDirty)throw Error('Nguồn đã đổi. Xem trước lại trước khi cập nhật.');
    const result=await post('/enterprise/'+selected.source+'/commit',{batch_id:selected.id,confirmed:true});await load();window.dispatchEvent(new Event('enterpriseDataChanged'));toast(`Đã lưu ${result.count} bản ghi; bỏ qua ${result.ignored_older_or_equal} bản ghi cũ/trùng.`);
   });
  }
  if(button.dataset.enterpriseGps!==undefined){
   const r=rows[Number(button.dataset.enterpriseGps)];if(!r||source!=='GPS')return;
   q('enterpriseMapCard').hidden=false;q('enterpriseMapStamp').textContent=`${r.vehicle_id} · Nguồn ghi nhận ${stamp(r.source_updated_at)} · ${r.ingestion_method==='api'?'Đọc API theo lần bấm':'Nhập tệp, chưa phải theo dõi trực tiếp'}`;
   if(!window.L){toast('Không tải được thư viện bản đồ.',true);return;}
   if(!map){map=L.map('enterpriseMap').setView([r.latitude,r.longitude],14);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'}).addTo(map);new ResizeObserver(()=>map.invalidateSize()).observe(q('enterpriseMap'));}
   if(marker)marker.remove();marker=L.marker([r.latitude,r.longitude],{icon:L.divIcon({className:'gps-source-pin',html:'GPS',iconSize:[40,30]})}).addTo(map).bindPopup(`<b>${esc(r.vehicle_id)}</b><br>${stamp(r.source_updated_at)}<br>${r.latitude}, ${r.longitude}`);
   map.invalidateSize();map.setView([r.latitude,r.longitude],14);q('enterpriseMapCard').scrollIntoView({behavior:'smooth',block:'center'});
  }
 });
 window.addEventListener('demoReset',()=>{epoch++;loaded=false;clearPreview();rows=[];if(location.hash==='#enterprise')load();});
 window.EnterpriseUI={load};if(location.hash==='#enterprise')load();
})();

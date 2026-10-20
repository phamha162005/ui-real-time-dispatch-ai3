"use strict";
(function(){
 const q=id=>document.getElementById(id);
 let state=null,notice=null,orderContext=null,selectSignature='',orderSignature='';
 const noticeNames={schedule:'Lịch tàu',booking:'Booking',pickup:'Đổi điểm lấy',delivery:'Đổi điểm giao',container:'Đổi container',vehicle:'Đổi phương tiện',incident:'Sự cố xe'};
 const orderStatuses={sent:'Đã gửi',received:'Đã nhận',confirmed:'Đã xác nhận',rejected:'Từ chối',executing:'Đang thực hiện'};
 const actionNames={continue:'Tiếp tục',hold:'Dừng an toàn',adjust:'Điều chỉnh'};
 const stamp=v=>v?`${shortTime(v)} ${date(v)}`:'—';
 const display=(v,field)=>field==='incident'&&!v?'Không có / đã xử lý':v&&['cutoff','ship_eta','ship_etd'].includes(field)?`${time(v)} ${date(v)} (VN)`:typeof v==='boolean'?(v?'Đã hủy':'Hoạt động'):(v||'Chưa có');
 function trip(id){return state?.trips.find(t=>String(t.id)===String(id));}
 function tripOptions(id,trips){const old=q(id).value;q(id).innerHTML=trips.map(t=>`<option value="${t.id}">${esc(t.code)} · ${esc(t.vehicle_id||'Chưa phân công')} · ${esc(t.origin)} → ${esc(t.destination)}</option>`).join('');if(trips.some(t=>String(t.id)===old))q(id).value=old;}
 function setOrderContext(){
  const t=trip(q('orderTrip').value);if(!t){orderContext=null;q('orderTripInfo').textContent='Cần chuyến chưa hoàn thành và đã được phân công xe.';return;}
  const version=Math.max(0,...state.operations.orders.filter(o=>o.trip_id===t.id).map(o=>o.version));
  orderContext={trip_id:t.id,trip_revision:t.revision,expected_version:version};
  q('orderTripInfo').innerHTML=`<b>${esc(t.code)} · ${esc(t.vehicle_id)}</b><br>${esc(t.origin)} → ${esc(t.destination)}<br>Cut-off ${stamp(t.cutoff)} · Phiên bản tiếp theo: v${version+1}`;
 }
 function render(s){
  state=s;const unfinished=s.trips.filter(t=>t.status!=='hoan_thanh');
  const sig=JSON.stringify(unfinished.map(t=>[t.id,t.code,t.vehicle_id,t.origin,t.destination]));
  if(sig!==selectSignature){selectSignature=sig;tripOptions('noticeTrip',unfinished);tripOptions('orderTrip',unfinished.filter(t=>t.vehicle_id));setOrderContext();}
  // Capture revisions only on explicit selection, rather than silently refreshing a draft.
  const orders=s.operations.orders,m=s.operations.metrics;
  q('orderMetrics').innerHTML=metric('Phiên bản đã phát hành',m.issued,'lệnh','Trong dữ liệu phiên thử','▤')+metric('Chờ xác nhận',m.waiting,'lệnh','Phiên bản còn hiệu lực','◷')+metric('Quá 05 phút',m.overdue,'lệnh','Cần điều vận liên hệ','!','warn')+metric('Xác nhận ≤05 phút',m.within_five_rate??'—','%',`${m.within_five_minutes}/${m.issued} phiên bản đã phát hành`,'✓');
  q('workflowReport').innerHTML=`<div class="detail-grid"><div><small>Phiên bản đã phát hành</small>${m.issued}</div><div><small>Đã xác nhận</small>${m.confirmed}</div><div><small>Xác nhận trong 05 phút / đã phát hành</small>${m.within_five_minutes}/${m.issued} · ${m.within_five_rate??'—'}%</div><div><small>Đang chờ / quá 05 phút</small>${m.waiting} / ${m.overdue}</div></div><p class="muted small">Mẫu số bao gồm tất cả phiên bản đã phát hành, kể cả phiên bản bị thay thế. Đây là số liệu phiên thử; mục tiêu ≥95% trong báo cáo chưa phải kết quả thực tế tại doanh nghiệp.</p>`;
  q('orderHistory').innerHTML=orders.length?`<table><thead><tr><th>CHUYẾN / PHIÊN BẢN</th><th>NGƯỜI NHẬN</th><th>HIỆU LỰC</th><th>GỬI – NHẬN – XÁC NHẬN</th><th>PHẢN HỒI</th><th>CHI TIẾT</th></tr></thead><tbody>${orders.map(o=>`<tr><td><b>${esc(o.trip_code)} · v${o.version}</b><span class="subcell">${esc(o.vehicle_id)} · ${actionNames[o.action]}</span></td><td>${esc(o.driver)}</td><td><span class="pill ${o.active?'teal':''}">${o.active?'Hiện hành':'Hết hiệu lực'}</span><span class="subcell">${orderStatuses[o.status]}${o.stale?' · Cần phát hành lại':''}</span></td><td>Gửi ${stamp(o.sent_at)}<span class="subcell">Nhận ${stamp(o.received_at)}<br>Xác nhận ${stamp(o.confirmed_at)}</span></td><td>${o.response_minutes===null?`Chưa xác nhận${o.active?' · '+o.elapsed_minutes.toFixed(1)+' phút':''}`:o.response_minutes.toFixed(1)+' phút'}${o.overdue?'<span class="subcell negative">Quá hạn phản hồi</span>':''}</td><td><button class="table-btn" data-order-detail="${o.id}">Nhật ký</button></td></tr>`).join('')}</tbody></table>`:'<div class="no-data">Chưa phát hành lệnh. Chọn chuyến và kiểm tra nội dung để bắt đầu.</div>';
  if(orderContext){const latest=trip(orderContext.trip_id);const version=Math.max(0,...orders.filter(o=>o.trip_id===orderContext.trip_id).map(o=>o.version));if(latest&&(latest.revision!==orderContext.trip_revision||version!==orderContext.expected_version))q('orderTripInfo').innerHTML+=q('orderTripInfo').innerHTML.includes('Nạp lại dữ liệu')?'':'<p class="negative">Chuyến hoặc phiên bản đã đổi. Bấm Nạp lại dữ liệu trước khi phát hành.</p>';}
  renderInbox();
  q('noticeHistory').innerHTML=s.operations.notices.map(n=>`<div class="log-row"><b>${esc(n.trip_code)} · ${esc(noticeNames[n.kind]||n.kind)}</b><small>${stamp(n.created_at)} · ${n.status==='applied'?'Đã cập nhật':'Chờ xác minh'} · ${n.changes.length} thay đổi</small><button class="table-btn" data-notice-detail="${esc(n.id)}">Xem đối chiếu</button></div>`).join('')||'<div class="no-data">Chưa tiếp nhận thông báo.</div>';
 }
 function renderInbox(){
  if(!state)return;const driver=q('inboxDriver').value.trim();
  q('driverInbox').innerHTML=state.operations.orders.filter(o=>o.driver===driver&&o.active).map(o=>{
   const buttons=o.stale?'':o.status==='sent'?`<button class="btn primary compact" data-driver-event="receive" data-order="${o.id}">Ghi nhận đã nhận</button>`:o.status==='received'?`<button class="btn primary compact" data-driver-event="confirm" data-order="${o.id}">Đã hiểu & xác nhận</button><button class="btn compact" data-driver-event="reject" data-order="${o.id}">Không thể thực hiện</button>`:o.status==='confirmed'?`<button class="btn primary compact" data-driver-event="execute" data-order="${o.id}">Bắt đầu thực hiện</button>`:'';
   return `<div class="driver-order"><div class="section-toolbar"><b>${esc(o.trip_code)} · v${o.version}</b><span class="pill ${o.overdue?'':'teal'}">${orderStatuses[o.status]}</span></div><p><b>${esc(o.vehicle_id)} · ${actionNames[o.action]}</b><br>${esc(o.trip_snapshot.origin)} → ${esc(o.trip_snapshot.destination)}<br>Cut-off ${stamp(o.trip_snapshot.cutoff)}</p><p class="order-instructions">${esc(o.instructions)}</p>${o.overdue?'<p class="negative">Đã quá 05 phút chưa xác nhận.</p>':''}${o.stale?'<p class="negative">Dữ liệu chuyến đã đổi; cần nhận phiên bản mới từ điều vận.</p>':''}${o.reason?`<p>Lý do từ chối: ${esc(o.reason)}</p>`:''}<div class="driver-actions">${buttons}</div></div>`;
  }).join('')||'<div class="no-data">Không có lệnh hiện hành cho mã lái xe này.</div>';
 }
 function showNotice(n){
  notice=n;const changed=n.changes.length>0;
  q('noticeResult').className='card';
  q('noticeResult').innerHTML=`<div class="card-head"><div><h2>Đối chiếu ${esc(n.trip_code)}</h2><p>${esc(n.method)}</p></div><span class="pill teal">${n.status==='applied'?'Đã cập nhật':n.changes.length+' thay đổi'}</span></div><div class="table-wrap"><table><thead><tr><th>TRƯỜNG</th><th>GIÁ TRỊ CŨ</th><th>GIÁ TRỊ MỚI</th></tr></thead><tbody>${n.changes.map(c=>`<tr><td>${esc(c.label)}</td><td>${esc(display(c.before,c.field))}</td><td><b>${esc(display(c.after,c.field))}</b></td></tr>`).join('')}</tbody></table></div><div class="card-body"><p>${changed?'Kiểm tra đúng chuyến, booking và thời gian trước khi cập nhật.':'Thông tin đọc được trùng dữ liệu hiện tại; không cần cập nhật.'}</p>${n.warnings.map(w=>`<p class="negative">${esc(w)}</p>`).join('')}<details><summary>Văn bản đã nhập & các trường đọc được</summary><pre class="notice-raw">${esc(n.text)}</pre><pre class="notice-raw">${esc(JSON.stringify(n.values,null,2))}</pre></details>${changed&&n.status==='pending'?'<button class="btn primary full" id="applyNotice">Xác minh & cập nhật dữ liệu chuyến</button>':''}${n.status==='applied'?'<p>Đã cập nhật dữ liệu. Phát hành lệnh mới để lái xe nhận và xác nhận.</p><a class="btn primary" href="#orders">Đến Lệnh & xác nhận →</a>':''}</div>`;
 }
 function sample(kind){
  const t=trip(q('noticeTrip').value);if(!t)return toast('Cần chọn chuyến chưa hoàn thành.',true);
  q('noticeKind').value=kind;
  const cutoff=localInput(new Date(new Date(t.cutoff).getTime()+120*60000).toISOString())+':00+07:00';
  const samples={schedule:`Tên tàu: UI SAMPLE VESSEL\nChuyến tàu: 026E\nCut-off: ${cutoff}`,booking:`Booking: BK-${t.code}\nTrạng thái: Hủy`,pickup:'Điểm lấy: Kho mới Bình Dương',delivery:'Điểm giao: Depot mới Thủ Đức',container:'Container: UIXX1234567',vehicle:`Phương tiện: ${state.vehicles.find(v=>v.available_now&&v.type===t.vehicle_type&&v.capacity>=t.load)?.id||t.vehicle_id||'NHAP-MA-XE'}`,incident:'Sự cố: Xe hỏng lốp, cần điều vận hỗ trợ'};
  q('noticeText').value=samples[kind]||'';

 }
 function showPilot(r){
  q('pilotResult').innerHTML=`<div class="notice"><strong>${r.recommended?'Ưu tiên xe '+esc(r.recommended):'Chưa có xe đáp ứng đầy đủ ràng buộc'}</strong><p>${esc(r.formula)}</p><p>Đã xét ${r.input_count} xe · ${r.feasible_count} xe hợp lệ · ${r.rejected.length} xe bị loại · Hiển thị ${r.returned_count} phương án tốt nhất</p><p>Tmax = ${r.max_tours} tour · Kmax = ${r.max_km} km</p></div><div class="option-grid">${r.options.map((o,i)=>`<article class="option-card ${i===0?'recommended':''}"><span class="pill teal">Thứ hạng ${i+1}</span><h3>${esc(o.plate)}</h3><div class="option-score">${o.display_score.toFixed(3)}<small> điểm S</small></div><div class="option-details">Tour: ${o.tours} · Km: ${o.km}<br>Vị trí: ${o.at_yard?'Bãi Xe U&I':'Ngoài bãi xe'}<br>S = (${o.tour_component.toFixed(3)} + ${o.km_component.toFixed(3)} + ${o.position_component}) / 3</div><p>${i===0?'Điểm thấp nhất trong các xe hợp lệ. Nhân viên điều vận kiểm tra điều kiện thực tế trước khi lựa chọn.':'Đáp ứng các điều kiện đã đánh dấu; đứng sau phương án ưu tiên theo điểm S.'}</p></article>`).join('')}</div>${r.rejected.length?'<div class="analysis-warning"><b>Xe bị loại</b>'+r.rejected.map(v=>`<p>${esc(v.plate)}: ${v.reasons.map(esc).join('; ')}</p>`).join('')+'</div>':''}<details class="fleet-ranking"><summary>Xem toàn bộ ${r.feasible_count} xe hợp lệ theo thứ hạng</summary><div class="table-wrap"><table><thead><tr><th>HẠNG</th><th>XE</th><th>ĐIỂM S</th></tr></thead><tbody>${r.ranking.map((v,i)=>`<tr><td>${i+1}</td><td>${esc(v.plate)}</td><td>${v.display_score.toFixed(3)}</td></tr>`).join('')}</tbody></table></div></details><p class="analysis-note">${esc(r.note)} Kết quả này không tự thay đổi phân công trong đội xe vận hành mẫu.</p>`;
 }
 q('noticeForm').addEventListener('submit',e=>{e.preventDefault();busy(e.submitter,async()=>{showNotice(await post('/notices/preview',{trip_id:Number(q('noticeTrip').value),kind:q('noticeKind').value,text:q('noticeText').value}));await refresh();});});
 q('sampleSchedule').addEventListener('click',()=>sample('schedule'));q('sampleBooking').addEventListener('click',()=>sample('booking'));q('sampleNotice').addEventListener('click',()=>sample(q('noticeKind').value));
 q('orderTrip').addEventListener('change',setOrderContext);q('reloadOrder').addEventListener('click',()=>{setOrderContext();toast('Đã nạp dữ liệu mới nhất. Kiểm tra nội dung lệnh trước khi phát hành.');});
 q('orderForm').addEventListener('submit',e=>{
  e.preventDefault();if(!orderContext)return toast('Chưa có chuyến phù hợp để phát hành.',true);
  const p={...orderContext,driver:q('orderDriver').value.trim(),action:q('orderAction').value,instructions:q('orderInstructions').value.trim(),confirmed:true};
  confirm('Phát hành lệnh v'+(p.expected_version+1),`Chuyến ${trip(p.trip_id)?.code}, người nhận ${p.driver}. Phiên bản cũ sẽ hết hiệu lực. Nội dung: ${p.instructions}`,async()=>{await post('/orders',p);await refresh();setOrderContext();toast('Đã phát hành phiên bản mới trong ứng dụng. Chuyển sang màn hình lái xe để nhận lệnh.');});
 });
 q('inboxDriver').addEventListener('input',renderInbox);
 q('orderAdvance').addEventListener('click',()=>busy(q('orderAdvance'),async()=>{acceptSnapshot(await post('/clock',{action:'advance',minutes:5}));toast('Đã tăng 05 phút thời gian điều hành.');}));
 document.addEventListener('click',e=>{
  const b=e.target.closest('button');if(!b)return;
  if(b.id==='applyNotice'&&notice){const n=notice;confirm('Xác minh thông báo thay đổi',`Cập nhật ${n.changes.length} trường của chuyến ${n.trip_code}? Thao tác này chưa phát hành lệnh tới lái xe.`,async()=>{showNotice(await post('/notices/'+n.id+'/apply',{confirmed:true}));staleAnalysis();await refresh();setOrderContext();toast('Đã cập nhật chuyến và tính lại rủi ro.');});}
  if(b.dataset.noticeDetail){const n=state.operations.notices.find(x=>x.id===b.dataset.noticeDetail);if(n)showNotice(n);}
  if(b.dataset.orderDetail){const o=state.operations.orders.find(x=>x.id===Number(b.dataset.orderDetail));if(!o)return;q('detailBody').innerHTML=`<h3>${esc(o.trip_code)} · v${o.version} · ${esc(o.driver)}</h3><p class="order-instructions">${esc(o.instructions)}</p><p>Trạng thái: ${orderStatuses[o.status]} · ${o.active?'Hiện hành':'Hết hiệu lực'}</p>${o.events.map(v=>`<div class="log-row"><b>${esc(({sent:'Phát hành & gửi',receive:'Đã nhận',confirm:'Đã xác nhận',reject:'Từ chối',execute:'Bắt đầu thực hiện'})[v.event])}</b><small>${stamp(v.sim_at)} điều hành · ${stamp(v.real_at)} thực tế</small>${v.reason?`<p>${esc(v.reason)}</p>`:''}</div>`).join('')}${o.superseded_at?`<p>Hết hiệu lực lúc ${stamp(o.superseded_at)}</p>`:''}`;q('detailDialog').showModal();}
  if(b.dataset.driverEvent){
   const o=state.operations.orders.find(x=>x.id===Number(b.dataset.order));if(!o)return;
   const event=b.dataset.driverEvent,driver=q('inboxDriver').value.trim();
   if(event==='reject'){
    q('driverRejectOrder').value=String(o.id);q('driverRejectDriver').value=driver;q('driverRejectReason').value='';q('driverRejectDialog').showModal();
   }else confirm('Xác nhận thao tác lái xe',`${driver} · ${o.trip_code} v${o.version}: ${event==='receive'?'ghi nhận đã nhận':event==='confirm'?'xác nhận đã hiểu nội dung':'bắt đầu thực hiện lệnh'}?`,async()=>{await post(`/orders/${o.id}/driver`,{driver,action:event,confirmed:true});staleAnalysis();await refresh();setOrderContext();toast('Đã ghi nhận phản hồi của lái xe.');});
  }
 });
 q('driverRejectForm').addEventListener('submit',e=>{e.preventDefault();busy(e.submitter,async()=>{await post(`/orders/${q('driverRejectOrder').value}/driver`,{driver:q('driverRejectDriver').value,action:'reject',reason:q('driverRejectReason').value,confirmed:true});q('driverRejectDialog').close();await refresh();toast('Đã ghi nhận từ chối; điều vận cần xử lý lại.');});});
 window.OperationsUI={render,showPilot};if(typeof snap!=='undefined'&&snap)render(snap);
})();

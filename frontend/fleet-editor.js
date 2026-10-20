"use strict";
(function(){
 const q=id=>document.getElementById(id);
 const checks={trailer_ok:'Loại moóc',capacity_ok:'Tải trọng',ready:'Sẵn sàng',hours_ok:'Giờ làm việc',cutoff_ok:'Cut-off'};
 const defaults=[{plate:'61C-172.28',tours:56.5,km:154.54,at_yard:false},{plate:'61C-277.11',tours:55,km:147.96,at_yard:false},{plate:'61C-304.40',tours:56.5,km:149.51,at_yard:true}].map(v=>({...v,...Object.fromEntries(Object.keys(checks).map(k=>[k,true]))}));
 let ready=false,dirty=false,version=0;
 function inputs(){return [...q('pilotInputs').querySelectorAll('tr')].map(row=>({plate:row.querySelector('[data-field=plate]').value.trim(),tours:row.querySelector('[data-field=tours]').value,km:row.querySelector('[data-field=km]').value,...Object.fromEntries(['at_yard',...Object.keys(checks)].map(k=>[k,row.querySelector('[data-field='+k+']').checked]))}));}
 function changed(){dirty=true;version++;q('pilotResult').innerHTML='';q('fleetSaveStatus').textContent='Có thay đổi chưa lưu';}
 function draw(vehicles,markDirty=true){
  q('pilotInputs').innerHTML=vehicles.map((v,i)=>`<tr><td><input data-field="plate" name="plate-${i}" aria-label="Biển số xe ${i+1}" required minlength="2" maxlength="30" value="${esc(v.plate)}" placeholder="Nhập biển số"></td><td><input data-field="tours" name="tours-${i}" aria-label="Tour xe ${i+1}" type="number" step="any" min="0" max="10000" required value="${esc(v.tours)}"></td><td><input data-field="km" name="km-${i}" aria-label="Km xe ${i+1}" type="number" step="any" min="0" max="100000" required value="${esc(v.km)}"></td><td><label><input data-field="at_yard" name="at_yard-${i}" type="checkbox" ${v.at_yard?'checked':''}> Có</label></td><td><div class="constraint-checks">${Object.entries(checks).map(([k,label])=>`<label><input data-field="${k}" name="${k}-${i}" type="checkbox" ${v[k]?'checked':''}> ${label}</label>`).join('')}</div></td><td><button class="table-btn delete" type="button" data-fleet-delete="${i}" aria-label="Xóa xe ${i+1}">Xóa</button></td></tr>`).join('');
  q('fleetCount').textContent=vehicles.length+' xe trong danh sách';q('fleetAnalyze').disabled=!vehicles.length;q('fleetSave').disabled=!vehicles.length;
  if(markDirty)changed();
 }
 function data(){
  if(!q('pilotForm').reportValidity())return null;
  const vehicles=inputs().map(v=>({...v,tours:Number(v.tours),km:Number(v.km)}));
  if(!vehicles.length){toast('Thêm ít nhất một xe trước khi phân tích.',true);return null;}
  const plates=vehicles.map(v=>v.plate.toLocaleLowerCase());
  if(new Set(plates).size!==plates.length){toast('Biển số xe bị trùng. Kiểm tra lại danh sách.',true);return null;}
  return {vehicles};
 }
 async function save(payload,revision){
  await api('/pilot/fleet',{method:'PUT',body:JSON.stringify(payload)});
  if(version===revision){dirty=false;q('fleetSaveStatus').textContent='Đã lưu '+payload.vehicles.length+' xe';}
 }
 async function load(){
  try{const r=await api('/pilot/fleet');draw(r.vehicles,false);q('fleetSaveStatus').textContent='Đã tải danh sách';ready=true;}
  catch(e){draw(defaults,false);ready=true;q('fleetSaveStatus').textContent='Chưa tải được danh sách đã lưu';toast(e.message,true);}
 }
 q('pilotInputs').addEventListener('input',changed);
 q('pilotInputs').addEventListener('click',e=>{const b=e.target.closest('[data-fleet-delete]');if(!b)return;const rows=inputs();rows.splice(Number(b.dataset.fleetDelete),1);draw(rows);});
 q('fleetAdd').addEventListener('click',()=>{if(!ready)return;const rows=inputs();rows.push({plate:'',tours:0,km:0,at_yard:false,...Object.fromEntries(Object.keys(checks).map(k=>[k,false]))});draw(rows);q('pilotInputs').lastElementChild.querySelector('input').focus();});
 q('fleetSave').addEventListener('click',()=>{const p=data();if(p)busy(q('fleetSave'),async()=>{await save(p,version);toast('Đã lưu danh sách xe.');});});
 q('fleetImport').addEventListener('click',()=>{if(ready)q('fleetFile').click();});
 q('fleetFile').addEventListener('change',()=>busy(q('fleetImport'),async()=>{
  const file=q('fleetFile').files[0];if(!file)return;
  try{
   if(file.size>5000000)throw Error('CSV tối đa 5 MB.');
   const startVersion=version;const text=await file.text();const r=await post('/pilot/fleet/import',{text});
   if(startVersion!==version)throw Error('Danh sách đã thay đổi trong lúc đọc file. Chọn lại CSV để nhập.');
   confirm('Nhập danh sách CSV',`Thay danh sách đang nhập bằng ${r.vehicles.length} xe từ file CSV? Chọn Phân tích hoặc Lưu danh sách để lưu lại.`,()=>{draw(r.vehicles);toast('Đã đọc '+r.vehicles.length+' xe từ CSV.');});
  }finally{q('fleetFile').value='';}
 }));
 q('pilotForm').addEventListener('submit',e=>{e.preventDefault();const p=data();if(!p)return;const startVersion=version;busy(e.submitter,async()=>{
  const r=await post('/pilot/analyze',p);
  if(version!==startVersion){toast('Dữ liệu đã đổi. Bấm Phân tích lại để có kết quả mới.',true);return;}
  await save(p,startVersion);if(version===startVersion)window.OperationsUI.showPilot(r);
 });});
 window.addEventListener('demoReset',()=>{version++;dirty=false;ready=false;q('pilotResult').innerHTML='';load();});
 window.addEventListener('beforeunload',e=>{if(dirty){e.preventDefault();e.returnValue='';}});
 load();
})();

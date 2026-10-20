const vm=require('node:vm'),fs=require('node:fs'),assert=require('node:assert/strict');
const elements={};let saved={},lastLayers=[];
function el(id){return elements[id]??={value:'',textContent:'',hidden:false,disabled:false,attrs:{},listeners:{},addEventListener(k,f){this.listeners[k]=f;},setAttribute(k,v){this.attrs[k]=v;},getAttribute(k){return this.attrs[k];},set innerHTML(v){this.html=v;if(id==='mapTrip')this.value=(v.match(/value="([^"]+)"/)||[])[1]||'';},closest(){return {classList:{toggle:()=>true}}}};}
const context={document:{getElementById:el,querySelectorAll:()=>[],addEventListener(){}},window:{addEventListener(){}},setInterval(){},URL,URLSearchParams,Number,JSON,localStorage:{getItem:k=>saved[k],setItem:(k,v)=>saved[k]=v},requestAnimationFrame:f=>f(),ResizeObserver:class{observe(){}},L:{map(){return {setView(){return this},fitBounds(){},invalidateSize(){},on(){return this}}},tileLayer(){return {on(){return this},addTo(){}}},featureGroup(){return {addTo(){return this},clearLayers(){lastLayers=[]},getLayers:()=>lastLayers,getBounds(){return []}}},divIcon:o=>o,marker(p,o){return {bindPopup(){return this},addTo(){lastLayers.push({p,o})}}}}};context.window.L=context.L;
vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../../frontend/map.js'),'utf8'),context);
const m=context.window.DispatchMap; m.setMode("route");
assert.equal(m.parseCoordinate('91, 100'),null);assert.equal(m.parseCoordinate(',100'),null);assert.equal(m.parseCoordinate('NaN,100'),null);assert.equal(m.parseCoordinate('10,181'),null);assert.equal(JSON.stringify(m.parseCoordinate('10.75, 106.79')),'[10.75,106.79]');
const trips=[{id:1,code:'UI-1',origin:'KCN Sóng Thần',destination:'Cảng Cát Lái'}];m.update(trips);assert.equal(lastLayers.length,2);assert.match(el('googleDirections').href,/origin=10.901/);
el('mapOrigin').value='10.8,106.8';el('mapDestination').value='10.7,106.7';el('mapCoordinates').listeners.submit({preventDefault(){}});assert.match(el('googleDirections').href,/origin=10.8/);assert.equal(lastLayers.length,2);assert.ok(Object.keys(saved).length);
el('mapClear').listeners.click();assert.match(el('googleDirections').href,/origin=10.901/);
m.update([{id:2,code:'UI-2',origin:'Kho chưa rõ',destination:'Nơi giao chưa rõ'}]);assert.equal(lastLayers.length,0);assert.match(el('mapLocationNote').textContent,/Chưa xác định/);
m.update([]);assert.equal(el('googleDirections').hidden,true);assert.equal(lastLayers.length,0);
console.log('PASS: coordinate validation, reference points, Google link, saving/clearing positions, unknown addresses, empty trips (DOM/Leaflet mocks).');

const sampleGPS=[{vehicle_id:'TRUCK-MOVE',speed_kmh:35,source_updated_at:new Date().toISOString()},{vehicle_id:'TRUCK-STOP',speed_kmh:0,source_updated_at:new Date().toISOString()},{vehicle_id:'TRUCK-OLD',speed_kmh:0,source_updated_at:new Date(Date.now()-600000).toISOString()}];
assert.equal(m.filteredGPS(sampleGPS,'truck','all').length,3);
assert.equal(m.filteredGPS(sampleGPS,'stop','stopped').length,1);
assert.equal(m.filteredGPS(sampleGPS,'','stale')[0].vehicle_id,'TRUCK-OLD');
assert.equal(m.filteredGPS(sampleGPS,'','moving')[0].vehicle_id,'TRUCK-MOVE');
assert.equal(m.filteredGPS(sampleGPS,'missing','all').length,0);
console.log('PASS: vehicle search and status filters, stale position priority.');

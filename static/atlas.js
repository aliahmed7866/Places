(() => {
  'use strict';
  const {catalog,flag,fmt,node,req,showEditor,records,paintMap}=window.placesAtlas;
  const $=id=>document.getElementById(id), panel=$('country-panel');
  const regions={World:[0,20,1],Europe:[18,52,2.4],Africa:[20,3,1.6],Asia:[90,35,1.5],'North America':[-105,40,1.5],'South America':[-60,-20,1.7],Oceania:[150,-20,1.7]};
  let svg,metadata={},selected=null,requestId=0,dragged=false,features=[],rotation=[0,-20,0],magnification=1,frame=0;
  const pointers=new Map();let gesture;
  const projection=d3.geoOrthographic().clipAngle(90).precision(.4), path=d3.geoPath(projection);
  const surface=$('map-window'), overlay=node('div','','globe-labels');overlay.setAttribute('aria-hidden','true');
  const measure=document.createElement('canvas').getContext('2d');measure.font='600 13px system-ui';
  function draw(){if(!frame)frame=requestAnimationFrame(renderGlobe);}
  function renderGlobe(){
    frame=0;if(!svg||!surface.clientWidth)return;
    const w=surface.clientWidth,h=surface.clientHeight,r=Math.min(w,h)*.44*magnification;
    svg.setAttribute('viewBox',`0 0 ${w} ${h}`);svg.dataset.zoom=magnification.toFixed(3);svg.dataset.rotation=rotation.join(',');
    projection.translate([w/2,h/2]).scale(r).rotate(rotation);
    svg.querySelectorAll('path[data-code]').forEach((p,i)=>{const d=path(features[i]);p.setAttribute('d',d||'');p.setAttribute('tabindex',d?'0':'-1');});
    for(const id of ['globe-ocean','globe-shade']){const c=svg.querySelector('#'+id);c.setAttribute('cx',w/2);c.setAttribute('cy',h/2);c.setAttribute('r',r);}
    svg.querySelector('#globe-grid').setAttribute('d',path(d3.geoGraticule10()));
    overlay.replaceChildren();const placed=[],center=[-rotation[0],-rotation[1]];
    const candidates=Object.entries(metadata).sort(([a],[b])=>Number(b===selected)-Number(a===selected));
    for(const [code,c]of candidates){
      const point=[c.label[0]/2.5-180,90-c.label[1]/2.5];
      if(d3.geoDistance(point,center)>1.30)continue;
      const [x,y]=projection(point),text=catalog.get(code)||c.name,width=measure.measureText(text).width+14,height=24;
      if(x-width/2<3||x+width/2>w-3||y-height/2<3||y+height/2>h-3)continue;
      const rect=[x-width/2,y-height/2,x+width/2,y+height/2];
      if(placed.some(b=>rect[0]<b[2]+5&&rect[2]>b[0]-5&&rect[1]<b[3]+5&&rect[3]>b[1]-5))continue;
      const label=node('span',text,code===selected?'selected':'');label.style.left=x+'px';label.style.top=y+'px';overlay.append(label);placed.push(rect);
    }
  }
  function zoom(factor){magnification=Math.max(1,Math.min(14,magnification/factor));draw();}
  function progress(){const region=$('atlas-region').value,codes=Object.keys(metadata).filter(c=>region==='World'||metadata[c].continent===region);const visited=new Set(records().filter(r=>r.status==='visited').map(r=>r.country));const count=codes.filter(c=>visited.has(c)).length;$('atlas-progress').textContent=`${region} · ${count} of ${codes.length} mapped countries & territories visited · ${codes.length?Math.round(count/codes.length*100):0}%`;}
  function focusCountry(code){const c=metadata[code];if(!c)return;rotation=[180-c.label[0]/2.5,c.label[1]/2.5-90,0];magnification=Math.max(1.5,Math.min(10,500/Math.max(20,c.bounds[2],c.bounds[3])));draw();}
  function button(text,handler,cls=''){const b=node('button',text,cls);b.type='button';b.onclick=handler;return b;}
  async function select(code,focus=true){
    selected=code;const token=++requestId;if(focus)focusCountry(code);
    svg?.querySelectorAll('path[data-code]').forEach(p=>p.classList.toggle('selected',p.dataset.code===code));
    panel.replaceChildren(node('p',metadata[code]?.continent||'EXPLORE','kicker'),node('h2',`${flag(code)} ${catalog.get(code)||code}`));
    const rows=records().filter(r=>r.country===code);
    panel.append(node('p',`${rows.filter(r=>r.status==='visited').length} visited · ${rows.filter(r=>r.status==='planned').length} planned · ${rows.filter(r=>r.status==='wishlist').length} wishlist`));
    const actions=node('div','','country-actions');actions.append(button('＋ Add a place',()=>showEditor(null,{country:code}),'primary'),button('Plan a trip',()=>showEditor(null,{country:code,status:'planned'})));panel.append(actions);
    const history=node('div','','country-history');
    for(const r of [...rows].sort((a,b)=>(b.start_date||'').localeCompare(a.start_date||''))){const b=button('',()=>showEditor(r),'country-entry');b.append(node('strong',r.place||catalog.get(code)),node('span',`${r.status} · ${r.start_date?fmt(r.start_date):'Undated'}${r.end_date&&r.end_date!==r.start_date?' – '+fmt(r.end_date):''}`));if(r.notes)b.append(node('p',r.notes));history.append(b);}
    if(!rows.length)history.append(node('p','No memories here yet. Add a visit or start planning.'));panel.append(history);
    const media=node('section','','country-media');media.append(node('h3','Country memories'));panel.append(media);
    try{
      let profile=await req(`/api/countries/${code}`);if(token!==requestId)return;
      const img=node('img');img.alt=`Your photo from ${catalog.get(code)}`;img.hidden=!profile.photo_url;if(profile.photo_url)img.src=profile.photo_url;media.append(img);
      const link=node('a','Open Instagram ↗');link.target='_blank';link.rel='noopener noreferrer';
      const sync=()=>{link.hidden=!profile.instagram_url;link.href=profile.instagram_url||'#';img.hidden=!profile.photo_url;if(profile.photo_url)img.src=profile.photo_url;};sync();media.append(link);
      const form=node('form'),label=node('label','Instagram Highlight or profile link'),input=node('input');input.type='url';input.placeholder='https://www.instagram.com/stories/highlights/…';input.value=profile.instagram_url;label.append(input);form.append(label);const save=node('button','Save link');save.type='submit';form.append(save);media.append(form);
      const photoLabel=node('label','Add a saved cover photo'),file=node('input');file.type='file';file.accept='image/jpeg,image/png';photoLabel.append(file);media.append(photoLabel);
      const message=node('p','','calendar-note');message.setAttribute('role','status');media.append(message);
      const update=async data=>{profile=await req(`/api/countries/${code}`,{method:'PUT',body:JSON.stringify(data)});sync();message.textContent='Saved.';};
      form.onsubmit=async e=>{e.preventDefault();save.disabled=true;try{await update({instagram_url:input.value});}catch(e){message.textContent=e.message;}finally{save.disabled=false;}};
      file.onchange=async()=>{const photo=file.files[0];if(!photo)return;file.disabled=true;message.textContent='Preparing photo…';let url;
        try{if(photo.size>20*1024*1024)throw Error('Choose a photo smaller than 20 MB.');url=URL.createObjectURL(photo);const image=new Image();image.src=url;await image.decode();const scale=Math.min(1,1600/Math.max(image.width,image.height)),canvas=document.createElement('canvas');canvas.width=Math.round(image.width*scale);canvas.height=Math.round(image.height*scale);canvas.getContext('2d').drawImage(image,0,0,canvas.width,canvas.height);await update({photo_base64:canvas.toDataURL('image/jpeg',.82).split(',')[1]});}catch(e){message.textContent=e.message||'Could not load this photo.';}finally{if(url)URL.revokeObjectURL(url);file.disabled=false;file.value='';}};
      media.append(button('Remove photo',async()=>{try{await update({photo_base64:null});}catch(e){message.textContent=e.message;}}));
      media.append(node('p','Save a photo from your country memories and add its Highlight link. The link opens Instagram; photos do not sync automatically.','calendar-note'));
    }catch(e){if(token===requestId)media.append(node('p',e.message,'error'));}
  }
  $('atlas-search').oninput=e=>{const q=e.target.value.trim().toLowerCase(),results=$('atlas-results');results.replaceChildren();if(!q)return;const matches=[...catalog].filter(([code,name])=>name.toLowerCase().includes(q)||code.toLowerCase()===q);for(const [code,name]of matches.slice(0,12))results.append(button(`${flag(code)} ${name}`,()=>{select(code);results.replaceChildren();$('atlas-search').value=name;}));if(!matches.length)results.append(node('p','No matching countries.'));};
  $('atlas-region').onchange=()=>{const [lon,lat,z]=regions[$('atlas-region').value];rotation=[-lon,-lat,0];magnification=z;draw();progress();};
  $('zoom-in').onclick=()=>zoom(.65);$('zoom-out').onclick=()=>zoom(1.5);$('zoom-reset').onclick=()=>{rotation=[0,-20,0];magnification=1;$('atlas-region').value='World';draw();progress();};
  window.addEventListener('places:changed',()=>{paintMap();progress();if(selected)select(selected,false);});
  Promise.all([req('/static/globe-countries.json'),req('/static/atlas-countries.json')]).then(([world,data])=>{
    metadata=data;features=world.features;
    $('world-map').innerHTML='<svg xmlns="http://www.w3.org/2000/svg" class="world-svg" role="group" aria-label="Interactive Earth globe"><defs><radialGradient id="ocean-light" cx="32%" cy="26%" r="80%"><stop stop-color="#74b4cb"/><stop offset=".65" stop-color="#326986"/><stop offset="1" stop-color="#173e59"/></radialGradient><radialGradient id="earth-shadow" cx="32%" cy="25%" r="80%"><stop offset=".5" stop-color="#04192c" stop-opacity="0"/><stop offset="1" stop-color="#04192c" stop-opacity=".55"/></radialGradient></defs><circle id="globe-ocean" fill="url(#ocean-light)"/><path id="globe-grid" fill="none" stroke="#ffffff" stroke-opacity=".15"/><g id="globe-land"></g><circle id="globe-shade" fill="url(#earth-shadow)" pointer-events="none"/></svg>';
    svg=$('world-map').querySelector('svg');$('world-map').append(overlay);
    for(const feature of features){const code=feature.properties.code,p=document.createElementNS('http://www.w3.org/2000/svg','path');p.dataset.code=code;p.setAttribute('role','button');p.setAttribute('aria-label',catalog.get(code)||code);svg.querySelector('#globe-land').append(p);
      const activate=()=>{if(catalog.has(code))select(code);};p.onclick=()=>{if(!dragged)activate();};p.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}};p.onmouseenter=p.onfocus=()=>{$('map-caption').textContent=catalog.get(code)||code;};
    }draw();paintMap();progress();new ResizeObserver(draw).observe(surface);
    function snapshot(){const p=[...pointers.values()];gesture={rotation:[...rotation],zoom:magnification,center:[p.reduce((s,v)=>s+v[0],0)/p.length,p.reduce((s,v)=>s+v[1],0)/p.length],distance:p.length>1?Math.hypot(p[0][0]-p[1][0],p[0][1]-p[1][1]):0};}
    surface.onpointerdown=e=>{if(e.button!==0)return;if(!pointers.size)dragged=false;pointers.set(e.pointerId,[e.clientX,e.clientY]);snapshot();};
    surface.onpointermove=e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,[e.clientX,e.clientY]);const p=[...pointers.values()],cx=p.reduce((s,v)=>s+v[0],0)/p.length,cy=p.reduce((s,v)=>s+v[1],0)/p.length,dx=cx-gesture.center[0],dy=cy-gesture.center[1];if(Math.abs(dx)+Math.abs(dy)>5||p.length>1){dragged=true;surface.setPointerCapture(e.pointerId);}const sensitivity=100/(Math.min(surface.clientWidth,surface.clientHeight)*gesture.zoom*.44);rotation=[gesture.rotation[0]+dx*sensitivity,Math.max(-85,Math.min(85,gesture.rotation[1]-dy*sensitivity)),0];if(p.length>1&&gesture.distance)magnification=Math.max(1,Math.min(14,gesture.zoom*Math.hypot(p[0][0]-p[1][0],p[0][1]-p[1][1])/gesture.distance));draw();};
    const end=e=>{pointers.delete(e.pointerId);if(pointers.size)snapshot();};surface.onpointerup=end;surface.onpointercancel=end;surface.onpointerleave=e=>{if(!surface.hasPointerCapture(e.pointerId))end(e);};
    surface.addEventListener('wheel',e=>{if(!e.ctrlKey&&document.activeElement!==surface)return;e.preventDefault();zoom(e.deltaY>0?1.15:.87);},{passive:false});
    surface.onkeydown=e=>{const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,1],ArrowDown:[0,-1]}[e.key];if(delta){e.preventDefault();rotation[0]+=delta[0]*10/magnification;rotation[1]=Math.max(-85,Math.min(85,rotation[1]+delta[1]*10/magnification));draw();}else if(['+','=','-'].includes(e.key)){e.preventDefault();zoom(e.key==='-'?1.5:.65);}};
  }).catch(()=>{$('map-caption').textContent='Globe unavailable. Search for a country or use Add a place.';});
})();

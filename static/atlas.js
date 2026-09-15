(() => {
  'use strict';
  const {catalog,flag,fmt,node,req,showEditor,records,paintMap}=window.placesAtlas;
  const $=id=>document.getElementById(id), panel=$('country-panel');
  const regions={World:[0,10,900,410],Europe:[400,35,230,150],Africa:[400,130,220,215],Asia:[510,25,370,280],'North America':[0,10,430,280],'South America':[205,210,200,220],Oceania:[715,205,185,190]};
  let svg,metadata={},selected=null,box=[...regions.World],requestId=0,dragged=false;
  const pointers=new Map();let gesture;
  function draw(){
    box[0]=Math.max(-box[2]*.3,Math.min(900-box[2]*.7,box[0]));
    box[1]=Math.max(-box[3]*.3,Math.min(450-box[3]*.7,box[1]));
    if(!svg)return;svg.setAttribute('viewBox',box.join(' '));
    let labels=svg.querySelector('.atlas-labels');if(!labels){labels=document.createElementNS('http://www.w3.org/2000/svg','g');labels.setAttribute('class','atlas-labels');labels.setAttribute('aria-hidden','true');svg.append(labels);}labels.replaceChildren();
    if(box[2]>350)return;
    const placed=[];
    for(const [code,c]of Object.entries(metadata)){
      const [x,y]=c.label;if(x<box[0]||x>box[0]+box[2]||y<box[1]||y>box[1]+box[3]||placed.some(([a,b])=>Math.abs(a-x)<box[2]*.11&&Math.abs(b-y)<box[3]*.07))continue;
      const t=document.createElementNS('http://www.w3.org/2000/svg','text');t.setAttribute('x',x);t.setAttribute('y',y);t.setAttribute('font-size',box[2]*.014);t.textContent=catalog.get(code)||c.name;labels.append(t);placed.push([x,y]);
    }
  }
  function zoom(factor){const width=Math.max(12,Math.min(900,box[2]*factor)),ratio=width/box[2];box=[box[0]+box[2]*(1-ratio)/2,box[1]+box[3]*(1-ratio)/2,width,box[3]*ratio];draw();}
  function progress(){const region=$('atlas-region').value,codes=Object.keys(metadata).filter(c=>region==='World'||metadata[c].continent===region);const visited=new Set(records().filter(r=>r.status==='visited').map(r=>r.country));const count=codes.filter(c=>visited.has(c)).length;$('atlas-progress').textContent=`${region} · ${count} of ${codes.length} mapped countries & territories visited · ${codes.length?Math.round(count/codes.length*100):0}%`;}
  function focusCountry(code){const b=metadata[code]?.bounds;if(!b)return;const width=Math.max(25,b[2]*1.5,b[3]*2.2);box=[b[0]+b[2]/2-width/2,b[1]+b[3]/2-width*.3,width,width*.6];draw();}
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
  $('atlas-region').onchange=()=>{box=[...regions[$('atlas-region').value]];draw();progress();};
  $('zoom-in').onclick=()=>zoom(.65);$('zoom-out').onclick=()=>zoom(1.5);$('zoom-reset').onclick=()=>{box=[...regions.World];$('atlas-region').value='World';draw();progress();};
  window.addEventListener('places:changed',()=>{paintMap();progress();if(selected)select(selected,false);});
  Promise.all([fetch('/static/places-world.svg').then(r=>{if(!r.ok)throw Error();return r.text();}),req('/static/atlas-countries.json')]).then(([markup,data])=>{
    metadata=data;$('world-map').innerHTML=markup;svg=$('world-map').querySelector('svg');draw();paintMap();progress();
    svg.querySelectorAll('path[data-code]').forEach(path=>{const code=path.dataset.code;const activate=()=>{if(catalog.has(code))select(code);};path.onclick=()=>{if(!dragged)activate();};path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}};path.onmouseenter=path.onfocus=()=>{$('map-caption').textContent=catalog.get(code)||code;};});
    const surface=$('map-window');
    function snapshot(){const p=[...pointers.values()];gesture={box:[...box],center:[p.reduce((s,v)=>s+v[0],0)/p.length,p.reduce((s,v)=>s+v[1],0)/p.length],distance:p.length>1?Math.hypot(p[0][0]-p[1][0],p[0][1]-p[1][1]):0};}
    surface.onpointerdown=e=>{if(e.button!==0)return;dragged=false;pointers.set(e.pointerId,[e.clientX,e.clientY]);snapshot();};
    surface.onpointermove=e=>{if(!pointers.has(e.pointerId))return;pointers.set(e.pointerId,[e.clientX,e.clientY]);const p=[...pointers.values()],cx=p.reduce((s,v)=>s+v[0],0)/p.length,cy=p.reduce((s,v)=>s+v[1],0)/p.length,dx=cx-gesture.center[0],dy=cy-gesture.center[1];if(Math.abs(dx)+Math.abs(dy)>5||p.length>1){dragged=true;surface.setPointerCapture(e.pointerId);}const scale=p.length>1&&gesture.distance?gesture.distance/Math.max(1,Math.hypot(p[0][0]-p[1][0],p[0][1]-p[1][1])):1;const width=Math.max(12,Math.min(900,gesture.box[2]*scale)),ratio=width/gesture.box[2];const rect=svg.getBoundingClientRect(),unit=Math.max(gesture.box[2]/rect.width,gesture.box[3]/rect.height);box=[gesture.box[0]-dx*unit+gesture.box[2]*(1-ratio)/2,gesture.box[1]-dy*unit+gesture.box[3]*(1-ratio)/2,width,gesture.box[3]*ratio];draw();};
    const end=e=>{pointers.delete(e.pointerId);if(pointers.size)snapshot();};surface.onpointerup=end;surface.onpointercancel=end;surface.onpointerleave=e=>{if(!surface.hasPointerCapture(e.pointerId))end(e);};
    surface.addEventListener('wheel',e=>{if(!e.ctrlKey&&document.activeElement!==surface)return;e.preventDefault();zoom(e.deltaY>0?1.15:.87);},{passive:false});
    surface.onkeydown=e=>{const delta={ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[e.key];if(delta){e.preventDefault();box[0]+=delta[0]*box[2]*.1;box[1]+=delta[1]*box[3]*.1;draw();}else if(['+','=','-'].includes(e.key)){e.preventDefault();zoom(e.key==='-'?1.5:.65);}};
  }).catch(()=>{$('map-caption').textContent='Map unavailable. Search for a country or use Add a place.';});
})();

(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const root = document.querySelector('.shell'), api = root.dataset.api;
  const catalog = new Map(JSON.parse($('countries-data').textContent).map(c => [c.code, c.name]));
  const dialog = $('place-dialog'), form = $('place-form');
  const field = name => form.elements.namedItem(name);
  const today = new Date();
  const localDate = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  let records = [], filter = 'all', editing = null, year = Number(root.dataset.currentYear);
  let month = today.getMonth(), overview = false, calendarRequest = 0, zoom = 1;
  const flag = code => code.replace(/./g, c => String.fromCodePoint(127397+c.charCodeAt(0)));
  const fmt = d => d ? new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}) : '';
  const labels = {visited:'Visited', planned:'Planned', wishlist:'Wishlist'};
  function node(tag, text, className) {
    const el = document.createElement(tag);
    if (text) el.textContent = text;
    if (className) el.className = className;
    return el;
  }
  async function req(url, options={}) {
    const response = await fetch(url, {...options, headers:{'Content-Type':'application/json'}, cache:'no-store'});
    if (!response.ok) {
      let body = {}; try { body = await response.json(); } catch {}
      throw new Error(body.error || 'Could not complete the request. Please try again.');
    }
    return response.status === 204 ? null : response.json();
  }
  function travelDays(rows) {
    const ranges = rows.filter(r=>r.start_date).map(r=>[Date.parse(r.start_date+'T00:00:00Z'),Date.parse((r.end_date||r.start_date)+'T00:00:00Z')]).sort((a,b)=>a[0]-b[0]);
    let total=0,start=null,end=null;
    for (const [a,b] of ranges) {
      if(start===null){start=a;end=b;}
      else if(a<=end+86400000) end=Math.max(end,b);
      else {total+=(end-start)/86400000+1;start=a;end=b;}
    }
    return total+(start===null?0:(end-start)/86400000+1);
  }
  function switchView(view) {
    document.querySelectorAll('[data-view]').forEach(b=>{
      const active=b.dataset.view===view;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));
    });
    document.querySelectorAll('.view').forEach(v=>{v.hidden=v.id!==`${view}-view`;});
    if(view==='calendar') renderCalendar();
  }
  function toggleDates() {
    const wishlist=field('status').value==='wishlist';
    $('date-fields').hidden=wishlist;
    field('start_date').required=field('status').value==='planned';
  }
  function showEditor(record=null, defaults={}) {
    editing=record?.id??null;form.reset();
    for(const key of ['country','place','status','start_date','end_date','notes'])
      field(key).value=record?.[key]??defaults[key]??(key==='status'?'visited':'');
    $('dialog-title').textContent=editing?'Edit place':defaults.start_date?`Add a flag · ${fmt(defaults.start_date)}`:'Add a place';
    $('delete-place').hidden=!editing;$('form-error').textContent='';
    $('day-entries').replaceChildren();$('day-entries').hidden=true;
    toggleDates();if(!dialog.open) dialog.showModal();
  }
  function showDay(day) {
    showEditor(null,{start_date:day,end_date:day,status:day>localDate(today)?'planned':'visited'});
    const entries=records.filter(r=>r.status!=='wishlist'&&r.start_date&&r.start_date<=day&&(r.end_date||r.start_date)>=day);
    if(entries.length) {
      const holder=$('day-entries');holder.hidden=false;holder.append(node('p','On this day · tap to edit'));
      for(const r of entries) {
        const b=node('button',`${flag(r.country)} ${catalog.get(r.country)||r.country}${r.place?' · '+r.place:''} · ${labels[r.status]}`);
        b.type='button';b.onclick=()=>showEditor(r);holder.append(b);
      }
      holder.append(node('p','Add another country below.'));
    }
  }
  function paintMap() {
    const sets=Object.fromEntries(Object.keys(labels).map(status=>[status,new Set(records.filter(r=>r.status===status).map(r=>r.country))]));
    document.querySelectorAll('.world-svg path').forEach(path=>{
      const code=path.dataset.code;
      const status=['visited','planned','wishlist'].find(s=>sets[s].has(code));
      for(const s of Object.keys(labels))path.classList.toggle(s,s===status);
      path.setAttribute('aria-label',`${catalog.get(code)||code}${status?' · '+labels[status]:''}`);
    });
  }
  function renderJournal() {
    const visited=records.filter(r=>r.status==='visited');
    $('countries-total').textContent=new Set(visited.map(r=>r.country)).size;
    $('days-total').textContent=travelDays(visited);$('trips-total').textContent=visited.length;
    $('wishlist-total').textContent=records.filter(r=>r.status==='wishlist').length;
    paintMap();
    const q=$('search').value.trim().toLowerCase();
    const shown=records.filter(r=>(filter==='all'||r.status===filter)&&`${catalog.get(r.country)||r.country} ${r.place} ${r.notes}`.toLowerCase().includes(q));
    const cards=$('cards');cards.replaceChildren();
    if(!shown.length)cards.append(node('div',records.length?'No matching places.':'Add your first place from the map or plan a trip.','empty'));
    for(const r of shown) {
      const b=node('button','',`card ${r.status}`);b.type='button';
      b.append(node('span',`${flag(r.country)} ${catalog.get(r.country)||r.country}`,'country'),node('h3',r.place||catalog.get(r.country)||r.country));
      if(r.notes)b.append(node('p',r.notes));
      const range=r.start_date?`${fmt(r.start_date)}${r.end_date&&r.end_date!==r.start_date?' – '+fmt(r.end_date):''}`:'No date';
      const footer=node('footer');footer.append(node('span',labels[r.status]),node('span',range));b.append(footer);
      b.onclick=()=>showEditor(r);cards.append(b);
    }
  }
  function monthMarkup(m, dayMap, shownYear) {
    const first=new Date(shownYear,m,1),last=new Date(shownYear,m+1,0);
    const wrap=node('section','','month');wrap.append(node('h3',first.toLocaleDateString('en-GB',{month:'long'})));
    const grid=node('div','','month-grid');
    for(const d of ['M','T','W','T','F','S','S'])grid.append(node('span',d,'dow'));
    for(let i=0;i<(first.getDay()+6)%7;i++)grid.append(node('span'));
    for(let day=1;day<=last.getDate();day++) {
      const key=`${shownYear}-${String(m+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
      const cell=node('button','','day');cell.type='button';cell.dataset.date=key;cell.append(node('span',String(day),'day-number'));
      const visits=dayMap[key]||[];
      cell.classList.toggle('travel',visits.some(v=>v.status==='visited'));
      cell.classList.toggle('planned',visits.some(v=>v.status==='planned'));
      if(key===localDate(today))cell.setAttribute('aria-current','date');
      const codes=[...new Set(visits.map(v=>v.country))];
      if(codes.length) {
        const fs=node('span','','flags');
        codes.slice(0,2).forEach(c=>fs.append(node('span',flag(c))));
        if(codes.length>2)fs.append(node('small',`+${codes.length-2}`));
        cell.append(fs);
      }
      const detail=visits.map(v=>`${catalog.get(v.country)||v.country} (${labels[v.status]})`).join(', ');
      cell.setAttribute('aria-label',`${fmt(key)}${detail?' · '+detail:''} · Add or edit countries`);
      cell.title=detail;cell.onclick=()=>showDay(key);grid.append(cell);
    }
    wrap.append(grid);return wrap;
  }
  async function renderCalendar() {
    const requestId=++calendarRequest, shownYear=year, shownMonth=month, showAll=overview;
    $('calendar-year').textContent=shownYear;$('planner-year').value=shownYear;$('planner-month').value=shownMonth;
    $('planner-month').hidden=showAll;$('calendar-mode').textContent=showAll?'Month view':'Year overview';
    $('calendar-mode').setAttribute('aria-pressed',String(showAll));
    $('prev-year').disabled=year===1900&&(showAll||month===0);$('next-year').disabled=year===2200&&(showAll||month===11);
    try {
      const data=await req(`/api/calendar/${shownYear}`);if(requestId!==calendarRequest)return;
      const grid=$('year-grid');grid.replaceChildren();grid.classList.toggle('month-mode',!showAll);
      for(const m of showAll?Array.from({length:12},(_,i)=>i):[shownMonth])grid.append(monthMarkup(m,data.days,shownYear));
      const days=Object.entries(data.days).filter(([day])=>showAll||Number(day.slice(5,7))===shownMonth+1);
      const count=status=>days.filter(([,entries])=>entries.some(v=>v.status===status)).length;
      $('calendar-summary').textContent=`${count('planned')} planned days · ${count('visited')} visited days · ${new Set(days.flatMap(([,entries])=>entries.map(v=>v.country))).size} countries`;
    } catch(err) {if(requestId===calendarRequest){$('year-grid').replaceChildren();$('calendar-summary').textContent=err.message;}}
  }
  function changePeriod(delta) {
    const next=new Date(year+(overview?delta:0),month+(overview?0:delta),1);
    if(next.getFullYear()<1900||next.getFullYear()>2200)return;
    year=next.getFullYear();month=next.getMonth();renderCalendar();
  }
  $('prev-year').onclick=()=>changePeriod(-1);$('next-year').onclick=()=>changePeriod(1);
  $('planner-month').onchange=e=>{month=Number(e.target.value);renderCalendar();};
  $('planner-year').onchange=e=>{const value=Number(e.target.value);if(Number.isInteger(value)&&value>=1900&&value<=2200){year=value;renderCalendar();}else e.target.value=year;};
  $('calendar-mode').onclick=()=>{overview=!overview;renderCalendar();};
  $('add-place').onclick=()=>showEditor();$('close-dialog').onclick=()=>dialog.close();field('status').onchange=toggleDates;
  $('add-plan').onclick=()=>showEditor(null,{status:'planned',start_date:localDate(new Date(year,month,1)),end_date:''});
  $('plan-trip').onclick=()=>{switchView('calendar');showEditor(null,{status:'planned',start_date:localDate(today)});};
  $('search').oninput=renderJournal;
  document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>{x.classList.toggle('active',x===b);x.setAttribute('aria-pressed',String(x===b));});renderJournal();});
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));
  form.onsubmit=async e=>{
    e.preventDefault();$('save-place').disabled=true;$('form-error').textContent='';
    try {
      const result=await req(editing?`${api}/${editing}`:api,{method:editing?'PUT':'POST',body:JSON.stringify(Object.fromEntries(new FormData(form)))});
      records=records.filter(r=>r.id!==result.id);records.unshift(result.place);
      dialog.close();renderJournal();$('app-message').textContent='Saved.';
      if(!$('calendar-view').hidden)await renderCalendar();
    } catch(err){$('form-error').textContent=err.message;}finally{$('save-place').disabled=false;}
  };
  $('delete-place').onclick=async()=>{
    if(!confirm('Delete this place?'))return;$('delete-place').disabled=true;
    try{await req(`${api}/${editing}`,{method:'DELETE'});records=records.filter(r=>r.id!==editing);dialog.close();renderJournal();$('app-message').textContent='Deleted.';if(!$('calendar-view').hidden)await renderCalendar();}
    catch(err){$('form-error').textContent=err.message;}finally{$('delete-place').disabled=false;}
  };
  function setZoom(value){zoom=Math.max(1,Math.min(4,value));const svg=document.querySelector('.world-svg');if(svg)svg.style.width=`${zoom*100}%`;}
  $('zoom-in').onclick=()=>setZoom(zoom+.5);$('zoom-out').onclick=()=>setZoom(zoom-.5);
  $('zoom-reset').onclick=()=>{setZoom(1);$('map-window').scrollTo(0,0);};
  fetch('/static/places-world.svg').then(r=>{if(!r.ok)throw new Error();return r.text();}).then(svg=>{
    // Only the trusted, bundled SVG is inserted as markup; entry text uses textContent.
    $('world-map').innerHTML=svg;
    document.querySelectorAll('.world-svg path').forEach(path=>{
      const code=path.dataset.code;
      const activate=()=>{if(catalog.has(code))showEditor(null,{country:code});};
      path.onclick=activate;path.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate();}};
      path.onmouseenter=path.onfocus=()=>{$('map-caption').textContent=catalog.get(code)||path.getAttribute('aria-label');};
    });paintMap();
  }).catch(()=>{$('map-caption').textContent='Map unavailable. Use Add a place to choose any country.';});
  req(api).then(data=>{records=data.places;renderJournal();}).catch(err=>{$('app-message').textContent=err.message;});
})();

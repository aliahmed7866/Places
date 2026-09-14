(() => {
  'use strict';
  const root=document.querySelector('.shell');
  const api=root.dataset.api;
  const countries=JSON.parse(document.getElementById('countries-data').textContent);
  const catalog=new Map(countries.map(c=>[c.code,c.name]));
  const $=id=>document.getElementById(id);
  const dialog=$('place-dialog'),form=$('place-form');
  let records=[],filter='all',editing=null,year=Number(root.dataset.currentYear);
  const field=name=>form.elements.namedItem(name);
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const flag=code=>code.replace(/./g,c=>String.fromCodePoint(127397+c.charCodeAt(0)));
  const fmt=d=>d?new Date(d+'T12:00:00').toLocaleDateString('en-GB',{day:'numeric',month:'short',year:'numeric'}):'';
  async function req(url,options={}){const r=await fetch(url,{...options,headers:{'Content-Type':'application/json'},cache:'no-store'});if(!r.ok){let b={};try{b=await r.json()}catch{}throw new Error(b.error||'Something went wrong.')}return r.status===204?null:r.json()}
  function travelDays(rows){
    const ranges=rows.filter(r=>r.start_date).map(r=>[Date.parse(r.start_date+'T00:00:00Z'),Date.parse((r.end_date||r.start_date)+'T00:00:00Z')]).sort((a,b)=>a[0]-b[0]);
    let total=0,start=null,end=null;
    for(const [a,b] of ranges){if(start===null){start=a;end=b}else if(a<=end+86400000){end=Math.max(end,b)}else{total+=(end-start)/86400000+1;start=a;end=b}}
    return total+(start===null?0:(end-start)/86400000+1);
  }
  function showEditor(record=null){editing=record?.id??null;form.reset();for(const k of ['country','place','status','start_date','end_date','notes'])field(k).value=record?.[k]??(k==='status'?'visited':'');$('dialog-title').textContent=editing?'Edit place':'Add a place';$('delete-place').hidden=!editing;$('form-error').textContent='';toggleDates();dialog.showModal()}
  function toggleDates(){$('date-fields').hidden=field('status').value==='wishlist'}
  function renderJournal(){const visited=records.filter(r=>r.status==='visited');$('countries-total').textContent=new Set(visited.map(r=>r.country)).size;$('trips-total').textContent=visited.length;$('wishlist-total').textContent=records.filter(r=>r.status==='wishlist').length;$('days-total').textContent=travelDays(visited);const q=$('search').value.trim().toLowerCase();const shown=records.filter(r=>(filter==='all'||r.status===filter)&&`${catalog.get(r.country)||r.country} ${r.place} ${r.notes}`.toLowerCase().includes(q));const cards=$('cards');cards.replaceChildren();if(!shown.length){const e=document.createElement('div');e.className='empty';e.textContent=records.length?'No matching places.':'Add your first trip or wishlist place.';cards.append(e);return}for(const r of shown){const b=document.createElement('button');b.className='card';b.type='button';const country=catalog.get(r.country)||r.country;const range=r.start_date?(r.end_date&&r.end_date!==r.start_date?`${fmt(r.start_date)} – ${fmt(r.end_date)}`:fmt(r.start_date)):'No date';b.innerHTML=`<span class="country">${flag(r.country)} ${esc(country)}</span><h3>${esc(r.place||country)}</h3>${r.notes?`<p></p>`:''}<footer><span>${r.status==='visited'?'● Visited':'● Wishlist'}</span><span>${esc(range)}</span></footer>`;if(r.notes)b.querySelector('p').textContent=r.notes;b.onclick=()=>showEditor(r);cards.append(b)}}
  function monthMarkup(month,dayMap,shownYear){const first=new Date(shownYear,month,1),last=new Date(shownYear,month+1,0);const wrap=document.createElement('section');wrap.className='month';const h=document.createElement('h3');h.textContent=first.toLocaleDateString('en-GB',{month:'short'}).toUpperCase();wrap.append(h);const grid=document.createElement('div');grid.className='month-grid';['M','T','W','T','F','S','S'].forEach(x=>{const d=document.createElement('span');d.className='dow';d.textContent=x;grid.append(d)});const offset=(first.getDay()+6)%7;for(let i=0;i<offset;i++)grid.append(document.createElement('span'));for(let day=1;day<=last.getDate();day++){const cell=document.createElement('div');cell.className='day';cell.textContent=day;const key=`${shownYear}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;const visits=dayMap[key]||[];if(visits.length){cell.classList.add('travel');const fs=document.createElement('span');fs.className='flags';[...new Set(visits.map(v=>v.country))].slice(0,3).forEach(c=>{const s=document.createElement('span');s.textContent=flag(c);fs.append(s)});cell.append(fs);cell.title=visits.map(v=>`${catalog.get(v.country)||v.country}${v.place?' · '+v.place:''}`).join('\n')}grid.append(cell)}wrap.append(grid);return wrap}
  let calendarRequest=0;
  async function renderCalendar(){
    const requestId=++calendarRequest,shownYear=year;
    $('calendar-year').textContent=shownYear;
    $('prev-year').disabled=shownYear<=1900;$('next-year').disabled=shownYear>=2200;
    try{
      const data=await req(`/api/calendar/${shownYear}`);
      if(requestId!==calendarRequest)return;
      const grid=$('year-grid');grid.replaceChildren();
      for(let m=0;m<12;m++)grid.append(monthMarkup(m,data.days,shownYear));
      const entries=Object.values(data.days),count=entries.length;
      const countrySet=new Set(entries.flat().map(v=>v.country));
      $('calendar-summary').textContent=`${count} travel day${count===1?'':'s'} · ${countrySet.size} countr${countrySet.size===1?'y':'ies'}`;
    }catch(err){if(requestId===calendarRequest){$('year-grid').replaceChildren();$('calendar-summary').textContent=err.message}}
  }
  async function load(){const data=await req(api);records=data.places;renderJournal();await renderCalendar()}
  $('add-place').onclick=()=>showEditor();$('close-dialog').onclick=()=>dialog.close();field('status').onchange=toggleDates;$('search').oninput=renderJournal;
  document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll('[data-filter]').forEach(x=>x.classList.toggle('active',x===b));renderJournal()});
  document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('[data-view]').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.view').forEach(v=>{const on=v.id===`${b.dataset.view}-view`;v.hidden=!on;v.classList.toggle('active',on)})});
  $('prev-year').onclick=()=>{year=Math.max(1900,year-1);renderCalendar()};$('next-year').onclick=()=>{year=Math.min(2200,year+1);renderCalendar()};
  form.onsubmit=async e=>{e.preventDefault();$('save-place').disabled=true;$('form-error').textContent='';try{const data=Object.fromEntries(new FormData(form));const result=await req(editing?`${api}/${editing}`:api,{method:editing?'PUT':'POST',body:JSON.stringify(data)});const refreshed=await req(api);records=refreshed.places;dialog.close();renderJournal();await renderCalendar()}catch(err){$('form-error').textContent=err.message}finally{$('save-place').disabled=false}};
  $('delete-place').onclick=async()=>{if(!confirm('Delete this place?'))return;try{await req(`${api}/${editing}`,{method:'DELETE'});records=records.filter(r=>r.id!==editing);dialog.close();renderJournal();await renderCalendar()}catch(err){$('form-error').textContent=err.message}};
  load().catch(err=>{$('calendar-summary').textContent=err.message});
})();

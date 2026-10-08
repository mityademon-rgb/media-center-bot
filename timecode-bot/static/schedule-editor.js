/* Teacher schedule editor: one form, existing values, explicit deletion. */
let scheduleDraft=null,scheduleBusy=false;
const scheduleReadOnly=schedule;
const scheduleRenderOriginal=render;
render=function(){if(scheduleDraft&&tab==='schedule')return;return scheduleRenderOriginal();};
function schedulePaint(){renderDock();$('#app').innerHTML=schedule();}
function scheduleOpen(kind,id=null,seed=null){
  const row=id===null?null:(kind==='lesson'?state.lessons:state.changes).find(x=>x.id===id);
  scheduleDraft={kind,action:'save',lab:lab,weekday:0,start:'18:00',title:'',place:'',day:new Date().toLocaleDateString('sv-SE',{timeZone:'Europe/Moscow'}),cancelled:false,...(seed||{}),...(row||{}),original:row?{...row}:undefined};
  schedulePaint();$('#schedule-title')?.focus();
}
function scheduleClose(){if(scheduleBusy)return;scheduleDraft=null;schedulePaint();}
function scheduleCapture(form){
  const p=Object.fromEntries(new FormData(form));
  scheduleDraft={...scheduleDraft,...p,cancelled:form.elements.cancelled?.checked===true};
}
function scheduleCancelChange(form){scheduleCapture(form);schedulePaint();}
async function scheduleSave(event){
  event.preventDefault();if(scheduleBusy)return;scheduleCapture(event.target);
  if(scheduleDraft.kind==='override'&&state.changes.some(x=>x.lab===scheduleDraft.lab&&x.day===scheduleDraft.day&&x.id!==scheduleDraft.id)){
    if(!confirm('На эту дату уже есть изменение. Заменить его?'))return;
  }
  scheduleBusy=true;schedulePaint();
  try{
    await req('schedule-edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(scheduleDraft)});
    scheduleDraft=null;state=await req('state');toast('Сохранено. Сообщение об изменении поставлено в общую рассылку.');
  }catch(error){toast(error.message);}
  finally{scheduleBusy=false;schedulePaint();}
}
async function scheduleRemove(kind,id){
  if(scheduleBusy)return;
  const row=(kind==='lesson'?state.lessons:state.changes).find(x=>x.id===id);if(!row)return;
  const question=kind==='lesson'?`Удалить «${row.title}» (${row.start}) из постоянной недели? Отдельные изменения на даты сохранятся.`:`Убрать изменение на ${row.day}? На эту дату будет действовать обычное расписание.`;
  if(!confirm(question))return;scheduleBusy=true;schedulePaint();
  try{
    await req('schedule-edit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({kind,action:'remove',id,original:{...row}})});
    state=await req('state');toast('Удалено. Сообщение об изменении поставлено в общую рассылку.');
  }catch(error){toast(error.message);}
  finally{scheduleBusy=false;schedulePaint();}
}
function scheduleForm(){
  const d=scheduleDraft,disabled=scheduleBusy?'disabled':'';
  return `<article class="card"><h2>${d.kind==='lesson'?(d.id?'Изменить занятие':'Добавить занятие'):'Изменение на дату'}</h2>
  <form onsubmit="scheduleSave(event)" oninput="scheduleCapture(this)">
  <label class="field">Группа<select name="lab" ${disabled}><option value="kids" ${d.lab==='kids'?'selected':''}>Kids Lab</option><option value="media" ${d.lab==='media'?'selected':''}>Media Lab</option></select></label>
  ${d.kind==='lesson'?`<label class="field">День недели<select name="weekday" ${disabled}>${week.map((x,i)=>`<option value="${i}" ${Number(d.weekday)===i?'selected':''}>${esc(x)}</option>`).join('')}</select></label>`:`<label class="field">Дата<input name="day" type="date" value="${esc(d.day)}" required ${disabled}></label><label class="field" style="display:flex;gap:12px;align-items:center"><input name="cancelled" type="checkbox" style="width:auto" ${d.cancelled?'checked':''} onchange="scheduleCancelChange(this.form)" ${disabled}>Отменить занятие на эту дату</label>`}
  ${d.cancelled?'':`<label class="field">Время<input name="start" type="time" value="${esc(d.start)}" required ${disabled}></label><label class="field">Тема<input id="schedule-title" name="title" value="${esc(d.title)}" maxlength="90" required ${disabled}></label><label class="field">Место<input name="place" value="${esc(d.place)}" maxlength="80" ${disabled}></label>`}
  <p>После сохранения все подписчики Telegram и MAX получат сообщение об изменении.</p>
  <div class="actions"><button type="submit" class="btn violet" ${disabled}>${scheduleBusy?'Сохраняю…':'Сохранить и сообщить всем'}</button><button type="button" class="btn ghost" onclick="scheduleClose()" ${disabled}>Отмена</button></div></form></article>`;
}
schedule=function(){
  if(state.me.role!=='admin')return scheduleReadOnly();
  const disabled=scheduleBusy?'disabled':'';
  const rows=state.lessons.filter(x=>x.lab===lab);
  const changes=state.changes.filter(x=>x.lab===lab);
  return `${commonHeader('TIMECODE / РАСПИСАНИЕ','УПРАВЛЕНИЕ ЗАНЯТИЯМИ.','Добавляй, меняй и удаляй занятия. Об изменениях я сообщу всем.')}
  <div class="rail">${[['kids','Kids Lab'],['media','Media Lab']].map(([id,name])=>`<button class="pill ${lab===id?'active':''}" onclick="lab='${id}';scheduleDraft=null;schedulePaint()" ${disabled}>${name}</button>`).join('')}</div>
  <section class="section">${scheduleDraft?scheduleForm():`<div class="actions"><button class="btn violet" onclick="scheduleOpen('lesson')" ${disabled}>Добавить занятие</button><button class="btn ghost" onclick="scheduleOpen('override')" ${disabled}>Изменить / отменить на дату</button></div>`}</section>
  ${scheduleDraft?'':`<section class="section grid"><article class="card"><h2>Постоянная неделя</h2>${rows.length?rows.map(x=>`<div class="notice"><strong>${esc(week[x.weekday])} · ${esc(x.start)}</strong><p>${esc(x.title)}${x.place?'<br>'+esc(x.place):''}</p><div class="actions"><button class="btn ghost" onclick="scheduleOpen('lesson',${x.id})" ${disabled}>Изменить</button><button class="btn ghost" onclick="scheduleOpen('override',null,{lab:'${lab}',start:'${x.start}',title:state.lessons.find(r=>r.id===${x.id}).title,place:state.lessons.find(r=>r.id===${x.id}).place})" ${disabled}>На дату</button><button class="btn ghost" onclick="scheduleRemove('lesson',${x.id})" ${disabled}>Удалить</button></div></div>`).join(''):'<p>Занятий пока нет.</p>'}</article><article class="card violet"><h2>Отдельные даты</h2>${changes.length?changes.map(x=>`<div class="notice"><strong>${esc(x.day)}</strong><p>${x.cancelled?'Занятие отменено':esc(x.start)+' · '+esc(x.title)+(x.place?'<br>'+esc(x.place):'')}</p><div class="actions"><button class="btn ghost" onclick="scheduleOpen('override',${x.id})" ${disabled}>Изменить</button><button class="btn ghost" onclick="scheduleRemove('override',${x.id})" ${disabled}>Убрать изменение</button></div></div>`).join(''):'<p>Пока без изменений.</p>'}</article></section>`}`;
};
admin=function(){return `<section class="section"><article class="card"><h2>Редактор расписания</h2><p>Все поля занятия в одной форме. Здесь можно также удалять занятия.</p><button class="btn violet" onclick="go('schedule')">Редактировать расписание</button></article></section>`;};
if(state&&tab==='schedule')schedulePaint();

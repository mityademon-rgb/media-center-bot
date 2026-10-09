/* Daily trophy avatar belongs to TIMECODE, not the messenger profile. */
const statusProfileOriginal=profile;
profile=function(){
  let html=statusProfileOriginal();const badge=state.me.daily_status;
  if(!badge)return html;
  const card=`<div class="card" style="margin:16px 0"><div style="display:flex;gap:18px;align-items:center"><span role="img" aria-label="${esc(badge.title)}" style="font-size:64px">${esc(badge.icon)}</span><div><h2>${esc(badge.title)}</h2><p>${esc(badge.day)} · ${badge.actions} действий за день</p></div></div><p>Статус до следующих вечерних итогов. Участвуй в перекличках, играй и присылай кадры. После дня без участия — «Лопушок на паузе».</p></div>`;
  return card+html;
};

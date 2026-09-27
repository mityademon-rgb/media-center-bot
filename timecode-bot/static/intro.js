(()=>{
  const splash=document.getElementById('intro');
  const video=document.getElementById('intro-video');
  const sound=document.getElementById('intro-sound');
  if(!splash||!video)return;
  let finished=false;
  let timer;
  function label(text){if(sound){sound.textContent=text;sound.setAttribute('aria-label',text)}}
  function finish(){
    if(finished)return;
    finished=true;
    clearTimeout(timer);
    video.pause();
    splash.classList.add('gone');
    setTimeout(()=>splash.remove(),400);
  }
  function deadline(){clearTimeout(timer);timer=setTimeout(finish,9500)}
  document.getElementById('intro-skip')?.addEventListener('click',finish);
  video.addEventListener('ended',finish,{once:true});
  video.addEventListener('error',finish,{once:true});
  sound?.addEventListener('click',()=>{
    if(finished)return;
    video.muted=!video.muted;
    label(video.muted?'🔊 Включить звук':'🔇 Выключить звук');
    if(video.paused)video.play().catch(()=>{});
  });
  try{
    deadline();
    if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches){finish();return}
    video.muted=false;
    video.volume=1;
    const start=video.play();
    if(start&&typeof start.then==='function')start.catch(()=>{
      video.muted=true;
      label('🔊 Включить звук');
      video.play().catch(finish);
    });
  }catch(_){video.muted=true;label('🔊 Включить звук');video.play().catch(finish)}
})();

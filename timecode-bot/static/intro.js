(()=>{
  const splash=document.getElementById('intro');
  const video=document.getElementById('intro-video');
  const sound=document.getElementById('intro-sound');
  if(!splash||!video)return;
  let finished=false;
  let waiting=false;
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
    if(waiting){
      video.muted=false;
      video.volume=1;
      const start=video.play();
      if(start&&typeof start.then==='function')start.then(()=>{
        waiting=false;
        label('🔇 Выключить звук');
        deadline();
      },()=>label('▶ Запустить со звуком'));
      return;
    }
    video.muted=!video.muted;
    label(video.muted?'🔊 Включить звук':'🔇 Выключить звук');
  });
  try{
    if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches){finish();return}
    video.muted=false;
    video.volume=1;
    const start=video.play();
    if(start&&typeof start.then==='function')start.then(deadline,()=>{
      waiting=true;
      video.pause();
      video.currentTime=0;
      label('▶ Запустить со звуком');
    });
    else deadline();
  }catch(_){waiting=true;label('▶ Запустить со звуком')}
})();

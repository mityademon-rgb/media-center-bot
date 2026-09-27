(()=>{
  const splash=document.getElementById('intro');
  const video=document.getElementById('intro-video');
  const sound=document.getElementById('intro-sound');
  if(!splash||!video)return;
  let finished=false;
  let timer;
  function soundLabel(){
    if(!sound)return;
    sound.textContent=video.muted?'🔊 Включить звук':'🔇 Выключить звук';
    sound.setAttribute('aria-label',video.muted?'Включить звук заставки':'Выключить звук заставки');
  }
  function finish(){
    if(finished)return;
    finished=true;
    clearTimeout(timer);
    video.pause();
    splash.classList.add('gone');
    setTimeout(()=>splash.remove(),400);
  }
  function deadline(){clearTimeout(timer);timer=setTimeout(finish,9500)}
  deadline();
  document.getElementById('intro-skip')?.addEventListener('click',finish);
  video.addEventListener('ended',finish,{once:true});
  video.addEventListener('error',finish,{once:true});
  sound?.addEventListener('click',()=>{
    if(finished)return;
    video.muted=!video.muted;
    soundLabel();
    if(video.paused){
      const playback=video.play();
      if(playback&&typeof playback.catch==='function')playback.catch(()=>{
        video.muted=true;
        soundLabel();
      });
    }
  });
  try{
    if(window.matchMedia?.('(prefers-reduced-motion: reduce)').matches){finish();return}
    video.muted=false;
    video.volume=1;
    soundLabel();
    const playback=video.play();
    if(playback&&typeof playback.catch==='function')playback.catch(()=>{
      video.muted=true;
      soundLabel();
      const silent=video.play();
      if(silent&&typeof silent.catch==='function')silent.catch(finish);
    });
  }catch(_){video.muted=true;soundLabel();try{video.play()}catch(e){finish()}}
})();

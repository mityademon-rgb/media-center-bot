/* One shared daily rotation for the TIMECODE home page and glossary. */
const dailyGames=[...games,{id:'terms',name:'Запомни и найди',meta:'Игра с кинотерминами',desc:'Открывай карточки и находи правильные названия.'}];
const dailyWords=glossaryEntries.filter((item,index,list)=>list.findIndex(other=>other[0].toLocaleLowerCase('ru')===item[0].toLocaleLowerCase('ru'))===index);

function currentDayNumber(){
  const date=state?.date||new Date().toISOString().slice(0,10);
  return Math.floor(Date.parse(date+'T00:00:00Z')/86400000);
}

function dailyGame(){
  const firstDay=Math.floor(Date.parse('2026-09-26T00:00:00Z')/86400000);
  const index=((currentDayNumber()-firstDay)%dailyGames.length+dailyGames.length)%dailyGames.length;
  return dailyGames[index];
}

function dailyWord(){
  const count=dailyWords.length;
  if(!count)return null;
  const firstDay=Math.floor(Date.parse('2026-09-26T00:00:00Z')/86400000);
  const day=currentDayNumber()-firstDay;
  const cycle=Math.floor(day/count);
  const position=((day%count)+count)%count;
  const order=Array.from({length:count},(_,i)=>i);
  let seed=(0x9e3779b9 ^ Math.imul(cycle+1,0x85ebca6b))>>>0;
  for(let i=count-1;i>0;i--){
    seed^=seed<<13;seed^=seed>>>17;seed^=seed<<5;
    const j=(seed>>>0)%(i+1);
    [order[i],order[j]]=[order[j],order[i]];
  }
  return dailyWords[order[position]];
}

const originalHome=home;
home=function(){
  const markup=originalHome();
  const anchor='<section class="section"><div class="section-label">ИГРА НА ПЕРЕМЕНЕ</div>';
  const start=markup.indexOf(anchor);
  if(start<0)return markup;
  const game=dailyGame(),word=dailyWord();
  const discovery=`<section class="section home-daily-grid">
    <article class="home-game-feature">
      <div class="home-feature-content">
        <span class="home-feature-label">ИГРА ДНЯ · КАЖДЫЙ ДЕНЬ НОВАЯ</span>
        <h2>${esc(game.name)}</h2><p>${esc(game.desc)}</p>
        <button class="btn violet" onclick="openGame('${game.id}')">Играть ↗</button>
      </div>
    </article>
    ${word?`<article class="home-word-feature"><span class="tag">СЛОВО ДНЯ · ИЗ НАШЕГО СЛОВАРЯ</span>
      <div class="home-word-icon">${esc(word[1])}</div><h2>${esc(word[0])}</h2>
      <p>${esc(word[2])}</p><button class="btn ghost" onclick="go('glossary')">Открыть словарь ↗</button>
    </article>`:''}
  </section>`;
  return markup.slice(0,start)+discovery;
};

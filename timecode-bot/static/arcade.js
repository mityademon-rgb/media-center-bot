/* TIMECODE arcade: two local games, no dependencies or server state while playing. */
let battle=null;
const battleSize=8;
function battleFleet(){
 for(let round=0;round<80;round++){
  let occupied=new Set(),fleet=[],success=true;
  for(const length of [4,3,2,2]){
   let placed=false;
   for(let attempt=0;attempt<160;attempt++){
    let horizontal=Math.random()<.5,x=Math.floor(Math.random()*(battleSize-(horizontal?length:1)+1)),y=Math.floor(Math.random()*(battleSize-(horizontal?1:length)+1));
    let cells=Array.from({length},(_,k)=>(y+(horizontal?0:k))*battleSize+x+(horizontal?k:0));
    if(cells.some(n=>{let cx=n%battleSize,cy=Math.floor(n/battleSize);return [...occupied].some(p=>Math.abs(p%battleSize-cx)<=1&&Math.abs(Math.floor(p/battleSize)-cy)<=1)}))continue;
    fleet.push(cells);cells.forEach(n=>occupied.add(n));placed=true;break;
   }
   if(!placed){success=false;break}
  }
  if(success)return fleet;
 }
 return [[0,1,2,3],[16,17,18],[32,33],[48,49]];
}
function battleKey(){return 'timecode-fleet-best-'+(state?.me?.id||'guest')}
function battleStart(){battle={fleet:battleFleet(),shots:new Set(),last:'Найди четыре корабля. Счёт идёт на точность.',won:false};}
function battleGame(){if(!battle)battleStart();let hit=new Set(battle.fleet.flat()),sunk=battle.fleet.filter(ship=>ship.every(n=>battle.shots.has(n))).length,best=localStorage.getItem(battleKey())||'—';
 let cells=Array.from({length:64},(_,i)=>{let shot=battle.shots.has(i),target=hit.has(i),ship=battle.fleet.find(s=>s.includes(i)),dead=ship?.every(n=>battle.shots.has(n)),label='Клетка '+String.fromCharCode(65+i%8)+(Math.floor(i/8)+1);return `<button class="sea-cell ${shot?(target?(dead?'sunk':'hit'):'miss'):''}" aria-label="${label}${shot?(target?' попадание':' мимо'):''}" ${shot||battle.won?'disabled':''} onclick="battleFire(${i})">${shot?(target?(dead?'✦':'◉'):'·'):''}</button>`}).join('');
 return `${commonHeader('АРКАДА / МОРСКОЙ БОЙ','ФЛОТ В КАДРЕ.','Ты снимаешь экспедицию. Корабли скрыты в море: найди их, открывая клетки. При каждом новом заходе флот меняет расположение.')}
 <div class="battle-shell"><div class="battle-top"><span><b>● REC</b> / ЭКСПЕДИЦИЯ</span><span>ПОПЫТОК: ${battle.shots.size}　|　КОРАБЛЕЙ: ${sunk}/4</span></div><div class="battle-field"><div class="sea-grid">${cells}</div><div class="battle-radar"><span>РАДАР / 08×08</span><div class="radar-eye"><i></i><i></i><i></i></div><strong>${battle.won?'ФЛОТ НАЙДЕН':sunk+' / 4'}</strong><p>Твой рекорд: ${best} ${best==='—'?'':'попыток'}</p><small>Попадание ◉ · найденный корабль ✦</small></div></div><p class="battle-status" role="status">${battle.last}</p><div class="actions"><button class="btn violet" onclick="battleStart();render()">Новая карта ↗</button><button class="btn ghost" onclick="go('games')">Все игры</button></div></div>`
}
function battleFire(cell){if(!battle||battle.won||battle.shots.has(cell))return;battle.shots.add(cell);let ship=battle.fleet.find(s=>s.includes(cell));if(ship){battle.last=ship.every(n=>battle.shots.has(n))?'Корабль найден целиком. В монтаж!':'Есть попадание. Соседние клетки под подозрением.'}else battle.last='Мимо. Море не сдаёт сюжет с первого дубля.';
 if(battle.fleet.every(s=>s.every(n=>battle.shots.has(n)))){battle.won=true;let n=battle.shots.size,best=Number(localStorage.getItem(battleKey()))||Infinity;if(n<best)localStorage.setItem(battleKey(),String(n));battle.last='Четыре корабля в кадре за '+n+' попыток. Хочешь побить свой рекорд?';saveGame('battleship',String(n))}render();}

const cordSize=16;
let cord=null,cordTimer=null,cordTouch=null;
function cordKey(){return 'timecode-cord-best-'+(state?.me?.id||'guest')}
function cordFood(body){let pool=[];for(let i=0;i<cordSize*cordSize;i++)if(!body.includes(i))pool.push(i);return pool.length?pool[Math.floor(Math.random()*pool.length)]:null}
function cordStop(){clearInterval(cordTimer);cordTimer=null;cordTouch=null}
function cordStart(){cordStop();let body=[8*cordSize+7,8*cordSize+6,8*cordSize+5];cord={body,dir:'right',next:'right',food:cordFood(body),score:0,running:true,over:false,paused:false};cordTimer=setInterval(cordTick,185)}
function cordEnd(message){if(!cord||cord.over)return;cord.over=true;cord.running=false;cordStop();let best=Number(localStorage.getItem(cordKey()))||0;if(cord.score>best)localStorage.setItem(cordKey(),String(cord.score));saveGame('miccord',String(cord.score));cordPaint(message)}
function cordTick(){if(game!=='miccord'||!cord?.running||cord.paused)return;let head=cord.body[0],x=head%cordSize,y=Math.floor(head/cordSize);cord.dir=cord.next;if(cord.dir==='up')y--;if(cord.dir==='down')y++;if(cord.dir==='left')x--;if(cord.dir==='right')x++;if(x<0||x>=cordSize||y<0||y>=cordSize)return cordEnd('Шнур упёрся в край площадки. Попробуем ещё дубль?');let cell=y*cordSize+x,grow=cell===cord.food,solid=cord.body.slice(0,grow?cord.body.length:-1);if(solid.includes(cell))return cordEnd('Микрофон запутался в собственном шнуре. Бывало и с профессионалами.');cord.body.unshift(cell);if(grow){cord.score++;cord.food=cordFood(cord.body);if(cord.food===null)return cordEnd('Ты собрал все звуки площадки. Шнур официально бесконечный.');if(cord.score%4===0){clearInterval(cordTimer);cordTimer=setInterval(cordTick,Math.max(85,185-Math.floor(cord.score/4)*15))}}else cord.body.pop();cordPaint();}
function cordTurn(direction){if(!cord||cord.over)return;let opposite={up:'down',down:'up',left:'right',right:'left'};if(direction===opposite[cord.dir])return;cord.next=direction}
function cordSwipeStart(e){cordTouch={x:e.clientX,y:e.clientY}}
function cordSwipeEnd(e){if(!cordTouch)return;let dx=e.clientX-cordTouch.x,dy=e.clientY-cordTouch.y;cordTouch=null;if(Math.max(Math.abs(dx),Math.abs(dy))<16)return;cordTurn(Math.abs(dx)>Math.abs(dy)?(dx>0?'right':'left'):(dy>0?'down':'up'))}
function cordPause(){if(!cord||cord.over)return;cord.paused=!cord.paused;cordPaint()}
window.addEventListener('keydown',e=>{if(game!=='miccord')return;let map={ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right',w:'up',a:'left',s:'down',d:'right'};let direction=map[e.key];if(direction){e.preventDefault();cordTurn(direction)}else if(e.key===' '){e.preventDefault();cordPause()}});
document.addEventListener('visibilitychange',()=>{if(document.hidden&&game==='miccord'&&cord&&!cord.over){cord.paused=true}});
function cordGame(){if(!cord)cordStart();return `${commonHeader('АРКАДА / ЗВУК В ЭФИРЕ','МИКРОФОН И ШНУР.','Проведи микрофон к звуковым сигналам. Каждый найденный звук удлиняет кабель; врежешься в него или в стену — дубль окончен.')}
 <div class="cord-shell"><div class="cord-hud"><span>🎙️ TIMECODE / ЗВУК</span><span id="cord-score">ЗВУКОВ: 0</span><span id="cord-best">РЕКОРД: ${localStorage.getItem(cordKey())||0}</span></div><div id="cord-board" class="cord-board" onpointerdown="cordSwipeStart(event)" onpointerup="cordSwipeEnd(event)" aria-label="Игровое поле: веди микрофон стрелками или движениями пальца"></div><div id="cord-message" class="cord-message" role="status"></div><div class="cord-controls"><button aria-label="Вверх" onclick="cordTurn('up')">↑</button><div><button aria-label="Влево" onclick="cordTurn('left')">←</button><button aria-label="Вниз" onclick="cordTurn('down')">↓</button><button aria-label="Вправо" onclick="cordTurn('right')">→</button></div></div><div class="actions"><button id="cord-pause" class="btn violet" onclick="cordPause()">Пауза</button><button class="btn ghost" onclick="openGame('miccord')">Новый дубль ↗</button><button class="btn ghost" onclick="go('games')">Все игры</button></div></div>`}
function cordPaint(message){let board=document.querySelector('#cord-board');if(!board||!cord)return;let cable=new Set(cord.body.slice(1));board.innerHTML=Array.from({length:cordSize*cordSize},(_,i)=>`<span class="cord-pixel ${cord.body[0]===i?'microphone':cable.has(i)?'cable':cord.food===i?'signal':''}">${cord.body[0]===i?'🎤':cord.food===i?'♪':''}</span>`).join('');let score=document.querySelector('#cord-score'),best=document.querySelector('#cord-best'),info=document.querySelector('#cord-message'),pause=document.querySelector('#cord-pause');if(score)score.textContent='ЗВУКОВ: '+cord.score;if(best)best.textContent='РЕКОРД: '+(localStorage.getItem(cordKey())||0);if(info)info.textContent=message|| (cord.over?'Дубль окончен.':cord.paused?'Пауза. Когда будешь готов, продолжим.':'Свайпни по полю или нажми стрелку.');if(pause){pause.textContent=cord.paused?'Продолжить':'Пауза';pause.disabled=cord.over}}

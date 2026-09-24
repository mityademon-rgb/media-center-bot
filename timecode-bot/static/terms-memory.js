/* TIMECODE / visual terminology memory game. No AI calls or automated messages. */
const termBank=[
 ['Общий план','🏙️','В кадре человек целиком и место вокруг него.','КАДР'],
 ['Средний план','🧍','Человека видно примерно по пояс.','КАДР'],
 ['Крупный план','👀','Лицо или предмет занимает почти весь кадр.','КАДР'],
 ['Деталь','🔍','Очень близко снятая часть предмета или лица.','КАДР'],
 ['Ракурс','↗️','Точка, с которой камера смотрит на героя.','КАДР'],
 ['Правило третей','▦','Линии делят кадр на девять частей и помогают разместить героя.','КАДР'],
 ['Воздух в кадре','🌬️','Свободное место перед взглядом или движением героя.','КАДР'],
 ['Панорама','🎥','Камера поворачивается на месте и показывает пространство.','КАМЕРА'],
 ['Наезд камеры','🔜','Камера приближается к тому, что снимает.','КАМЕРА'],
 ['Фокус','🎯','То, что выглядит резким на изображении.','КАМЕРА'],
 ['Экспозиция','☀️','Количество света на снимке: слишком темно, нормально или пересвет.','КАМЕРА'],
 ['Контровой свет','🌅','Источник света стоит позади героя.','СВЕТ'],
 ['Хромакей','🟩','Однотонный фон, который заменяют другой картинкой.','СВЕТ'],
 ['Хлопушка','🎬','Табличка в начале дубля помогает совместить звук и видео.','ПЛОЩАДКА'],
 ['Дубль','🔴','Одна попытка снять сцену от начала до конца.','ПЛОЩАДКА'],
 ['Раскадровка','🗂️','Рисунки будущих кадров в порядке сцен.','ПЛОЩАДКА'],
 ['Реквизит','🕶️','Предметы, которыми герои пользуются в кадре.','ПЛОЩАДКА'],
 ['Бэкстейдж','🎭','Съёмка того, что происходит за кадром.','ПЛОЩАДКА'],
 ['Петличка','🎙️','Маленький микрофон, который крепят на одежду.','ЗВУК'],
 ['Микрофон-пушка','🎤','Направленный микрофон, который ловит звук из нужной стороны.','ЗВУК'],
 ['Интершум','🌧️','Живой звук места: шаги, дождь, голоса, машины.','ЗВУК'],
 ['Закадровый голос','🗣️','Голос слышен, а говорящего в кадре не видно.','ЗВУК'],
 ['Синхрон','💬','Фрагмент интервью, где мы видим и слышим говорящего.','ТВ'],
 ['Стендап','🧑‍💼','Корреспондент сам говорит в кадре с места событий.','ТВ'],
 ['Подводка','📣','Фраза ведущего перед началом сюжета.','ТВ'],
 ['Прямой эфир','📡','Передача идёт зрителям в тот же момент, когда её снимают.','ТВ'],
 ['Перебивка','✂️','Короткий дополнительный кадр между частями разговора.','МОНТАЖ'],
 ['Склейка','⚡','Место, где один кадр сменяется другим.','МОНТАЖ'],
 ['Таймкод','⏱️','Время и номер кадра на записи для точного поиска момента.','МОНТАЖ'],
 ['Титры','🔠','Текст на экране: имена участников, название, авторы.','МОНТАЖ'],
 ['Плашка','🏷️','Графический блок с именем, должностью или другой подписью.','ГРАФИКА'],
 ['Монтаж','🧩','Выбор кадров и их сборка в последовательную историю.','МОНТАЖ'],
 ['Черновой монтаж','🛠️','Первая сборка истории, которую ещё будут менять.','МОНТАЖ'],
 ['Натурная съёмка','🌳','Съёмка в настоящем месте вне павильона.','ПЛОЩАДКА'],
 ['Пилот','🚀','Первый пробный выпуск будущей программы.','ТВ'],
 ['Блиц','⚡','Несколько коротких вопросов подряд.','ИНТЕРВЬЮ']
];
let tm=null;
const tmShuffle=a=>{let b=[...a];for(let i=b.length-1;i>0;i--){let j=Math.floor(Math.random()*(i+1));[b[i],b[j]]=[b[j],b[i]]}return b};
function tmKey(){return 'timecode-terms-seen-'+(state?.me?.id||'browser')}
function tmSeen(){try{let a=JSON.parse(localStorage.getItem(tmKey())||'[]');return Array.isArray(a)?a.filter(n=>Number.isInteger(n)&&n>=0&&n<termBank.length):[]}catch{return []}}
function tmStart(){let seen=tmSeen(),available=termBank.map((_,i)=>i).filter(i=>!seen.includes(i));if(available.length<3){seen=[];available=termBank.map((_,i)=>i);localStorage.removeItem(tmKey())}let picked=tmShuffle(available).slice(0,3);tm={picked,order:tmShuffle(picked),phase:'study',at:0,tries:0,score:0,marks:[],lastWrong:null,options:[]};}
function tmQuiz(){if(!tm)return tmStart(),tmQuiz();let {picked,order,phase,at}=tm,seen=tmSeen().length;
let head=`<div class="tm-head"><span class="tag">ИГРА / КИНОСЛОВАРЬ</span><h1>ЗАПОМНИ<br>И НАЙДИ<span>.</span></h1><p>Три термина. Потом они поменяются местами.</p></div><div class="tm-stats"><span>ИЗУЧЕНО: ${seen} / ${termBank.length}</span><span>${phase==='study'?'СМОТРИ И ЗАПОМИНАЙ':phase==='quiz'?`НАЙДИ ${at+1} / 3`:'РАУНД ЗАКОНЧЕН'}</span></div>`;
if(phase==='study')return `${head}<div class="tm-cards">${picked.map((n,i)=>tmCard(n,'study',i)).join('')}</div><div class="tm-actions"><button class="btn violet" onclick="tmBegin()">Запомнил. Перемешать ↗</button></div>`;
if(phase==='quiz'){let n=order[at];return `${head}<div class="tm-peek">${tmCard(n,'quiz',at)}</div><div class="tm-question">Как называется то, что на карточке?</div><div class="tm-options">${tm.options.map(i=>`<button class="${tm.lastWrong===i?'wrong':''}" onclick="tmAnswer(${i})">${termBank[i][0]}</button>`).join('')}</div><p class="tm-feedback" role="status">${tm.lastWrong!==null?'Промах. Посмотри на картинку ещё раз.':'Выбери название. Подсказку можно открыть ниже.'}</p><button class="tm-hint" onclick="tmHint()">Показать подсказку</button><div id="tm-hint" class="tm-hint-body" hidden>${termBank[n][2]}</div>`}
return `${head}<div class="tm-finish"><span>${tm.score} / 3</span><h2>${tm.score===3?'ПАМЯТЬ В КАДРЕ!':'ЕЩЁ ОДИН ДУБЛЬ?'}</h2><div class="tm-results">${order.map((n,i)=>`<div class="tm-result"><b>${termBank[n][1]}</b><strong>${termBank[n][0]}</strong><small>${tm.marks[i]?'✓ С ПЕРВОГО РАЗА':'УЗНАЛ ПОСЛЕ ПОДСКАЗКИ'}</small></div>`).join('')}</div><div class="tm-actions"><button class="btn violet" onclick="tmStart();render()">Ещё три новых термина ↗</button><button class="btn ghost" onclick="go('games')">К играм</button></div></div>`
}
function tmCard(n,phase,i){let [name,icon,description,group]=termBank[n];return `<article class="tm-card tm-color-${n%5}"><div class="tm-card-top"><span>0${i+1} / ${group}</span><span>TIME:CODE</span></div><div class="tm-picture"><div class="tm-spot"></div><span aria-hidden="true">${icon}</span><i class="tm-cross a"></i><i class="tm-cross b"></i></div><div class="tm-card-info">${phase==='study'?`<strong>${name}</strong><p>${description}</p>`:'<strong>КАК ЭТО НАЗЫВАЕТСЯ?</strong><p>Вспомни название предмета или приёма.</p>'}</div></article>`}
function tmBegin(){if(!tm||tm.phase!=='study')return;tm.phase='quiz';tm.at=0;tm.lastWrong=null;tm.options=tmShuffle(tm.picked);render()}
function tmHint(){let hint=document.querySelector('#tm-hint');if(hint)hint.hidden=false}
function tmAnswer(i){if(!tm||tm.phase!=='quiz')return;let target=tm.order[tm.at];if(i!==target){tm.tries++;tm.lastWrong=i;render();return}let first=tm.tries===0;tm.marks.push(first);if(first)tm.score++;tm.at++;tm.tries=0;tm.lastWrong=null;tm.options=tmShuffle(tm.picked);if(tm.at===3){tm.phase='done';let seen=tmSeen();localStorage.setItem(tmKey(),JSON.stringify([...new Set([...seen,...tm.picked])]))}render()}

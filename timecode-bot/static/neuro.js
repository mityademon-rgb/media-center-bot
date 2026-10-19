/* TIMECODE: AI workshop, private conversation in page memory only. */
(() => {
  let messages = [], draft = '', busy = false, error = '', page = 'chat', owner = null;
  const examples = ['Подготовить игровое занятие по журналистике для детей 12 лет на 60 минут', 'Сделать афишу открытого урока и текст приглашения', 'Написать программу кружка на год с упором на практику', 'Собрать презентацию к занятию', 'Улучшить мой промпт', 'Подготовить отчёт по моим фактам'];
  const terms = [
    ['Нейросеть', 'Система, которая находит закономерности в примерах и создаёт ответ на ваш запрос. Может ошибаться: уверенный тон не означает достоверность.'],
    ['Промпт', 'Поручение нейросети. Например: «Придумай три игры на знакомство для 12 подростков, 12+, на 15 минут, без реквизита. Дай правила и время каждой».'],
    ['Контекст', 'Условия вашей задачи: для кого, зачем, что уже есть, сколько времени и какой результат нужен. «Напиши про лепку» и «Напиши приглашение на лепку для родителей детей 7–9 лет» — разные задачи.'],
    ['РКФО', 'Необязательная памятка: роль, контекст, формат, ограничения. Например: редактор; кружок журналистики 12+; три анонса по 500 знаков; без выдуманных дат и обещаний.'],
    ['Модель', 'Конкретная система внутри сервиса. Сервис — рабочее место, модель — инструмент, который отвечает. Версии и доступные функции меняются.'],
    ['Мультимодальность', 'Работа с несколькими форматами: текстом, изображениями, звуком или видео. Наличие такой модели не означает, что в каждом чате доступны все функции.'],
    ['Галлюцинация', 'Правдоподобная выдумка в ответе: несуществующая цитата, источник, дата. Сверяйте факты с первоисточником, особенно перед публикацией.'],
    ['Референс', 'Пример, который показывает нужный стиль или устройство результата. Объясните, что взять из образца: композицию, тон, структуру, а не «сделай так же».'],
    ['Итерация', 'Следующая правка в том же разговоре. Например: «Сократи вступление, оставь игры, добавь по одному примеру». Не нужно каждый раз писать всё заново.'],
    ['Токен', 'Небольшая часть текста, которой модель измеряет вход и ответ. Длинный диалог занимает больше места; если теряется контекст, кратко повторите важные условия.'],
    ['Работа с источниками', 'Ответ по вашим материалам: программе, заметкам, документам. Просите указывать, откуда взят вывод, и отделять найденное от предположений.'],
    ['Цепочка действий', 'Несколько последовательных задач: содержание → проверка → оформление → сохранение. Не обязательно искать одну нейросеть, которая сделает всё сразу.']
  ];
  const categories = [
    ['01', 'Текст и идеи', 'Занятия, сценарии, программы, анонсы и правки. Сначала получите содержание, затем уточняйте.', 'GigaChat / DeepSeek', 'https://giga.chat/', 'https://chat.deepseek.com/'],
    ['02', 'Изображения', 'Иллюстрации, фон афиши, визуальная идея. Точные даты, логотипы и мелкий текст удобно добавить при вёрстке.', 'GigaChat', 'https://giga.chat/'],
    ['03', 'Презентации', 'Превратить проверенный план в последовательность слайдов. Сначала структура и факты, затем оформление.', 'Gamma', 'https://gamma.app/'],
    ['04', 'Звук и музыка', 'Музыкальные эскизы, заставки, настроение. Перед использованием проверьте условия сервиса и права.', 'Suno', 'https://suno.com/'],
    ['05', 'Видео', 'Короткие сцены по описанию или изображению. Сначала сценарий и отдельные планы, затем генерация и монтаж.', 'Уточнить задачу с Кими'],
    ['06', 'Источники и документы', 'Найти смысл в ваших материалах, сопоставить, составить конспект. Просите опору на конкретные фрагменты.', 'Начать с текста источника']
  ];
  const previousHome = home, previousRender = render, previousDock = renderDock;
  const teacherAccess = () => !!state?.me && ['teacher', 'admin'].includes(state.me.role);
  home = function() { return previousHome() + (teacherAccess() ? `<section class="section neuro-entry"><span class="tag">МАСТЕРСКАЯ ПРЕПОДАВАТЕЛЯ / КИМИ</span><h2>Есть задача.<br>Найдём нейросеть.</h2><p>Занятие, афиша, программа, отчёт. Кими предложит маршрут и напишет запросы для каждого шага.</p><button class="btn" onclick="openNeuro()">Нейросети →</button></section>` : ''); };
  renderDock = function() {
    previousDock();
    if (!teacherAccess()) return;
    const dock = document.querySelector('#dock');
    const button = document.createElement('button');
    button.className = tab === 'neuro' ? 'active' : '';
    button.innerHTML = '<b>✳</b>Нейросети';
    button.onclick = () => openNeuro();
    dock.append(button); dock.classList.add('neuro-dock');
  };
  render = function() {
    if (tab !== 'neuro' || !state) return previousRender();
    if (!teacherAccess()) { tab = 'home'; return previousRender(); }
    if (owner !== state.me.id) { owner = state.me.id; messages = []; draft = ''; error = ''; }
    document.body.classList.remove('arcade-playing');
    renderDock(); document.querySelector('#app').innerHTML = view();
    bind();
  };
  window.openNeuro = function() { if (!teacherAccess()) return; page = 'chat'; go('neuro'); };
  function view() {
    const head = `<header class="neuro-head"><div class="eyebrow">TIMECODE / ПРАКТИКА С КИМИ</div><h1>Нейросети<br><em>для вашей задачи.</em></h1><p>Расскажите, что нужно сделать. Разберём на шаги, выберем инструменты и составим промпты.</p></header><div class="neuro-tabs" role="group" aria-label="Раздел нейросетей">${[['chat','Помощь Кими'],['tools','Кто что умеет'],['terms','Термины']].map(([id,label])=>`<button class="pill ${page===id?'active':''}" data-page="${id}" aria-pressed="${page===id}">${label}</button>`).join('')}</div>`;
    const course = `<aside class="neuro-course"><span>КУРС ДЛЯ ПРЕПОДАВАТЕЛЕЙ</span><h3>Нейросети для преподавателя</h3><p>Четыре встречи: от первого запроса до готового занятия, визуала и отчёта.</p><a href="https://timecode-lab.ru/#/ai" target="_blank" rel="noopener" class="pill">Открыть курс ↗</a><a href="https://timecode-lab.ru/assets/neuro/index.html" target="_blank" rel="noopener" class="pill">Практикум ↗</a></aside>`;
    if (page === 'terms') return `<div class="neuro">${head}<div class="neuro-terms">${terms.map(([title,text])=>`<details><summary>${esc(title)}</summary><p>${esc(text)}</p></details>`).join('')}</div>${course}</div>`;
    if (page === 'tools') return `<div class="neuro">${head}<p class="neuro-note">Это разделение по задачам. Единого рейтинга «самая умная» нет; один сервис может совмещать несколько форматов.</p><div class="neuro-categories">${categories.map(([n,title,text,label,url,second])=>`<article><span>${n}</span><h2>${title}</h2><p>${text}</p>${url?`<a href="${url}" target="_blank" rel="noopener">${esc(label.split(' / ')[0])} ↗</a>${second?` · <a href="${second}" target="_blank" rel="noopener">DeepSeek ↗</a>`:''}`:`<button class="pill" data-example="${esc('Помогите выбрать нейросеть: '+title)}">${label} →</button>`}</article>`).join('')}</div><p class="neuro-note">Назначения сверены по официальным страницам 20.10.2026. Доступ, функции и условия использования проверяйте в самом сервисе.</p>${course}</div>`;
    return `<div class="neuro">${head}${!messages.length?`<section class="neuro-start"><div class="neuro-kimi">К</div><div><h2>Что будем делать?</h2><p>Можно одной фразой. Например: «Нужна игра для первого занятия».</p></div></section><div class="neuro-examples">${examples.map((text,i)=>`<button data-example="${esc(text)}"><span>0${i+1}</span>${esc(text)} ↗</button>`).join('')}</div>`:''}<div class="neuro-chat" aria-live="polite">${messages.map((m,i)=>m.role==='user'?`<article class="neuro-user"><b>Вы</b><p>${esc(m.content)}</p></article>`:answer(m.result,i)).join('')}${busy?'<div class="neuro-wait" role="status">Кими собирает маршрут…</div>':''}</div><form id="neuro-form" class="neuro-compose"><label for="neuro-task">${messages.length?'Продолжить разговор':'Ваша задача'}</label><textarea id="neuro-task" rows="4" maxlength="4000" placeholder="Мне нужно…" ${busy?'disabled':''} required>${esc(draft)}</textarea><div class="neuro-controls"><button type="submit" class="btn" ${busy?'disabled':''}>${busy?'Кими отвечает…':'Получить помощь →'}</button>${messages.length?`<button type="button" class="pill" id="neuro-new" ${busy?'disabled':''}>Новая задача</button><button type="button" class="pill" id="neuro-export">Скачать диалог ↓</button>`:''}</div>${error?`<p class="neuro-error" role="alert">${esc(error)}</p>`:''}<small>Диалог сохраняется только до перезагрузки страницы. Для примеров используйте вымышленные имена и обезличенные материалы.</small></form>${course}</div>`;
  }
  function answer(r,index) {
    return `<article class="neuro-answer"><div class="neuro-author"><span class="neuro-kimi">К</span><b>Кими <small>помощник по нейросетям</small></b></div><p>${esc(r.reply)}</p>${r.steps.map((s,i)=>`<section class="neuro-step"><div class="neuro-step-title"><span>${i+1}</span><h3>${esc(s.title)}</h3></div>${s.tool?`<div class="neuro-tool">${esc(s.tool)}</div>`:''}<p>${esc(s.action)}</p>${s.prompt?`<div class="neuro-prompt"><div><b>ГОТОВЫЙ ПРОМПТ</b><button class="pill" data-copy="${index}:${i}">Копировать</button></div><pre tabindex="0">${esc(s.prompt)}</pre></div>`:''}${s.check?`<p class="neuro-check"><b>Проверка:</b> ${esc(s.check)}</p>`:''}</section>`).join('')}${r.questions.length?`<div class="neuro-questions"><b>Чтобы продолжить:</b>${r.questions.map(q=>`<p>${esc(q)}</p>`).join('')}</div>`:''}</article>`;
  }
  function flatten(r) { return r.reply+'\n\n'+r.steps.map((s,i)=>`${i+1}. ${s.title}\n${s.tool}\n${s.action}\n${s.prompt?`Промпт: ${s.prompt}\n`:''}Проверка: ${s.check}`).join('\n\n')+'\n'+r.questions.join('\n'); }
  function bind() {
    document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>{page=b.dataset.page;render();});
    document.querySelectorAll('[data-example]').forEach(b=>b.onclick=()=>{page='chat';draft=b.dataset.example;render();document.querySelector('#neuro-task').focus();});
    const box=document.querySelector('#neuro-task'); if(box) box.oninput=()=>{draft=box.value;};
    const form=document.querySelector('#neuro-form'); if(form) form.onsubmit=send;
    document.querySelectorAll('[data-copy]').forEach(b=>b.onclick=async()=>{const [mi,si]=b.dataset.copy.split(':').map(Number); const text=messages[mi].result.steps[si].prompt;try{await navigator.clipboard.writeText(text);b.textContent='Скопировано';}catch(e){const pre=b.closest('.neuro-prompt').querySelector('pre');const range=document.createRange();range.selectNodeContents(pre);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);toast('Текст выделен — скопируйте вручную');}});
    const reset=document.querySelector('#neuro-new'); if(reset)reset.onclick=()=>{if(busy)return;messages=[];draft='';error='';render();};
    const download=document.querySelector('#neuro-export');if(download)download.onclick=()=>{const content=messages.map(m=>(m.role==='user'?'ВЫ\n':'КИМИ\n')+m.content).join('\n\n');const url=URL.createObjectURL(new Blob([content],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=url;a.download='timecode-neuro-dialogue.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
  }
  async function send(event) {
    event.preventDefault();if(busy||draft.trim().length<2)return;
    const text=draft.trim(),requestOwner=owner; busy=true;error='';render();
    try {
      const result=await req('neuro',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,history:messages.slice(-10).map(m=>({role:m.role,content:m.content.slice(0,6500)}))})});
      if(state?.me.id!==requestOwner)return;
      messages.push({role:'user',content:text},{role:'assistant',content:flatten(result),result});draft='';
    } catch(e) { error=e.message; }
    finally { busy=false;if(tab==='neuro'){render();document.querySelector('#neuro-form')?.scrollIntoView({behavior:'smooth',block:'center'});} }
  }
  if(state)render();
})();

/* Teacher mode: lessons first; daily activities are an explicit, reversible choice. */
(() => {
  const teacher = () => state?.me?.role === 'teacher';
  const paused = () => teacher() && !state.me.daily_enabled;
  const oldProfile = profile, oldDock = renderDock, oldRender = render;
  profile = function() {
    if (!teacher()) return oldProfile();
    const active = !!state.me.daily_enabled;
    return `<section class="section neuro"><div class="eyebrow">TIMECODE / ПРЕПОДАВАТЕЛЬ</div><h1>Мой режим</h1><article class="card paper"><h2>${active?'Ежедневная жизнь включена':'Только уроки по нейросетям'}</h2><p>${active?'Вы получаете переклички, задания, фотографии и выпуски. Можно читать и играть в приложении.':'Переклички, задания и ежедневные выпуски в личный бот выключены. Уроки по нейросетям и Кими доступны.'}</p><button class="btn violet" onclick="teacherDailyMode(${active?'false':'true'})">${active?'Отключить ежедневную жизнь':'Участвовать в ежедневной жизни'}</button><p>То же самое в чате бота: <code>/daily ${active?'off':'on'}</code>. Режим можно менять в любой момент.</p></article><div class="actions"><button class="btn" onclick="openNeuro()">Уроки и помощь Кими →</button></div></section>`;
  };
  renderDock = function() {
    oldDock();
    if (paused()) {
      document.querySelector('#dock').innerHTML = `<button class="${tab==='neuro'?'active':''}" onclick="openNeuro()"><b>✳</b>Нейросети</button><button class="${tab==='profile'?'active':''}" onclick="go('profile')"><b>◎</b>Моё</button>`;
    }
  };
  render = function() {
    if (paused() && tab !== 'neuro' && tab !== 'profile') tab = 'neuro';
    return oldRender();
  };
  window.teacherDailyMode = async function(enabled) {
    try {
      await req('teacher-mode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({enabled})});
      state = await req('state');
      render();toast(enabled?'Ежедневная жизнь включена':'Ежедневная жизнь выключена');
    } catch(e) { toast(e.message); }
  };
  if (state) render();
})();

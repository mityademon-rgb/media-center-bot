"""Private, persistent four-step screenplay workshop."""
import json
import time

STEPS = ('Идея', 'Заявка', 'Сценарный план', 'Сцены')
QUESTIONS = (
    'Какой фильм хочется снять? Кто герой и что необычное с ним случится?',
    'Кто герой, чего он хочет и что ему мешает? Попробуй рассказать о фильме в трёх предложениях.',
    'Что случится в начале, середине и конце? Запиши главные действия по порядку.',
    'Разбей историю на сцены: где происходит каждая, что делает герой и что меняется?',
)

def schema(c):
    c.execute('''create table if not exists screenplay_projects (
      id integer primary key autoincrement, user_id integer not null,
      step integer not null default 0, title text not null default 'Новый фильм',
      drafts text not null default '["","","",""]', messages text not null default '[]',
      updated integer not null)''')
    c.execute('create index if not exists screenplay_owner on screenplay_projects(user_id,updated)')

def data(c, user_id, project_id=None):
    schema(c)
    rows=[dict(r) for r in c.execute('select id,title,step,updated from screenplay_projects where user_id=? order by updated desc,id desc',(user_id,))]
    if project_id is None:project_id=rows[0]['id'] if rows else None
    row=c.execute('select * from screenplay_projects where user_id=? and id=?',(user_id,project_id)).fetchone() if project_id else None
    project=dict(row) if row else None
    if project:
        project['drafts']=json.loads(project['drafts']);project['messages']=json.loads(project['messages'])
    return {'projects':rows,'project':project,'steps':STEPS,'questions':QUESTIONS}

def act(c,user_id,p,ai_json):
    action=p.get('action');project_id=p.get('id')
    if action=='create':
        schema(c)
        c.execute('insert into screenplay_projects(user_id,updated) values(?,?)',(user_id,int(time.time())))
        return data(c,user_id,c.execute('select last_insert_rowid()').fetchone()[0])
    if type(project_id) is not int or project_id<1:raise ValueError('Выбери проект')
    result=data(c,user_id,project_id);project=result['project']
    if not project:raise ValueError('Проект не найден')
    drafts=project['drafts'];messages=project['messages'];step=project['step']
    if action=='save':
        text=p.get('text')
        if not isinstance(text,str) or len(text)>6000:raise ValueError('Текст слишком длинный')
        if step>3:raise ValueError('Вернись к этапу для правки')
        drafts[step]=text.strip();project['drafts']=drafts
        if step==0 and drafts[0]:project['title']=drafts[0].splitlines()[0][:70]
    elif action=='next':
        if step>=4 or not drafts[step].strip():raise ValueError('Сначала сохрани результат этапа')
        project['step']=step+1
    elif action=='back':
        project['step']=max(0,step-1)
    elif action=='message':
        question=p.get('text')
        if not isinstance(question,str) or not 2<=len(question.strip())<=1200 or step>=4:raise ValueError('Напиши вопрос Кими до 1200 знаков')
        question=question.strip()
        history=[m for m in messages if m['step']==step][-6:]
        context={'этап':STEPS[step],'задача':QUESTIONS[step],'черновики_предыдущих_этапов':drafts[:step], 'черновик_сейчас':drafts[step], 'разговор':history,'реплика_ученика':question}
        system=('Ты Кими, доброжелательный соавтор и наставник школьника в мастерской кино TIMECODE. '
                'Помоги ребёнку самому придумать короткий фильм. На этапе идеи вместе предложи варианты и задай ОДИН конкретный вопрос. '
                'На этапе заявки помоги в 2–4 предложениях объяснить героя, цель и препятствие. '
                'На этапе плана помоги перечислить начало, середину и конец как действия. '
                'На этапе сцен помоги пронумеровать сцены с местом, действием и переменой. '
                'Не сочиняй готовый сценарий, реплики персонажей или полноценные сцены. '
                'Сохраняй выбор ребёнка, не выдумывай факты о его жизни, пиши понятным языком без канцелярита. '
                'Верни JSON с полями reply (короткий ответ и один вопрос, до 600 знаков) и proposal '
                '(необязательная краткая формулировка текущего этапа, которую ученик сможет править; до 1200 знаков).')
        generated=ai_json(system,json.dumps(context,ensure_ascii=False),450)
        reply=str(generated.get('reply','')).strip()[:600] if isinstance(generated,dict) else ''
        proposal=str(generated.get('proposal','')).strip()[:1200] if isinstance(generated,dict) else ''
        if not reply:reply='Я сейчас не могу ответить. Запиши мысль в черновик и попробуй спросить меня чуть позже.'
        messages.extend(({'step':step,'role':'user','text':question},{'step':step,'role':'assistant','text':reply,'proposal':proposal}))
        project['messages']=messages[-80:]
    else:raise ValueError('Неизвестное действие')
    c.execute('update screenplay_projects set step=?,title=?,drafts=?,messages=?,updated=? where id=? and user_id=?',(
        project['step'],project['title'],json.dumps(project['drafts'],ensure_ascii=False),json.dumps(project['messages'],ensure_ascii=False),int(time.time()),project_id,user_id))
    return data(c,user_id,project_id)

"""Private, persistent four-step screenplay workshop."""
import json
import re
import time

STEPS = ('Идея', 'Заявка', 'Сценарный план', 'Сцены')
QUESTIONS = (
    'Идея — ровно три предложения: кто герой, что с ним случится и чем закончится история. Пока без сцен, диалогов и подробностей.',
    'Заявка — расскажи путь фильма от начала до конца: с чего история начинается, что запускает действие и каким будет финал. Не расписывай сцены.',
    'Сценарный план — распиши события по порядку: чего хочет герой, какие препятствия встречает, что предпринимает и как приходит к финалу. Без диалогов.',
    'Сцены — распиши самостоятельно каждую сцену: номер, место, действие героя и что меняется к концу сцены. Кими может подсказать вопрос, но не пишет сцены за тебя.',
)

def sentence_count(text):
    return len([part for part in re.split(r'[.!?…]+|\n+',text) if part.strip()])


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
        if step==0 and sentence_count(drafts[0])!=3:raise ValueError('Идея — ровно три предложения: герой, событие, финал')
        project['step']=step+1
    elif action=='back':
        project['step']=max(0,step-1)
    elif action=='message':
        question=p.get('text')
        if not isinstance(question,str) or not 2<=len(question.strip())<=1200 or step>=4:raise ValueError('Напиши вопрос Кими до 1200 знаков')
        question=question.strip()
        history=[m for m in messages if m['step']==step][-6:]
        context={'этап':STEPS[step],'задача':QUESTIONS[step],'черновики_предыдущих_этапов':drafts[:step], 'черновик_сейчас':drafts[step], 'разговор':history,'реплика_ученика':question}
        rules=(
            'ТОЛЬКО ИДЕЯ. Результат — три коротких предложения: кто герой, что случится, чем закончится. Обсуди задумку, задай один вопрос о герое, событии или финале. Не переходи к заявке, препятствиям, плану, сценам или диалогам.',
            'ТОЛЬКО ЗАЯВКА. У ученика уже есть идея. Помоги наметить начало истории, запускающее событие и финал. Задай один вопрос о связи начала и финала. Не разбивай историю на сцены, не расписывай препятствия и подробный план.',
            'ТОЛЬКО СЦЕНАРНЫЙ ПЛАН. Есть идея и заявка. Помоги ученику самому продумать последовательность событий, цель героя, препятствия, его действия и решение. Задай один вопрос о причинной связи или препятствии. Не пиши сцены и диалоги.',
            'ТОЛЬКО РАЗБИВКА НА СЦЕНЫ. Ученик пишет её самостоятельно. Ты не перечисляешь и не сочиняешь сцены. Задай один уточняющий вопрос о месте, действии или перемене в ОДНОЙ выбранной учеником сцене. Не пиши диалоги и готовый сценарий.',
        )
        system=('Ты Кими, внимательный редактор и собеседник школьника в TIMECODE. Говори с ребёнком на русском простыми словами. '
                'Строго работай только на текущем этапе, не предлагай и не сочиняй содержание следующих этапов, даже если тебя об этом просят. '
                'Никогда не пиши готовый сценарий, сцену, реплики персонажей или план вместо ребёнка. '
                'Если ученик прислал готовый сценарий или сразу всё целиком, помоги выделить только материал текущего этапа. '
                'Не выдумывай факты об ученике. '+rules[step]+' Верни только JSON вида {"reply":"ответ до 240 знаков, один вопрос"}.')
        generated=ai_json(system,json.dumps(context,ensure_ascii=False),180)
        reply=str(generated.get('reply','')).strip()[:300] if isinstance(generated,dict) else ''
        if not reply or len(reply)>260 or re.search(r'(?im)^\s*(?:сцена\s*\d+|(?:инт|нат)\.|(?:акт|эпизод)\s*\d+)',reply):
            reply=QUESTIONS[step].split(' Пока')[0] if step==0 else QUESTIONS[step].split('. ')[0]+'.'
        messages.extend(({'step':step,'role':'user','text':question},{'step':step,'role':'assistant','text':reply}))
        project['messages']=messages[-80:]
    else:raise ValueError('Неизвестное действие')
    c.execute('update screenplay_projects set step=?,title=?,drafts=?,messages=?,updated=? where id=? and user_id=?',(
        project['step'],project['title'],json.dumps(project['drafts'],ensure_ascii=False),json.dumps(project['messages'],ensure_ascii=False),int(time.time()),project_id,user_id))
    return data(c,user_id,project_id)

"""Private, persistent four-step screenplay workshop."""
import json
import re
import time

STEPS = ('Идея', 'Заявка', 'Сценарный план', 'Сцены')
QUESTIONS = (
    'Идея — о чём кино. Назови жанр или тему одним словом, и Кими предложит два-три сюжета. Итог: три предложения о героях и необычной ситуации, без финала и сцен.',
    'Заявка — с чего начинается именно ваша история и чем заканчивается. Кими поможет выбрать начало и финал, связать их между собой. Пока без препятствий и сцен.',
    'Сценарный план — чего хотят герои, какие сложности преодолевают и как их действия ведут к выбранному финалу. Вместе с Кими выбери препятствия и запиши цепочку событий.',
    'Сцены — теперь самостоятельно разбей готовую историю на сцены: номер, место, действие и перемена. Кими ответит на вопрос, если понадобится.',
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
        if step==0 and sentence_count(drafts[0])!=3:raise ValueError('Идея — три предложения о героях и ситуации; финал придумаем на следующем шаге')
        project['step']=step+1
    elif action=='back':
        project['step']=max(0,step-1)
    elif action=='message':
        question=p.get('text')
        if not isinstance(question,str) or not 2<=len(question.strip())<=1200 or step>=4:raise ValueError('Напиши вопрос Кими до 1200 знаков')
        question=question.strip()
        history=[m for i,m in enumerate(messages) if m['step']==step and 'proposal' not in m and not (m['role']=='user' and 'proposal' in (messages[i+1] if i+1<len(messages) else {}))][-6:]
        context={'этап':STEPS[step],'задача':QUESTIONS[step],'черновики_предыдущих_этапов':drafts[:step], 'черновик_сейчас':drafts[step], 'разговор':history,'реплика_ученика':question}
        rules=(
            'ЭТАП 1: ИДЕЯ. Ученик сообщает направление, жанр или героя (например «ужастик»), ТЫ активно предлагаешь 2–3 разных коротких идеи, завязанных на его выборе: например двое школьников получают сообщения из будущего. Варианты отличаются драматургическим ходом, а не только именами. Спроси, какой ему нравится, или предложи смешать их. Если ученик выбрал идею, предложи редактируемую формулировку ровно в три предложения: кто герои, что необычного произошло и про что эта история. Не рассказывай, с чего фильм начинается и чем кончается, это следующий шаг.',
            'ЭТАП 2: ЗАЯВКА. Опирайся на утверждённую идею. Предложи 2–3 конкретных варианта НАЧАЛА и/или ФИНАЛА именно этой истории и помоги связать выбранные ходы. По выбору ребёнка предложи краткую редактируемую заявку с началом и концом. Пока НЕ предлагай препятствия, последовательность событий и сцены.',
            'ЭТАП 3: ПЛАН. Опирайся на идею и уже выбранные начало и финал. Предложи 2–3 разных препятствия, которые герои должны преодолеть, и помоги решить, что они делают и как это ведёт к финалу. По выбору ребёнка предложи краткий редактируемый план действий в причинном порядке. Не дели на сцены и не сочиняй диалогов.',
            'ЭТАП 4: СЦЕНЫ. Ученик сам расписывает сцены. Помоги одним уточняющим вопросом о выбранной им сцене или предложи проверить переход между сценами. Не предлагай готовые сцены и не заполняй их вместо ребёнка.',
        )
        system=('Ты Кими, энергичный соавтор школьника в TIMECODE. Ты ВЕДЁШЬ разговор: предлагай конкретные варианты, не заставляй ученика приносить готовый текст. '
                'Говори просто и живо, учитывай выбор школьника и предыдущие черновики. Работай СТРОГО на текущем этапе. '
                'Если ребёнок просит сделать всё сразу, вернись к текущему этапу. Не сочиняй полный сценарий, сцены, реплики и материалы следующих этапов. '
                +rules[step]+' Верни JSON: {"reply":"короткое вступление и вопрос о выборе", '
                '"options":["вариант 1","вариант 2","вариант 3"], "draft":"краткая формулировка текущего этапа после выбора ребёнка"}. '
                'При первом вопросе ОБЯЗАТЕЛЬНО дай в options 2–3 конкретных разных варианта, каждый не длиннее 180 символов. '
                'Если ребёнок выбрал вариант или смешал варианты, можешь дополнительно вернуть draft. '
                'На этапе сцен options и draft оставь пустыми; reply — один полезный вопрос. '
                'Текущий этап не предлагает и не раскрывает события следующего этапа.')
        generated=ai_json(system,json.dumps(context,ensure_ascii=False),550)
        reply=str(generated.get('reply','')).strip()[:400] if isinstance(generated,dict) else ''
        options=[]
        if isinstance(generated,dict) and step<3 and isinstance(generated.get('options'),list):
            options=[str(x).strip()[:180] for x in generated['options'] if isinstance(x,str) and x.strip()][:3]
        draft=str(generated.get('draft','')).strip() if isinstance(generated,dict) and step<3 else ''
        if step==0 and sentence_count(draft)!=3:draft=''
        draft=draft[:1200 if step==2 else 600]
        if not reply or re.search(r'(?im)^\s*(?:сцена\s*\d+|(?:инт|нат)\.|(?:акт|эпизод)\s*\d+)',reply):
            reply=('Какое кино хочется придумать: страшное, смешное или приключение?' if step==0 else
                   'С чего начнётся история и к какому финалу придём?' if step==1 else
                   'Какое препятствие заставит героев действовать?' if step==2 else
                   'Что меняется для героя к концу этой сцены?')
        if step==3:options=[];draft=''
        messages.extend(({'step':step,'role':'user','text':question},{'step':step,'role':'assistant','text':reply,'options':options,'draft':draft}))
        project['messages']=messages[-80:]
    else:raise ValueError('Неизвестное действие')
    c.execute('update screenplay_projects set step=?,title=?,drafts=?,messages=?,updated=? where id=? and user_id=?',(
        project['step'],project['title'],json.dumps(project['drafts'],ensure_ascii=False),json.dumps(project['messages'],ensure_ascii=False),int(time.time()),project_id,user_id))
    return data(c,user_id,project_id)

"""Five-question games in Telegram and MAX, based on TIMECODE lessons 02 and 03."""
import datetime as dt
import hashlib
import json

# Source: news/boom-kadr-deploy/lessons.js, lessons interview and beautiful-frame.
GAMES={
 'f':{'title':'Как ты строишь кадр?','lesson':'Урок 3 · Учимся красиво снимать','questions':[
  {'q':'В кадре виден герой целиком и место вокруг него. Какой это план?',
   'options':['Общий','Средний','Крупный'],'correct':0,'why':'Общий план знакомит зрителя с местом и показывает героя целиком.','skill':'различать общий, средний и крупный планы'},
  {'q':'Герой услышал неожиданную новость. Хочешь показать его глаза и реакцию. Какой план выберешь?',
   'options':['Общий — побольше фона','Крупный — лицо и эмоция','Средний — герой по пояс'],'correct':1,'why':'Крупный план даёт увидеть реакцию. Сейчас зрителю важнее лицо, чем обстановка.','skill':'выбирать план под задачу сцены'},
  {'q':'Героиня стоит в кадре и смотрит вправо. Где оставишь больше свободного места?',
   'options':['Слева, за её затылком','Только над головой','Справа, перед взглядом'],'correct':2,'why':'Оставляем место перед взглядом: зритель должен понимать, куда смотрит героиня.','skill':'оставлять пространство перед взглядом'},
  {'q':'Включил сетку из девяти прямоугольников. Хочешь применить правило третей. Куда попробуешь поставить главное?',
   'options':['В самый угол','К линии или пересечению','Всегда точно в центр'],'correct':1,'why':'Главное часто ставят к линии или пересечению третей. Центр тоже можно использовать, если это осознанное решение.','skill':'осознанно располагать главное в кадре'},
  {'q':'Телефон обычный, а кадр хочется сделать лучше уже сегодня. С чего начнёшь?',
   'options':['Выберу план и построю кадр','Добавлю побольше фильтров','Подожду дорогую камеру'],'correct':0,'why':'Сначала решаем, что показать, затем — как расположить это в кадре. Камера за нас эти решения не принимает.','skill':'выбирать план и композицию до записи'},
 ]},
 'i':{'title':'Сможешь разговорить героя?','lesson':'Урок 2 · Как задать вопрос, чтобы человек заговорил','questions':[
  {'q':'Берёшь интервью после первого выхода человека на большую сцену. Какой вопрос скорее даст историю?',
   'options':['Вы волновались?','Что произошло за минуту до выхода?','Всё прошло хорошо?'],'correct':1,'why':'Вопрос о конкретном событии приглашает вспомнить и рассказать. На «волновались?» легко ответить одним словом.','skill':'начинать с открытого вопроса'},
  {'q':'Герой говорит: «Перед выступлением я потерял текст». Что спросишь дальше?',
   'options':['А что вы тогда сделали?','Дальше по списку: где учились?','Ну, такое у всех бывает'],'correct':0,'why':'В ответе уже появилась интересная деталь. Уточняем её и развиваем историю, вместо того чтобы уходить к списку вопросов.','skill':'слышать деталь и задавать уточнение'},
  {'q':'Герой закончил ответ и на секунду задумался. Как поступишь?',
   'options':['Сразу задам следующий вопрос','Сам закончу его мысль','Выдержу короткую паузу'],'correct':2,'why':'Две секунды тишины часто дают герою вспомнить и добавить важное. Не торопись заполнять каждую паузу.','skill':'выдерживать паузу и слушать собеседника'},
  {'q':'Начинаешь стендап у фестиваля. Какая фраза обещает зрителю продолжение?',
   'options':['Я нахожусь на фестивале','Очередь растёт — выясним, зачем пришли','Здесь довольно много людей'],'correct':1,'why':'Есть действие и обещание: сейчас выясним причину очереди. Зритель понимает, зачем смотреть дальше.','skill':'начинать стендап с действия'},
  {'q':'История уже прозвучала. Хочешь понять, почему она важна герою. Какой вопрос выберешь?',
   'options':['Вам понравилось?','Вы часто об этом думаете?','Почему вы до сих пор это помните?'],'correct':2,'why':'Этот вопрос помогает раскрыть значение события, а не получить очередное «да» или «нет».','skill':'доводить разговор до смысла истории'},
 ]},
}


def install(s):
    original_callback=s['callback']
    original_message=s['bot_message']

    def tables(c):
        c.execute("create table if not exists chat_game_runs(user_id integer not null,day text not null,topic text not null,step integer not null default 0,score integer not null default 0,missed text not null default '[]',primary key(user_id,day,topic))")

    def question_text(topic,step):
        game=GAMES[topic];q=game['questions'][step]
        return '<b>'+s['esc'](game['title'])+' · '+str(step+1)+'/5</b>\n\n'+s['esc'](q['q'])

    def buttons(day,topic,step):
        return [[{'text':str(index+1)+'. '+option,'callback_data':f'cg:a:{day}:{topic}:{step}:{index}'}] for index,option in enumerate(GAMES[topic]['questions'][step]['options'])]

    def finish(uid,topic,row):
        score=row['score'];game=GAMES[topic]
        with s['conn']() as c:user=c.execute('select name from users where id=?',(uid,)).fetchone()
        name=(user['name'] if user else 'Друг')
        if score==5:
            praise=('Молодец: во всех пяти ситуациях ты выбрал решение, которое помогает зрителю увидеть главное.' if topic=='f' else
                    'Молодец: ты умеешь открыть разговор, услышать деталь и помочь герою рассказать историю.')
        elif score>=3:
            praise='Хороший результат. Большинство решений верные, а несколько моментов ещё стоит потренировать.'
        else:
            praise='Есть к чему стремиться. Теперь ты знаешь, какие решения стоит потренировать перед следующей съёмкой.'
        missed=json.loads(row['missed'])
        advice=(' В следующий раз обрати внимание на то, как '+ '; '.join(dict.fromkeys(missed)) +'.') if missed else (
            ' На ближайшей съёмке проверь эти решения уже с настоящим героем — там начинается самое интересное.')
        s['send'](uid,'<b>'+s['esc'](name)+', твой результат: '+str(score)+'/5.</b>\n\n'+praise+s['esc'](advice),
                  [[{'text':'Другая игра','callback_data':'cg:menu'}]])

    def menu(uid):
        day=s['today']().replace('-','')
        s['send'](uid,'Давай проверим, как ты принимаешь решения на съёмке. Пять ситуаций из наших уроков: выбирай ответ кнопкой, а я объясню, что сработает. В конце покажу твой результат. С чего начнём?',
                  [[{'text':GAMES[t]['title'],'callback_data':f'cg:s:{day}:{t}'}] for t in ('f','i')])

    def callback(q):
        data=q.get('data','')
        if not data.startswith('cg:'):return original_callback(q)
        uid=q.get('from',{}).get('id')
        if not uid or not s['allowed'](uid):return
        if q.get('id')!='max':s['api']('answerCallbackQuery',{'callback_query_id':q['id']})
        if data=='cg:menu':return menu(uid)
        bits=data.split(':')
        try:
            action,day,topic=bits[1:4]
            parsed=dt.datetime.strptime(day,'%Y%m%d').date()
            if parsed>s['now']().date() or (s['now']().date()-parsed).days>7 or topic not in GAMES:raise ValueError()
            with s['conn']() as c:
                tables(c)
                c.execute('insert or ignore into chat_game_runs(user_id,day,topic) values(?,?,?)',(uid,day,topic))
                row=c.execute('select * from chat_game_runs where user_id=? and day=? and topic=?',(uid,day,topic)).fetchone()
            feedback=''
            if action=='a':
                step,chosen=map(int,bits[4:6])
                if not 0<=step<5 or not 0<=chosen<3:raise ValueError()
                if step==row['step']:
                    item=GAMES[topic]['questions'][step];correct=chosen==item['correct']
                    missed=json.loads(row['missed'])
                    if not correct:missed.append(item['skill'])
                    with s['conn']() as c:
                        changed=c.execute('update chat_game_runs set step=step+1,score=score+?,missed=? where user_id=? and day=? and topic=? and step=?',
                                          (int(correct),json.dumps(missed,ensure_ascii=False),uid,day,topic,step)).rowcount
                        row=c.execute('select * from chat_game_runs where user_id=? and day=? and topic=?',(uid,day,topic)).fetchone()
                    if changed:feedback=('Верно. ' if correct else 'Здесь лучше выбрать: «'+item['options'][item['correct']]+'». ')+item['why']+'\n\n'
            elif action!='s':raise ValueError()
            if row['step']>=5:
                if feedback:s['send'](uid,s['esc'](feedback.strip()))
                return finish(uid,topic,row)
            s['send'](uid,s['esc'](feedback)+question_text(topic,row['step']),buttons(day,topic,row['step']))
        except (ValueError,IndexError,TypeError):
            s['send'](uid,'Эта кнопка уже устарела. Напиши /game — открою сегодняшние игры.')

    def message(msg):
        text=msg.get('text','').strip().lower()
        uid=msg.get('from',{}).get('id')
        if text.split('@',1)[0] in ('/game','/игра','игра','давай играть') and uid and s['allowed'](uid):return menu(uid)
        return original_message(msg)

    def invite():
        day=s['today']().replace('-','')
        topic='f' if s['now']().date().toordinal()%2==0 else 'i'
        title=GAMES[topic]['title']
        body=('Друзья, у меня для вас короткая игра: «'+title+'» Пять ситуаций из наших уроков, без перехода в приложение. '
              'Жми кнопку, выбирай ответы — после каждого разберём решение. В конце получишь свой результат и подсказку для следующей съёмки.')
        keyboard=[[{'text':'Играть: '+title,'callback_data':f'cg:s:{day}:{topic}'}],
                  [{'text':'Выбрать другую игру','callback_data':'cg:menu'}]]
        key=hashlib.sha256(('chat-game:'+s['today']()).encode()).hexdigest()[:24]
        with s['conn']() as c:
            tables(c)
            for row in c.execute('select id from users where enabled=1').fetchall():
                c.execute('insert or ignore into notification_outbox(day,message_key,chat,body,keyboard) values(?,?,?,?,?)',
                          (s['today'](),key,json.dumps(row['id']),body,json.dumps(keyboard,ensure_ascii=False)))
        s['retry_notifications'](key)

    s.update({'callback':callback,'bot_message':message,'chat_game_invite':invite,'chat_game_menu':menu})

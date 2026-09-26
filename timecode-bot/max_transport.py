"""MAX transport primitives for TIMECODE. Disabled until a moderated bot token is configured.

See https://dev.max.ru/docs-api and https://dev.max.ru/docs/webapps/validation.
Telegram and MAX external IDs must never be used as interchangeable TIMECODE IDs.
"""
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
import os
import ssl
import html
import re

API = 'https://platform-api2.max.ru'


def verified_user(init_data, bot_token, *, clock=time.time, max_age=3600):
    """Return signed MAX user ID; reject unsigned, duplicate or stale launch fields."""
    if not isinstance(init_data, str) or not bot_token or len(init_data)>12000:return None
    try:
        fields=urllib.parse.parse_qsl(init_data,keep_blank_values=True,strict_parsing=True)
        keys=[key for key,_ in fields]
        if len(keys)!=len(set(keys)) or keys.count('hash')!=1:return None
        data=dict(fields)
        signature=data.pop('hash')
        if len(signature)!=64:return None
        raw='\n'.join(key+'='+value for key,value in sorted(data.items()))
        secret=hmac.new(b'WebAppData',bot_token.encode(),hashlib.sha256).digest()
        digest=hmac.new(secret,raw.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest,signature):return None
        age=clock()-int(data['auth_date'])
        if not -60<=age<=max_age:return None
        user=json.loads(data['user']);uid=user['id']
        if type(uid) is not int or uid<=0:return None
        return uid
    except (ValueError,KeyError,TypeError,OverflowError):return None


def valid_webhook_secret(received,expected):
    return bool(expected) and isinstance(received,str) and hmac.compare_digest(received,expected)


def api(method,path,token,payload=None,*,timeout=12):
    if not token:raise ValueError('MAX bot is not configured')
    if not path.startswith('/') or not method in ('GET','POST'):raise ValueError('Invalid API request')
    body=json.dumps(payload,ensure_ascii=False).encode() if payload is not None else None
    request=urllib.request.Request(API+path,data=body,method=method,headers={
        'Authorization':token,'Content-Type':'application/json'})
    ca=os.getenv('MAX_CA_FILE')
    context=ssl.create_default_context(cafile=ca) if ca else ssl.create_default_context()
    with urllib.request.urlopen(request,timeout=timeout,context=context) as response:
        return json.load(response)


def send_text(user_id,text,token,*,keyboard=None):
    if not isinstance(user_id,int) or user_id<=0:raise ValueError('Invalid MAX user')
    body={'text':str(text)[:4000],'format':'html'}
    if keyboard:
        body['attachments']=[{'type':'inline_keyboard','payload':{'buttons':keyboard}}]
    return api('POST','/messages?user_id='+str(user_id),token,body)


def keyboard_from_telegram(rows):
    """Convert the existing TIMECODE buttons to MAX buttons."""
    result=[]
    for row in rows or []:
        converted=[]
        for button in row:
            label=button.get('text','')
            if 'callback_data' in button:
                converted.append({'type':'callback','text':label,'payload':button['callback_data']})
            elif 'web_app' in button:
                converted.append({'type':'open_app','text':label})
            elif 'url' in button:
                destination=urllib.parse.urlsplit(button['url'])
                start=urllib.parse.parse_qs(destination.query).get('start',[''])[0]
                if destination.hostname=='t.me' and start in ('mission','instant'):
                    converted.append({'type':'callback','text':label,'payload':'max:start:'+start})
                elif destination.hostname!='t.me':
                    converted.append({'type':'link','text':label,'url':button['url']})
        if converted:result.append(converted)
    return result


def send_timecode(user_id,text,token,keyboard=None):
    """Match the Telegram send() result shape used by the delivery code."""
    try:
        response=send_text(user_id,text,token,keyboard=keyboard_from_telegram(keyboard))
        return {'ok':True,'result':response.get('message',response)}
    except Exception as error:
        print('MAX send failed:',type(error).__name__,flush=True)
        return {'ok':False}


def ensure_identity_table(c):
    c.execute('''create table if not exists messenger_identities (
        platform text not null, external_id text not null, user_id integer not null,
        primary key(platform,external_id))''')
    c.execute('create index if not exists identity_user on messenger_identities(user_id)')


def internal_id(c,platform,external_id):
    ensure_identity_table(c)
    row=c.execute('select user_id from messenger_identities where platform=? and external_id=?',
                  (platform,str(external_id))).fetchone()
    return row['user_id'] if row else None


def link_identity(c,platform,external_id,user_id):
    """Call only after the signed launch and TIMECODE invitation have both been checked."""
    if platform not in ('max','telegram') or type(user_id) is not int or user_id==0:
        raise ValueError('Invalid identity')
    ensure_identity_table(c)
    existing=internal_id(c,platform,external_id)
    if existing is not None and existing!=user_id:raise ValueError('Already linked to another student')
    c.execute('insert or ignore into messenger_identities(platform,external_id,user_id) values(?,?,?)',
              (platform,str(external_id),user_id))

"""Persist received MAX image metadata and bridge photos without exposing bot tokens."""
import json
import os
import re
import ssl
import threading
import urllib.parse
import urllib.request
import uuid

LOCK = threading.RLock()
LIMIT = 10 * 1024 * 1024


def ensure(s):
    with s['conn']() as c:
        c.execute("""create table if not exists shared_photo_assets (
            photo text primary key, url text not null default '',
            max_token text not null default '', tg_file_id text not null default '')""")


def remember(s, photo, url=''):
    ensure(s)
    with s['conn']() as c:
        c.execute("insert or ignore into shared_photo_assets(photo,url) values(?,?)", (photo,url))
        if url:c.execute('update shared_photo_assets set url=? where photo=?',(url,photo))


def trusted_url(url, telegram=False):
    p=urllib.parse.urlsplit(url)
    host=p.hostname or ''
    allowed=(host=='api.telegram.org' if telegram else
             any(host==d or host.endswith('.'+d) for d in ('max.ru','oneme.ru','okcdn.ru','mycdn.me')))
    if p.scheme!='https' or p.username or p.password or p.port not in (None,443) or not allowed:
        raise ValueError('Untrusted media host')
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        trusted_url(newurl,telegram=urllib.parse.urlsplit(req.full_url).hostname=='api.telegram.org')
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def request(url, data=None, headers=None, telegram=False):
    trusted_url(url,telegram)
    ca=os.getenv('MAX_CA_FILE') if not telegram else None
    context=ssl.create_default_context()
    if ca:context.load_verify_locations(cafile=ca)
    opener=urllib.request.build_opener(SafeRedirect(),urllib.request.HTTPSHandler(context=context))
    req=urllib.request.Request(url,data=data,headers=headers or {})
    with opener.open(req,timeout=25) as r:
        raw=r.read(LIMIT+1)
    if len(raw)>LIMIT:raise ValueError('Image exceeds bridge limit')
    return raw


def multipart(fields, field, data):
    boundary='timecode'+uuid.uuid4().hex
    parts=[]
    for key,value in fields.items():
        parts.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+key+'"\r\n\r\n'+str(value)+'\r\n').encode())
    parts.append(('--'+boundary+'\r\nContent-Disposition: form-data; name="'+field+'"; filename="frame.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode()+data+b'\r\n')
    parts.append(('--'+boundary+'--\r\n').encode())
    return b''.join(parts),{'Content-Type':'multipart/form-data; boundary='+boundary}


def download(s, photo, row):
    if photo.startswith('max:image:'):
        url=row['url']
        if not url:
            with s['conn']() as c:
                old=c.execute('select photo_url from daily_photos where photo=? and photo_url!=\'\' limit 1',(photo,)).fetchone()
            url=old['photo_url'] if old else ''
        if not url:raise ValueError('MAX image URL missing')
        return request(url)
    response=s['api']('getFile',{'file_id':photo})
    path=(response.get('result') or {}).get('file_path','')
    if not response.get('ok') or not re.fullmatch(r'[A-Za-z0-9_./-]+',path) or '..' in path or path.startswith('/'):
        raise ValueError('Telegram file unavailable')
    if (response['result'].get('file_size') or 0)>LIMIT:raise ValueError('Image exceeds bridge limit')
    return request('https://api.telegram.org/file/bot'+s['TOKEN']+'/'+path,telegram=True)


def send_photo(s, chat, photo, caption):
    """Cache compatible file IDs once, preserving the original author's photo."""
    from_max=photo.startswith('max:image:')
    # Telegram group IDs may also be negative; only mapped MAX identities are MAX.
    with s['conn']() as c:
        to_max=(isinstance(chat,int) and chat<0 and
                s['max_transport'].internal_id(c,'max',-chat) is not None)
    if from_max==to_max:
        if to_max:return s['max_transport'].send_image(-chat,photo[len('max:image:'):],s['esc'](caption),s['MAX_TOKEN'])
        return s['send_attachment'](chat,{'photo':[{'file_id':photo}]},caption)
    with LOCK:
        remember(s,photo)
        with s['conn']() as c:row=c.execute('select * from shared_photo_assets where photo=?',(photo,)).fetchone()
        if to_max:
            token=row['max_token']
            if not token:
                data=download(s,photo,row)
                endpoint=s['max_transport'].api('POST','/uploads?type=image',s['MAX_TOKEN'])
                body,headers=multipart({},'data',data)
                headers['Authorization']=s['MAX_TOKEN']
                result=json.loads(request(endpoint['url'],body,headers))
                token=str(result.get('token') or next((x.get('token') for x in (result.get('photos') or {}).values() if isinstance(x,dict) and x.get('token')),''))
                if not token:raise ValueError('MAX upload token missing')
                with s['conn']() as c:c.execute('update shared_photo_assets set max_token=? where photo=?',(token,photo))
            return s['max_transport'].send_image(-chat,token,s['esc'](caption),s['MAX_TOKEN'])
        if row['tg_file_id']:
            return s['send_attachment'](chat,{'photo':[{'file_id':row['tg_file_id']}]},caption)
        data=download(s,photo,row)
        body,headers=multipart({'chat_id':chat,'caption':caption[:1024]},'photo',data)
        result=json.loads(request('https://api.telegram.org/bot'+s['TOKEN']+'/sendPhoto',body,headers,telegram=True))
        images=(result.get('result') or {}).get('photo') or []
        if result.get('ok') and images:
            with s['conn']() as c:c.execute('update shared_photo_assets set tg_file_id=? where photo=?',(images[-1]['file_id'],photo))
        return result

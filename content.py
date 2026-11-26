"""Normalized readable message records; never expose raw XML or media keys."""
from wx4.forward import build_forward
from datetime import datetime, timezone

LABELS={'image':'Image','emoji':'Sticker','voice':'Voice message','video':'Video','file':'File','card':'Contact card','location':'Location','voip':'Call','chatrecord':'Forwarded chat','other':'Unsupported message','system':'System message','link':'Link','miniprogram':'Mini program','quote':'Reply'}

def describe(data,m,media=None,depth=0):
    kind=m['kind']; e=m.get('extra') or {}; text=m.get('text') or ''
    if kind in ('image','emoji','voice','video','file','card','location','voip','chatrecord','other'):
        details=e.get('filename') or e.get('title') or e.get('description') or ''
        text=f'[{LABELS.get(kind,kind)}]'+(' '+str(details) if details else '')
        if kind=='voice' and str(e.get('voice_length','')).isdigit():text+=f" ({int(e['voice_length'])/1000:g}s)"
    if kind in ('link','miniprogram'):
        text='\n'.join(dict.fromkeys(x for x in (text,e.get('title'),e.get('description'),e.get('url')) if isinstance(x,str) and x))
    result={'kind':kind,'text':text,'message_id':str(m.get('server_id') or m.get('local_id') or ''),'attachments':[]}
    if kind=='quote':
        q=e.get('reply') or {}; result['reply']={k:q.get(k,'') for k in ('sender','text','server_id')}
        if q:result['text']+='\n[Reply to '+str(q.get('sender') or 'Unknown')+'] '+str(q.get('text') or '')
    if kind=='chatrecord' and depth<6:
        f=m.get('forward') or build_forward(data,m); children=[]
        for child in f.get('messages',[]):
            r=describe(data,child,media,depth+1);r['sender']=child.get('sender','');r['timestamp']=datetime.fromtimestamp(child['create_time']).astimezone().isoformat(sep=' ') if child.get('create_time') else child.get('time_str','');children.append(r)
        result['forward']={'title':f.get('title',''),'messages':children,'truncated':bool(f.get('truncated')),'details_available':bool(children)}
        result['text']+='\n'+ ('\n'.join(f"{c['timestamp']} {c['sender']}: {c['text']}" for c in children) if children else '[Forwarded details unavailable]')
        if f.get('truncated'):result['text']+='\n[Forwarded record truncated]'
    if kind in ('image','emoji','voice','video','file'):
        result['attachments']=[media.save(data,m)] if media else [{'status':'not_requested','kind':kind}]
    return result

"""Portable, transactional batch exports, including an offline HTML viewer."""
import csv,html,json,re,shutil,tempfile,zipfile,os
from pathlib import Path
from datetime import datetime
from urllib.parse import quote
from collections import Counter
from reader import iter_messages
from attachments import LocalMedia

FIELDS=['timestamp','sender','sender_id','kind','message_id','text','attachments']
FORMATS=('html','txt','md','csv','json','jsonl','xlsx')
def cell(v):
    v=str(v or '');return "'"+v if re.match(r'^[\s\ufeff]*[=+\-@＝＋－＠]',v) else v

def resources(row):
    yield from row.get('attachments',[])
    for r in row.get('forward',{}).get('messages',[]):yield from resources(r)

def flat(r):
    return {k:('; '.join(a.get('path') or a.get('status','') for a in resources(r)) if k=='attachments' else r.get(k,'text' if k=='kind' else '')) for k in FIELDS}

def write(folder,session,rows,fmt,cancel=lambda:None):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True);p=folder/('chat.'+fmt)
    if fmt=='xlsx':
        import xlsxwriter
        with xlsxwriter.Workbook(str(p),{'constant_memory':True,'strings_to_formulas':False,'strings_to_urls':False}) as w:
            sheet=None
            for i,r in enumerate(rows):
                cancel()
                if i%1048575==0:
                    sheet=w.add_worksheet(f'Messages {i//1048575+1}');sheet.write_row(0,0,FIELDS);sheet.freeze_panes(1,0);sheet.set_column(0,0,26);sheet.set_column(1,4,20);sheet.set_column(5,5,85);sheet.set_column(6,6,45)
                sheet.write_row(i%1048575+1,0,[str(v)[:32767] for v in flat(r).values()])
            if sheet is None:w.add_worksheet('Messages').write_row(0,0,FIELDS)
        return p
    with p.open('w',encoding='utf-8-sig' if fmt=='csv' else 'utf-8',newline='') as f:
        if fmt=='csv':
            w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
            for r in rows:cancel();w.writerow({k:cell(v) for k,v in flat(r).items()})
        elif fmt=='json':
            f.write('{"conversation":'+json.dumps(session,ensure_ascii=False)+',"messages":[')
            for i,r in enumerate(rows):cancel();f.write((',' if i else '')+'\n'+json.dumps(r,ensure_ascii=False))
            f.write('\n]}')
        elif fmt=='jsonl':
            for r in rows:cancel();f.write(json.dumps(r,ensure_ascii=False)+'\n')
        elif fmt=='html':
            esc=html.escape;f.write('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src \'self\' data:; media-src \'self\'; script-src \'unsafe-inline\'"><title>'+esc(session['name'])+'</title><style>body{font:16px system-ui;margin:0 auto;max-width:850px;padding:24px;background:#f5f6f7;color:#20252a}header{position:sticky;top:0;background:#f5f6f7;padding:10px 0}input{width:95%;padding:12px}article{background:white;border-radius:12px;padding:14px;margin:12px 0;overflow-wrap:anywhere}small{color:#555}pre{white-space:pre-wrap;font:inherit}img,video{max-width:100%;max-height:450px}a{color:#176da4}</style><header><h1>'+esc(session['name'])+'</h1><input id="q" placeholder="Search this chat" aria-label="Search"><p id="n"></p></header><main>')
            for r in rows:
                cancel();f.write('<article><small>'+esc(r['timestamp']+' · '+r['sender'])+'</small><pre>'+esc(r['text'])+'</pre>')
                for a in resources(r):
                    if a.get('path'):
                        link=quote(a['path'],safe='/');f.write('<p><a href="'+link+'" download>'+esc(Path(a['path']).name)+'</a></p>')
                        if a['kind'] in ('image','emoji'):f.write('<img loading="lazy" src="'+link+'" alt="Attachment">')
                        elif a['kind']=='video':f.write('<video controls preload="none" src="'+link+'"></video>')
                    else:f.write('<small>'+esc(a.get('kind','')+': '+a.get('status',''))+'</small>')
                f.write('</article>')
            f.write('</main><script>const q=document.getElementById("q"),a=[...document.querySelectorAll("article")],n=document.getElementById("n");function filter(){let c=0;for(const r of a){r.hidden=!r.textContent.toLowerCase().includes(q.value.toLowerCase());if(!r.hidden)c++}n.textContent=c+" messages"}q.addEventListener("input",filter);filter()</script></html>')
        else:
            f.write(('## ' if fmt=='md' else 'Conversation: ')+session['name']+'\n\n')
            for r in rows:
                cancel();f.write(f"[{r['timestamp']}] {r['sender']}:\n{r['text']}\n")
                for a in resources(r):f.write(f"[{a.get('kind','')}: {a.get('path') or a.get('status','')}]\n")
                f.write('\n')
    return p

def batch(data,chosen,output,fmt,full=False,copy_media=False,archive=False,start=None,end=None,keyword='',account=None,cancel=lambda:None,progress=lambda *_:None,status=lambda _:None,image_keys=()):
    if fmt not in FORMATS:raise ValueError('Unknown format')
    output=Path(output);output.mkdir(parents=True,exist_ok=True);stage=Path(tempfile.mkdtemp(prefix='.wechat-export-',dir=output));summary=[];total=0;stats=Counter();target=None
    try:
        for i,s in enumerate(chosen,1):
            cancel();status(f'Exporting {i}/{len(chosen)}: {s["name"]}');name=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',s['name']).strip(' .')[:50] or 'chat';sub=stage/f'{i:04d}_{name}';sub.mkdir();media=LocalMedia(account,sub,cancel,image_keys) if full and copy_media else None
            local=Counter();number=[0]
            def tracked():
                for r in iter_messages(data,s['id'],start,end,cancel,full,keyword,media):
                    number[0]+=1;local.update(a.get('status','unknown') for a in resources(r));yield r
            stream=tracked()
            try:write(sub,s,stream,fmt,cancel)
            finally:stream.close()
            total+=number[0];stats.update(local);summary.append({'conversation':s,'messages':number[0],'file':(sub/('chat.'+fmt)).relative_to(stage).as_posix(),'attachment_status':dict(local)});progress(i,len(chosen))

        (stage/'manifest.json').write_text(json.dumps({'messages':total,'format':fmt,'full':full,'conversations':summary,'attachment_status':dict(stats)},ensure_ascii=False,indent=2),encoding='utf-8')
        if fmt=='html':(stage/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Chat exports</title><h1>Chat exports</h1><ul>'+''.join('<li><a href="'+quote(r['file'],safe='/')+'">'+html.escape(r['conversation']['name'])+'</a> ('+str(r['messages'])+')</li>' for r in summary)+'</ul>',encoding='utf-8')
        stamp=datetime.now().strftime('%Y%m%d-%H%M%S');base='WeChat_export_'+stamp
        if archive:
            fd,tmp=tempfile.mkstemp(prefix='.zip-',suffix='.tmp',dir=output);os.close(fd)
            try:
                with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=4) as z:
                    for f in sorted(stage.rglob('*')):
                        cancel()
                        if f.is_file():
                            with f.open('rb') as src,z.open(f.relative_to(stage).as_posix(),'w',force_zip64=True) as dst:
                                for b in iter(lambda:src.read(1024*1024),b''):cancel();dst.write(b)
                cancel();i=0
                while True:
                    target=output/(base+(f'_{i}' if i else '')+'.zip')
                    try:target.touch(exist_ok=False);break
                    except FileExistsError:i+=1
                try:os.replace(tmp,target)
                except BaseException:target.unlink(missing_ok=True);raise
            finally:Path(tmp).unlink(missing_ok=True)
        else:
            cancel();i=0
            while True:
                target=output/(base+(f'_{i}' if i else ''))
                try:target.mkdir();break
                except FileExistsError:i+=1
            try:
                for f in stage.iterdir():f.rename(target/f.name)
            except BaseException:shutil.rmtree(target,ignore_errors=True);raise
        return total,str(target),dict(stats)
    finally:shutil.rmtree(stage,ignore_errors=True)

import csv,json,re,hashlib,os,tempfile
from pathlib import Path

def export_chat(folder, session, rows, fmt, cancel=lambda:None):
    if fmt not in {'txt','md','csv','json'}:raise ValueError('Invalid output format.')
    stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',session['name']).strip(' .')[:65] or 'chat'
    stem='chat_'+stem+'_'+hashlib.sha256(session['id'].encode()).hexdigest()[:10]
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.export-',suffix='.tmp',dir=folder)
    try:
        with os.fdopen(fd,'w',encoding='utf-8-sig' if fmt=='csv' else 'utf-8',newline='') as f:
            if fmt=='csv':
                w=csv.DictWriter(f,fieldnames=['timestamp','sender','sender_id','text']);w.writeheader()
                # Excel formula injection prevention; original text unchanged in TXT/MD/JSON.
                for row in rows:
                    cancel();w.writerow({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()})
            elif fmt=='json':
                f.write('{"conversation": '+json.dumps(session,ensure_ascii=False)+', "messages": [')
                for i,row in enumerate(rows):
                    cancel();f.write((',' if i else '')+'\n'+json.dumps(row,ensure_ascii=False))
                f.write('\n]}\n')
            else:
                f.write(('## ' if fmt=='md' else 'Conversation: ')+session['name']+'\n\n')
                for r in rows:
                    cancel();f.write(f"[{r['timestamp']}] {r['sender']}:\n{r['text']}\n\n")
        cancel()
        n=0
        while True:
            path=folder/(stem+(f'_{n}' if n else '')+'.'+fmt)
            # Reserve name exclusively; atomic replacement of own reservation.
            try:
                with path.open('x'):pass
                break
            except FileExistsError:n+=1
        try:os.replace(tmp,path)
        except BaseException:path.unlink(missing_ok=True);raise
        return path
    finally:Path(tmp).unlink(missing_ok=True)

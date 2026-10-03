import re,glob,os,html
d=os.path.dirname(os.path.abspath(__file__));ch=os.path.join(d,'..','chapters')
out=['<article class="chapter" id="ch17" data-no="17" data-title="Formula and Fact Sheet" data-tag="Compiled from every chapter · read before the exam">',
'<h1>Formula and Fact Sheet</h1>',
'<p class="oneline">In one line: every rule and "Memorise this" box from the guide on one page, for the night before the exam.</p>',
'<p class="tip"><b>Exam facts (official PFRDA notification):</b> Phase I on 15 Oct 2026. Reasoning 30 questions, 25 marks, so 0.8333 per question (25 ÷ 30). Official wording: negative marking is ¼ of the marks assigned. This guide uses a flat −0.25 per wrong answer as you directed (check your call letter). Break-even chance about 23%. Paper 1 is 90 questions in one 60-minute timer, shared with English, Reasoning and General Awareness. Separate cut-off per paper plus an aggregate.</p>',
'<p class="src">This sheet is generated from the chapters themselves, after their fact-check. If a rule here looks odd, open its chapter and read the worked example. Nothing on this sheet is new.</p>']
files=sorted(f for f in glob.glob(ch+'/*.html') if not os.path.basename(f).startswith(('17-','16-')))
for f in files:
    s=open(f,encoding='utf-8').read()
    m=re.search(r'data-no="([^"]*)" data-title="([^"]*)"',s)
    if not m: continue
    no,title=m.groups()
    boxes=re.findall(r'<div class="box">(.*?)</div>',s,re.S)
    mems=re.findall(r'<div class="mem">(.*?)</div>',s,re.S)
    if not boxes and not mems: continue
    out.append(f'<section class="card"><h2><span class="n">{no}</span>{title}</h2>')
    seen=set()
    if boxes:
        out.append('<h3>Rules</h3>')
        for b in boxes:
            k=re.sub(r'\s+',' ',b).strip()
            if k in seen: continue
            seen.add(k);out.append(f'<div class="box">{k}</div>')
    for i,mm in enumerate(mems):
        mm=re.sub(r'<b>Memorise this</b>','',mm).strip()
        out.append(f'<h3>Memorise{" (lesson "+str(i+1)+")" if len(mems)>1 else ""}</h3><div class="mem">{mm}</div>')
    out.append('</section>')
out.append('<p class="src"><b>Sources:</b> each chapter lists its own fetched sources and which items are "derived, Python-checked". Exam facts: PFRDA 2026 notification.</p></article>')
open(os.path.join(ch,'17-formula-sheet.html'),'w',encoding='utf-8').write('\n'.join(out))
print(len(files),'chapters scanned, sheet',len('\n'.join(out))//1024,'KB')

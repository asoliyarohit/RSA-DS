import re
CARD=re.compile(r'<section class="card">(.*?)</section>',re.S)
def title_of(card):
    m=re.match(r'<h2>(?:<span class="n">\d+</span>)?(.*?)</h2>',card,re.S)
    return re.sub(r'<[^>]+>','',m.group(1)).strip() if m else ''
def det(summary,inner,cls='more'):
    return f'<details class="{cls}"><summary>{summary}</summary>{inner}</details>'
def transform(part, core_tags):
    no=re.search(r'data-no="([^"]*)"',part).group(1)
    # badge in tag
    badge=core_tags.get(no)
    if badge:
        part=re.sub(r'data-tag="([^"]*)"',lambda m:f'data-tag="{badge} · {m.group(1)}"',part,count=1)
    # collect and remove sources paragraphs
    srcs=re.findall(r'<p class="src">.*?</p>',part,re.S)
    part=re.sub(r'<p class="src">.*?</p>','',part,flags=re.S)
    out=[];pos=0;buf_why=[];buf_lab=[];buf_ex=[]
    def flush(kind):
        pass
    res=[];last=0
    cards=list(CARD.finditer(part))
    pieces=[];idx=0
    # process sequentially, grouping consecutive intuition cards, labs, examiner cards
    i=0;out=part[:cards[0].start()] if cards else part
    groups=[]  # list of (kind, [card_html])
    for m in cards:
        body=m.group(1);t=title_of(body)
        if t.startswith(('Picture this','The idea')): k='why'
        elif t.startswith('How the examiner asks'): k='ex'
        elif t.startswith('Lab'): k='lab'
        else: k='core'
        full=f'<section class="card">{body}</section>'
        between=part[m.end():m.end()+0]
        groups.append((k,full))
    # rebuild preserving non-card text between cards
    rebuilt=[];cur=None;buf=[]
    def emit():
        nonlocal cur,buf
        if not buf: return
        inner=''.join(buf)
        if cur=='why': rebuilt.append(det('Need the why? Picture it + the idea in small steps (2 min)',inner,'more why'))
        elif cur=='ex': rebuilt.append(det('Typical question wording (our style, optional)',inner))
        elif cur=='lab': rebuilt.append(det('Practice tool (optional)',inner))
        else: rebuilt.extend(buf)
        cur=None;buf=[]
    for (k,full) in groups:
        if k=='core':
            emit();rebuilt.append(full)
        else:
            if cur!=k: emit();cur=k
            buf.append(full)
    emit()
    # replace the block of cards region
    first=cards[0].start() if cards else 0;lastend=cards[-1].end() if cards else 0
    # text between cards (e.g. lesson headings h1/div wrappers) is rare; keep headings by scanning gaps
    gaps=[part[cards[j].end():cards[j+1].start()] for j in range(len(cards)-1)]
    gaptxt=''.join(g for g in gaps if g.strip())
    new=part[:first]+''.join(rebuilt)+gaptxt+part[lastend:]
    new=re.sub(r'(<section class="card"><h2>)<span class="n">\d+</span>',r'\1',new)
    if srcs:
        sd=det('Sources and what is unverified (all lessons)',''.join(srcs))
        new=re.sub(r'</article>\s*$',sd+'\n</article>',new)
    return new

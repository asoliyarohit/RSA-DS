import re,glob,html,sys
num=r'-?\d[\d,]*(?:\.\d+)?'
pat=re.compile(r'(?<![\w.])('+num+r')\s*([+−\-×x÷*/])\s*('+num+r')\s*=\s*('+num+r')(?![\d]|\.\d)')
def val(s):return float(s.replace(',',''))
tot=bad=0
for f in sorted(glob.glob('*.html')):
    t=open(f,encoding='utf-8').read()
    t=re.sub(r'<script[^>]*>.*?</script>',lambda m:m.group(0) if 'json' in m.group(0)[:60] else ' ',t,flags=re.S)
    t=html.unescape(re.sub(r'<[^>]+>',' ',t))
    for m in pat.finditer(t):
        a,op,b,c=m.groups();a,b,c=val(a),val(b),val(c)
        try:
            r={'+':a+b,'−':a-b,'-':a-b,'×':a*b,'x':a*b,'*':a*b,'÷':a/b if b else None,'/':a/b if b else None}[op]
        except Exception: continue
        pre=t[:m.start()].rstrip()[-1:] ; post=t[m.end():].lstrip()[:1]
        if pre in '+−-×x÷*/=^²³>→' or post in '+−-×x÷*/^²³%=→(': continue
        tot+=1
        if r is None: continue
        tol=max(0.011,abs(c)*0.0006)  # allow rounded values
        if abs(r-c)>tol:
            bad+=1;ctx=t[max(0,m.start()-40):m.end()+30].replace('\n',' ')
            print(f,'|',m.group(0),'| calc',round(r,4),'|',ctx)
print('checked',tot,'suspect',bad)

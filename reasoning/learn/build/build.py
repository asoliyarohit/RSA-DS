import glob,re,os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','..','..','refine'))
import core_transform as ct
d=os.path.dirname(os.path.abspath(__file__))
shell=open(d+'/shell.html',encoding='utf-8').read()
CORE=['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '14', '15', '16', '17', '1b']
parts=[open(f,encoding='utf-8').read() for f in sorted(glob.glob(d+'/../chapters/*.html'))]
def no(p): return re.search(r'data-no="([^"]*)"',p).group(1)
tags={no(p):('CORE' if no(p) in CORE else 'IF TIME') for p in parts}
full=shell.replace('@@CHAPTERS@@','\n'.join(parts))
core=shell.replace('@@CHAPTERS@@','\n'.join(ct.transform(p,tags) for p in parts))
open(d+'/../index-full.html','w',encoding='utf-8').write(full)
open(d+'/../index.html','w',encoding='utf-8').write(core)
print(len(parts),'chapters; core',len(core)//1024,'KB; full',len(full)//1024,'KB')

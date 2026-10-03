import glob,re,os,sys
d=os.path.dirname(os.path.abspath(__file__))
shell=open(d+'/shell.html',encoding='utf-8').read()
parts=[open(f,encoding='utf-8').read() for f in sorted(glob.glob(d+'/../chapters/*.html'))]
out=shell.replace('@@CHAPTERS@@','\n'.join(parts))
open(d+'/../index.html','w',encoding='utf-8').write(out)
print(len(parts),'chapters',len(out)//1024,'KB')

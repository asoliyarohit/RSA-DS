import re,sys,os
d=os.path.dirname(os.path.abspath(__file__))
s=open(os.path.join(d,'..','index.html'),encoding='utf-8').read()
title=re.search(r'<title>.*?</title>',s,re.S).group(0)
style=re.search(r'<style>(.*?)</style>',s,re.S).group(1)
body=re.search(r'<body>(.*)</body>',s,re.S).group(1)
style=style.replace('--bar:#7fb0ff;--bar2:#f2b04c}}','--bar:#7fb0ff;--bar2:#f2b04c;color-scheme:dark}}')
style=style.replace('--bar:#7fb0ff;--bar2:#f2b04c}\n*{','--bar:#7fb0ff;--bar2:#f2b04c;color-scheme:dark}\n*{')
style=style.replace('.topbar{position:sticky;top:0;','.topbar{position:sticky;top:env(safe-area-inset-top,0px);')
style=style.replace('#toc{position:fixed;inset:0;','#toc{position:fixed;inset:0;padding-top:env(safe-area-inset-top,0px);')
assert style.count('color-scheme:dark}')==2 and 'env(safe-area-inset-top' in style
out=title+'\n<style>'+style+'</style>\n'+body
open(sys.argv[1],'w',encoding='utf-8').write(out)
print(len(out)//1024,'KB',title,'external:',len(re.findall(r'<(?:script|link)[^>]+(?:src|href)="https?://',out)))

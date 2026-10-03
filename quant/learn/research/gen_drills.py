import random
from mental_math_verify import *
random.seed(2026)
def drill(day,kind,n=6):
    q=[]
    for _ in range(n):
        if kind=='ltr':
            a=random.randint(120,899);b=random.randint(120,899);q.append((f"{a} + {b}",a+b))
            assert ltr_add_steps(a,b)==a+b
        elif kind=='friendly':
            a=random.randint(420,900);b=random.choice([29,38,47,49,58,67,69,78,87,98,99,197,298,396])
            q.append((f"{a} - {b}",a-b)); assert friendly_sub(a,b)==a-b
        elif kind=='comp':
            k=random.choice([100,1000]);x=random.randint(11,k-1)
            q.append((f"{k} - {x}",k-x)); assert complement_sub(k,x)==k-x
        elif kind=='countup':
            b=random.randint(500,999);a=random.randint(100,b-50)
            q.append((f"{b} - {a}",b-a)); assert count_up(a,b)==b-a
        elif kind=='est':
            a=random.randint(200,990);b=random.randint(200,990);op=random.choice('+-')
            if op=='-' and a<b:a,b=b,a
            ex=a+b if op=='+' else a-b
            q.append((f"{a} {op} {b}  (estimate first, then exact)",ex))
    return q
plan={1:['ltr'],2:['ltr','friendly'],3:['friendly','comp'],4:['comp','countup'],5:['ltr','friendly','comp'],
6:['countup','est'],7:['ltr','friendly','comp','countup'],8:['est','ltr'],9:['friendly','comp','countup'],
10:['ltr','friendly','est'],11:['comp','countup','est','ltr'],12:['ltr','friendly','comp']}
out=[]
for d,ks in plan.items():
    out.append(f"**Day {d} drills** (write each step on paper)")
    ans=[]
    n=1
    for k in ks:
        out.append(f"- {k}:")
        for qq,a in drill(d,k,6 if len(ks)<=2 else 4):
            out.append(f"  {n}. {qq}"); ans.append(f"{n}={a}"); n+=1
    out.append(f"- Answer key (check AFTER): {', '.join(ans)}\n")
open('drills_generated.txt','w').write("\n".join(out))
print(len(out))

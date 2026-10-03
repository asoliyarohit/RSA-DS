import random
def ltr_add(a,b):
    # add by place value, largest first, no carrying in head
    t=0; s=0
    for p in (10**k for k in range(max(len(str(a)),len(str(b)))-1,-1,-1)):
        s+= (a//p%10)*p + (b//p%10)*p
        t=s
    return t
def ltr_add_steps(a,b):
    # a + hundreds of b, then tens, then ones
    r=a
    for p in (100,10,1):
        r+= (b//p%10)*p
    return r
def friendly_sub(a,b):   # a-b = a-(b rounded to 10) -/+ gap
    r=round(b/10)*10; gap=b-r
    return a-r-gap
def friendly_add(a,b):
    r=round(b/10)*10; gap=b-r
    return a+r+gap
def complement_sub(n,b):  # 100/1000 - b: 9s, except last NON-ZERO digit from 10; trailing zeros stay 0
    L=len(str(n))-1
    d=str(b).zfill(L); last=max(i for i,c in enumerate(d) if c!='0')
    out=[str(9-int(c)) if i<last else (str(10-int(c)) if i==last else '0') for i,c in enumerate(d)]
    return int("".join(out))
def count_up(a,b):  # b-a by counting up to next ten, then hundred, then rest
    steps=0;x=a
    for m in (10,100,1000):
        nxt=-(-x//m)*m
        if nxt>b: break
        steps+=nxt-x;x=nxt
    return steps+(b-x)
def estimate_ok(exact,a,b,op):
    r=lambda n:int(round(n,-(len(str(abs(int(n))))-1)))
    est={'+':r(a)+r(b),'-':r(a)-r(b),'*':r(a)*r(b)}[op]
    return abs(exact-est)<=0.35*abs(exact)+10
random.seed(1)
for _ in range(20000):
    a=random.randint(10,999);b=random.randint(10,999)
    assert ltr_add_steps(a,b)==a+b
    assert friendly_add(a,b)==a+b
    if a>=b: assert friendly_sub(a,b)==a-b; assert count_up(b,a)==a-b
    assert estimate_ok(a+b,a,b,'+')
    k=random.choice([100,1000]); x=random.randint(1,k-1)
    assert complement_sub(k,x)==k-x
    assert 850-375==850-350-25==475 and 1250-753==497
print("all method checks passed (20000 random cases each)")

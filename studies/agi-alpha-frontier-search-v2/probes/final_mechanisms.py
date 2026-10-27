import math
p=lambda th:(th+1)/2
h=1e-5
print((p(h)-p(-h))/(2*h))
print([(t,1/(2*math.sqrt(t))) for t in [1e-2,1e-4,1e-6]])
for a in [0,1]:
 b=1; reveal=(a==1); out=(a^b) if reveal else a
 print(a,b,reveal,out)


import json
ip_tuples={}
ip_list=[]
with open("files.txt", 'r') as p:
  files=p.readlines()
  for filename in files:
     data=[]
     with open("/data/maloss/sysdig/python.latest.finding/" + filename.strip(), 'r') as d:
       for line in d:
         try:
          response = json.loads(line)
          if "Network activity" in (response['output']):
           data.append(response['output'])
         except:
          continue

     for i in data:
        values=i.split(" ")
        connection = [s for i, s in enumerate(values) if 'connection' in s]
        container = [s for i, s in enumerate(values) if 'container' in s]
        for c in connection:
         try:
          src_dest =  (connection[0].split("=")[1])
          src = (src_dest.split('->')[0]).split(':')[0]
          if src not in ip_list:
             ip_list.append(src)
          dest = (src_dest.split('->')[1]).split(':')[0]
          if dest not in ip_list:
             ip_list.append(dest)
         except:
          continue
        if (src + ":" + dest) not in ip_tuples:
            ip_tuples[(src + ":" + dest)]=[]
            ip_tuples[(src + ":" + dest)].append(container) 
        else:
          if container not in ip_tuples[(src + ":" + dest)]:
            ip_tuples[(src + ":" + dest)].append(container)
     
count={}
for key,items in ip_tuples.items():
  count[key]=len(items)
from operator import itemgetter
l =  sorted(count.items(), key=itemgetter(1), reverse=True)
with open('ip_list.txt', 'w+') as f:
   f.write(json.dumps(l))

print(ip_list)

with open('ipreport.txt', 'w+') as f:
    for item in ip_list:
        f.write("%s\n" % item)

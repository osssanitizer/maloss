import json

name_site = {}
with open('rubygems_metadata.txt') as json_file:
    data = json.load(json_file)
    for p1 in data['ruby_package']:
	dep =  p1['dependencies']
        if dep:
	    for val in dep:
		print val
        else:
  	    print "list is empty..."
        if p1['author'] in name_site:
            continue
        names = []
        names.append(p1['author'])
        for p2 in data['ruby_package']:
	    #print p2['name']
            if p1['author'] == p2['author'] and p1['name'] != p2['name']:
	       #print p1['author']
               names.append(p2['name'])
        name_site[p1['author']]=names

with open('author_package_ruby.txt', 'a') as f:
    for key, value in name_site.items():
        f.write('%s:%s\n' % (key, value))

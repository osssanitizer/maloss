import json
import os,fnmatch
#from graph_tool.all import *
import csv

pattern = "*.metadata.json"
listOfFiles=os.listdir('.')

data = {}
data['ruby_package'] = []
for root, dirs, files in os.walk("."):
    package_name= root.strip("./")
    #print "-----------"
    print package_name

    for entry in files:
        if fnmatch.fnmatch(entry, pattern):
                filepath = os.path.join(root, entry)
                content_string = open(filepath, 'r').read()
                if content_string:
                    f = open(filepath)
                    metadata = json.load(f)
                    name = metadata["name"]
                    authors = metadata["authors"]
                    url = metadata["project_uri"]
                    downloads = metadata["downloads"]
                    version = metadata["version"]
                    dependencies=[]
                    if 'dependencies' in metadata and 'runtime' in metadata['dependencies']:
                        row = metadata["dependencies"]["runtime"]
                        for key in row:
                            dependencies.append(key["name"])
                    data['ruby_package'].append({
                        'name': name,
                        'author': authors,
                        'version': version,
                        'url': url,
                        'downloads':downloads,
                        'dependencies':dependencies
                    })
    print package_name



with open('rubygems_metadata.txt', 'w') as outfile:
    json.dump(data, outfile)


import sys
import json
import urllib
import requests
import argparse


# parse arguments
parser = argparse.ArgumentParser(prog="rubygems_dependents", description="Parse arguments")
parser.add_argument("name", help="Name of the package to query dependents")
parser.add_argument("-o", "--outfile", help="Path to the output file for storing dependents info")
args = parser.parse_args(sys.argv[1:])

name = args.name
outfile = args.outfile


def get_dependents(pkgName):
    metadata_url = "https://rubygems.org/api/v1/gems/%s/reverse_dependencies.json" % pkgName
    metadata_content = requests.request('GET', metadata_url)
    dependents = json.loads(metadata_content.text)
    print("%s has %d dependents (%s)" % (pkgName, len(dependents), dependents))
    return dependents


# breath-first search for dependents
dependents = set()
queue = [name]
while queue:
    vertex = queue.pop(0)
    if vertex not in dependents:
        dependents.add(vertex)
        queue.extend(set(get_dependents(vertex)) - dependents)
dependents -= {name}

# post-processing
print("there are %d dependents for package name %s" % (len(dependents), name))
if outfile:
    json.dump(list(dependents), open(outfile, 'w'), indent=2)

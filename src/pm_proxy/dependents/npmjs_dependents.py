import sys
import json
import urllib
import logging
import requests
import argparse
from urlparse import urljoin
from bs4 import BeautifulSoup


# parse arguments
parser = argparse.ArgumentParser(prog="npmjs_dependents", description="Parse arguments")
parser.add_argument("name", help="Name of the package to query dependents")
parser.add_argument("-o", "--outfile", help="Path to the output file for storing dependents info")
args = parser.parse_args(sys.argv[1:])

name = args.name
outfile = args.outfile


# deprecated
def get_dependents(pkgName):
    # npm-dependents
    # https://github.com/davidmarkclements/npm-dependents/blob/master/index.js#L17-L19
    metadata_url = "https://skimdb.npmjs.com/registry/_design/app/_view/dependedUpon?group_level=2&startkey=%5B%22" + pkgName + "%22%5D&endkey=%5B%22" + pkgName + "%22%2C%7B%7D%5D&skip=0&limit=10000"
    metadata_content = requests.request('GET', metadata_url)
    dependents = [row['key'][-1] for row in json.loads(metadata_content.text)['rows']]
    logging.warning("%s has %d dependents (%s)", pkgName, len(dependents), dependents)
    return dependents


def get_dependents_link(link):
    logging.warning("fetching link: %s", link)
    pkg_dep_content = requests.request('GET', link)
    soup = BeautifulSoup(pkg_dep_content.text, "lxml")
    dependents = {link.get('href').split('/package/')[-1] for link in soup.findAll('a', attrs={'target': '_self'}) if '/package/' in link.get('href')}
    logging.warning("link %s has %d packages (%s)", link, len(dependents), dependents)
    return dependents, soup


def get_dependents_html(pkgName):
    # current page
    base_link = "https://www.npmjs.com/browse/depended/%s" % pkgName
    dependents, soup = get_dependents_link(base_link)
    if len(dependents) == 0:
        return dependents

    # process next pages
    pkg_dep_next_page_url = [link.get('href') for link in soup.findAll('a', text='Next Page')]
    while pkg_dep_next_page_url:
        pkg_dep_next_page_url = urljoin(base_link, pkg_dep_next_page_url[0])
        next_page_dependents, soup = get_dependents_link(pkg_dep_next_page_url)
        dependents |= next_page_dependents
        pkg_dep_next_page_url = [link.get('href') for link in soup.findAll('a', text='Next Page')]
        logging.warning("collected %d dependents for %s so far", len(dependents), pkgName)
    # the total number of dependents
    logging.warning("%s has %d dependents (%s)", pkgName, len(dependents), dependents)
    return dependents


# breath-first search for dependents
dependents = set()
queue = [name]
while queue:
    vertex = queue.pop(0)
    if vertex not in dependents:
        dependents.add(vertex)
        queue.extend(set(get_dependents_html(vertex)) - dependents)
dependents -= {name}

# post-processing
print("there are %d dependents for package name %s" % (len(dependents), name))
if outfile:
    json.dump(list(dependents), open(outfile, 'w'), indent=2)


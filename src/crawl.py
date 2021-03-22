import logging
import csv
import re
import sys
import string
import datetime
import urllib2
import urlparse
import tempfile
import time
import json
import shutil
from urlparse import urljoin
from urllib import urlencode
from os.path import join

import requests
from lxml import etree
from bs4 import BeautifulSoup

from util.enum_util import LanguageEnum, PackageManagerEnum
from util.job_util import exec_command

PackageManager2Language = {
    PackageManagerEnum.pypi: LanguageEnum.python,
    PackageManagerEnum.npmjs: LanguageEnum.javascript,
    PackageManagerEnum.rubygems: LanguageEnum.ruby,
    PackageManagerEnum.maven: LanguageEnum.java,
    PackageManagerEnum.jcenter: LanguageEnum.java,
    PackageManagerEnum.jitpack: LanguageEnum.java,
    PackageManagerEnum.nuget: LanguageEnum.csharp,
    PackageManagerEnum.packagist: LanguageEnum.php,
    PackageManagerEnum.dockerhub: LanguageEnum.docker,
}

leaf_suffixes = ('.jar', '.md5', '.sha1', '.pom', '.xml', '.gz', '.zip', '.block', '.aar', '.war', '.asc',
                 '.htm', '.html', '.jsp', '.txt', '.tgz', '.tar', '.dmg', 'exe')


def jitpack_crawl(url, packages, jcenter_path="../data/jcenter.csv", maven_path="../data/maven.csv"):
    # search the packages from jcenter/maven against jitpack
    # https://jitpack.io/api/search?q=com.github.jitpack
    maven_packages = set(row['package name'] for row in csv.DictReader(open(maven_path, 'r')))
    jcenter_packages = set(row['package name'] for row in csv.DictReader(open(jcenter_path, 'r')))
    base_packages = maven_packages | jcenter_packages
    base_gids = set(pkg.split('/')[0] for pkg in base_packages)
    for base_gid in base_gids:
        try:
            # add parameters to url
            # https://stackoverflow.com/questions/2506379/add-params-to-given-url-in-python
            params = {'q': base_gid}
            url_parts = list(urlparse.urlparse(url))
            query = dict(urlparse.parse_qsl(url_parts[4]))
            query.update(params)
            url_parts[4] = urlencode(query)
            base_gid_search_url = urlparse.urlunparse(url_parts)
            logging.warning("fetching url %s for %s", base_gid_search_url, base_gid)
            content = requests.request('GET', base_gid_search_url)
            content_json = json.loads(content.text)
            logging.warning("collected %s packages from %s", len(content_json.keys()), base_gid)
            packages.update(content_json.keys())
        except Exception as e:
            logging.error("unexpected error: %s", str(e))


def jcenter_crawl(url, packages, retries=3, wait_time=3600):
    html_page = None
    while retries:
        try:
            html_page = exec_command('curl', ['curl', url], ret_stdout=True)
            break
        except Exception as e:
            logging.error("error using curl for url %s, error: %s", url, str(e))
            try:
                html_page = urllib2.urlopen(url)
                break
            except urllib2.HTTPError as he:
                logging.error("starting to be blocked, wait %s seconds, error: %s", wait_time, str(he))
                time.sleep(wait_time)
                retries -= 1
            except Exception as e:
                logging.error("unexpected error: %s", str(e))
    soup = BeautifulSoup(html_page, "lxml")
    logging.warning("url is: %s", url)
    links = {link.get('href').lstrip(':') for link in soup.findAll('a')}
    links = [link for link in links if not link.startswith('.')]
    if 'maven-metadata.xml' in links or 'maven-metadata.xml.sha1' in links or 'maven-metadata.xml.md5' in links:
        logging.warning("identified new package: %s", url)
        # FIXME: parse url for package name
        package_name = url.split('/jcenter.bintray.com/', 1)[-1]
        packages.add(package_name)
    else:
        valid_links = filter(lambda link: not link.startswith('..') and not link.endswith(leaf_suffixes) and 'jcenter.bintray.com' in urljoin(url, link), links)
        logging.warning("there are %d valid links before '/' filtering", len(valid_links))
        valid_links = filter(lambda link: link.endswith("/"), valid_links)
        logging.warning("there are %d valid links!", len(valid_links))
        for valid_link in valid_links:
            next_url = urljoin(url, valid_link)
            if next_url == url:
                continue
            logging.warning("next url is: %s", next_url)
            jcenter_crawl(next_url, packages)


def maven_crawl(url, packages, retries=3, wait_time=3600):
    html_page = None
    while retries:
        try:
            html_page = exec_command('curl', ['curl', url], ret_stdout=True)
            break
        except Exception as e:
            logging.error("error using curl for url %s, error: %s", url, str(e))
            try:
                html_page = urllib2.urlopen(url)
                break
            except urllib2.HTTPError as he:
                logging.error("starting to be blocked, wait %s seconds, error: %s", wait_time, str(he))
                time.sleep(wait_time)
                retries -= 1
            except Exception as e:
                logging.error("unexpected error: %s", str(e))
                return

    soup = BeautifulSoup(html_page, "lxml")
    logging.warning("url is: %s", url)
    links = {link.get('href') for link in soup.findAll('a')}
    if 'maven-metadata.xml' in links or 'maven-metadata.xml.sha1' in links or 'maven-metadata.xml.md5' in links:
        logging.warning("identified new package: %s", url)
        # FIXME: parse url for package name
        package_name = url.split('/maven2/', 1)[-1]
        packages.add(package_name)
    else:
        if not any(link.endswith(('.jar', '.pom', '.aar', '.war')) for link in links):
            valid_links = filter(lambda link: not link.startswith('..') and not link.endswith(leaf_suffixes) and 'repo1.maven.org' in urljoin(url, link), links)
            logging.warning("there are %d valid links before '/' filtering", len(valid_links))
            valid_links = filter(lambda link: link.endswith("/"), valid_links)
            logging.warning("there are %d valid links!", len(valid_links))
            for valid_link in valid_links:
                next_url = urljoin(url, valid_link)
                if next_url == url:
                    continue
                logging.warning("next url is: %s", next_url)
                maven_crawl(next_url, packages)
        else:
            logging.warning("skipping url due to lack of pom: %s", url)


def get_stats_wrapper(infile, outfile, package_manager):
    reader = csv.DictReader(open(infile, 'r'))
    if 'package name' not in reader.fieldnames:
        raise Exception("field package name is not in %s" % reader.fieldnames)
    if 'downloads' not in reader.fieldnames:
        fieldnames = reader.fieldnames + ['downloads']
    else:
        fieldnames = reader.fieldnames
    writer = csv.DictWriter(open(outfile, 'w'), fieldnames=fieldnames)
    writer.writeheader()
    for row in reader:
        _, downloads = get_stats(package_name=row['package name'], package_manager=package_manager)
        row['downloads'] = downloads
        writer.writerow(row)


def get_stats(package_name, package_manager):
    if package_manager == PackageManagerEnum.pypi:
        # pypi stats
        # https://github.com/crflynn/pypistats.org
        # https://pypistats.org/api/
        # https://pypi.org/project/pypistats/
        recent_url = "https://pypistats.org/api/packages/%s/recent" % package_name
        overall_url = "https://pypistats.org/api/packages/%s/overall" % package_name
        downloads = {}
        try:
            # get the recent downloads
            recent_content = requests.request('GET', recent_url)
            recent_downloads = json.loads(recent_content.text)['data']
            downloads.update(recent_downloads)
            # get the overall downloads
            overall_content = requests.request('GET', overall_url)
            overall_downloads = sum([record['downloads'] for record in json.loads(overall_content.text)['data'] if
                                     record['category'] == 'with_mirrors'])
            downloads['overall'] = overall_downloads
        except Exception as e:
            logging.error("fail to get download stats for package %s: %s", package_name, e)
        return (package_name, downloads)
    elif package_manager == PackageManagerEnum.npmjs:
        # npmjs stats api
        # https://github.com/npm/registry/blob/master/docs/REGISTRY-API.md
        # https://github.com/npm/registry/blob/master/docs/download-counts.md
        # existing tools
        # https://github.com/pvorb/npm-stat.com
        # https://github.com/npm/download-counts
        # bulk query doesn't support scoped packages
        # https://api.npmjs.org/downloads/point/last-day/npm,express
        date_today = datetime.date.today()
        date_today_str = date_today.strftime('%Y-%m-%d')
        date_last_year = date_today.replace(year=date_today.year - 1)
        date_last_year_str = date_last_year.strftime('%Y-%m-%d')
        # three years back
        date_overall1 = date_today - datetime.timedelta(18*365/12)
        date_overall2 = date_overall1 - datetime.timedelta(18*365/12)
        date_overall1_str = date_overall1.strftime('%Y-%m-%d')
        date_overall2_str = date_overall2.strftime('%Y-%m-%d')
        # recent downloads
        last_week_url = "https://api.npmjs.org/downloads/point/last-week/%s" % package_name
        last_month_url = "https://api.npmjs.org/downloads/point/last-month/%s" % package_name
        last_year_url = "https://api.npmjs.org/downloads/point/%s:%s/%s" % (
            date_last_year_str, date_today_str, package_name)
        # data is limited to 18 months of data
        overall1_url = "https://api.npmjs.org/downloads/point/%s:%s/%s" % (
            date_overall1_str, date_today, package_name)
        overall2_url =  "https://api.npmjs.org/downloads/point/%s:%s/%s" % (
            date_overall2_str, date_overall1_str, package_name)
        downloads = {}
        try:
            last_week_content = requests.request('GET', last_week_url)
            last_week_downloads = json.loads(last_week_content.text)['downloads']
            downloads['last_week'] = last_week_downloads
            last_month_content = requests.request('GET', last_month_url)
            last_month_downloads = json.loads(last_month_content.text)['downloads']
            downloads['last_month'] = last_month_downloads
            last_year_content = requests.request('GET', last_year_url)
            last_year_downloads = json.loads(last_year_content.text)['downloads']
            downloads['last_year'] = last_year_downloads
            overall1_content = requests.request('GET', overall1_url)
            overall1_downloads = json.loads(overall1_content.text)['downloads']
            overall2_content = requests.request('GET', overall2_url)
            overall2_downloads = json.loads(overall2_content.text)['downloads']
            downloads['overall'] = overall1_downloads + overall2_downloads
        except Exception as e:
            logging.error("fail to get download stats for package %s: %s", package_name, e)
        return (package_name, downloads)
    elif package_manager == PackageManagerEnum.rubygems:
        # rubygems stats
        # https://guides.rubygems.org/rubygems-org-api/
        # https://rubygems.org/api/v1/downloads/[GEM NAME]-[GEM VERSION].(json|yaml)
        # rate limit setting
        # https://guides.rubygems.org/rubygems-org-api/
        # API and website: 10 requests per second
        # Dependency API: 15 requests per second
        overall_url = "https://rubygems.org/api/v1/gems/%s.json" % package_name
        downloads = {}
        try:
            # get the overall downloads
            overall_content = requests.request('GET', overall_url)
            overall_downloads = json.loads(overall_content.text)['downloads']
            downloads['overall'] = overall_downloads
        except Exception as e:
            logging.error("fail to get download stats for package %s: %s", package_name, e)
        return (package_name, downloads)
    elif package_manager == PackageManagerEnum.packagist:
        # packagist stats
        # https://packagist.org/apidoc
        # https://packagist.org/packages/[vendor]/[package].json
        vendor, product = package_name.split('/')
        overall_url = "https://packagist.org/packages/%s/%s.json" % (vendor, product)
        downloads = {}
        try:
            # get the overall downloads
            overall_content = requests.request('GET', overall_url)
            overall_downloads = json.loads(overall_content.text)['package']['downloads']
            downloads['overall'] = overall_downloads['total']
            downloads['last_month'] = overall_downloads['monthly']
            downloads['last_day'] = overall_downloads['daily']
        except Exception as e:
            logging.error("fail to get download stats for package %s: %s", package_name, e)
        return (package_name, downloads)
    elif package_manager == PackageManagerEnum.nuget:
        # nuget stats, not available yet, may add in the future
        # https://api-v2v3search-0.nuget.org/query?q=NuGet.Versioning&prerelease=false
        raise Exception("nuget statistics is available, not implemented yet!")
    elif package_manager == PackageManagerEnum.maven:
        # maven stats, not available, use mvnrepository or jcenter
        raise Exception("maven statistics is not available, nor implemented!")
    elif package_manager == PackageManagerEnum.jcenter:
        # jcenter stats, some of them are available
        # http://jcenter.bintray.com/
        raise Exception("jcenter statistics is available, not implemented yet!")
    elif package_manager == PackageManagerEnum.jitpack:
        # jitpack stats
        # https://jitpack.io/api/stats/com.github.jitpack/gradle-modular
        recent_url = "https://jitpack.io/api/stats/%s" % package_name
        downloads = {}
        try:
            recent_content = requests.request('GET', recent_url)
            recent_downloads = json.loads(recent_content.text)
            downloads['last_month'] = recent_downloads['month']
            downloads['last_week'] = recent_downloads['week']
        except Exception as e:
            logging.error("fail to get download stats for package %s: %s", package_name, e)
        return (package_name, downloads)
    elif package_manager == PackageManagerEnum.dockerhub:
        # docker hub stats
        raise Exception("Not implemented yet!")
    else:
        raise Exception("package manager %s not supported yet!" % package_manager)


def write_packages(package_names, package_manager, outfile, stats=False, processes=1):
    fieldnames = ['package name', 'version', 'source', 'downloads', 'language']
    writer = csv.DictWriter(open(outfile, 'w'), fieldnames=fieldnames)
    writer.writeheader()
    if stats:
        from functools import partial
        get_stats_partial = partial(get_stats, package_manager=package_manager)
        if processes > 1:
            from multiprocessing import Pool
            pool = Pool(processes=processes)
            package_names_downloads = pool.map(get_stats_partial, package_names)
            pool.close()
            pool.join()
            for package_name, downloads in package_names_downloads:
                writer.writerow({'package name': package_name, 'source': str(package_manager),
                                 'downloads': downloads,
                                 'language': str(PackageManager2Language[package_manager])})
        else:
            for package_name in package_names:
                writer.writerow({'package name': package_name, 'source': str(package_manager),
                                 'downloads': get_stats_partial(package_name)[1],
                                 'language': str(PackageManager2Language[package_manager])})
    else:
        for package_name in package_names:
            writer.writerow({'package name': package_name, 'source': str(package_manager),
                             'language': str(PackageManager2Language[package_manager])})


def crawl(package_manager, outfile, infile=None, stats=False, processes=1):
    fieldnames = ['package name', 'version', 'source', 'downloads', 'language']
    if package_manager == PackageManagerEnum.pypi:
        # brew install pip
        pypi_link = 'https://pypi.python.org/simple/'
        pypi_content = requests.request('GET', pypi_link)
        root = etree.fromstring(pypi_content.text)
        package_names = [package.text for package in root.xpath("//a[@href]")]
        logging.warning("there are %d packages in %s", len(package_names), package_manager)
        write_packages(package_names=package_names, package_manager=package_manager, outfile=outfile, stats=stats,
                       processes=processes)

    elif package_manager == PackageManagerEnum.npmjs:
        # brew install node
        # https://www.npmjs.com/package/all-the-package-names
        # a list of 2742 JavaScript modules with C++ addons
        # https://github.com/nice-registry/native-modules
        extract_temp_dir = tempfile.mkdtemp(prefix="all-the-package-names-")
        extract_all_package_software = ['tar', '-zxf', 'third-party/all-the-package-names-1.3544.0.tar.gz',
                                        '--strip', '1', '-C', extract_temp_dir]
        exec_command('tar -zxf all-the-package-names', extract_all_package_software)
        install_all_package_dep = ['npm', 'install']
        exec_command('npm install dependencies', install_all_package_dep, cwd=extract_temp_dir)
        build_all_package_software = ['npm', 'run-script', 'build']
        exec_command('npm run-script build', build_all_package_software, cwd=extract_temp_dir)
        packages = json.load(open(join(extract_temp_dir, 'names.json'), 'r'))
        shutil.rmtree(extract_temp_dir)
        logging.warning("there are %d packages in %s", len(packages), package_manager)
        invalid_characters = ['?', '!', '*', '~', "'", '(', ')', '{', '}', '|', ' ', '"']
        package_names = []
        for package in packages:
            if any(ch in package for ch in invalid_characters):
                logging.error("skipping package %s due to invalid character!", package)
                continue
            if '@' in package and package[0] != '@':
                logging.error("skipping package %s due to invalid character!", package)
                continue
            package_names.append(package)
        write_packages(package_names=package_names, package_manager=package_manager, outfile=outfile, stats=stats,
                       processes=processes)

    elif package_manager == PackageManagerEnum.rubygems:
        # brew install ruby
        gem_cmd = ['gem', 'search']
        gem_output = exec_command('gem search', gem_cmd, ret_stdout=True)
        gem_pattern = re.compile(r'([^\(\) ]+) \(([^\)]+)\)')
        packages = filter(lambda k: re.match(gem_pattern, k), gem_output.split('\n'))
        logging.warning("there are %d packages in %s", len(packages), package_manager)
        package_names = [re.match(gem_pattern, package).groups()[0] for package in packages]
        write_packages(package_names=package_names, package_manager=package_manager, outfile=outfile, stats=stats,
                       processes=processes)

    elif package_manager == PackageManagerEnum.packagist:
        # The easiest way to work with the packagist API
        # https://github.com/spatie/packagist-api/blob/master/src/Packagist.php
        # PHP API for Packagist
        # https://github.com/KnpLabs/packagist-api
        packagist_link = 'https://packagist.org/packages/list.json'
        packagist_content = requests.request('GET', packagist_link)
        packages = json.loads(packagist_content.text)['packageNames']
        logging.warning("there are %d packages in total for %s", len(packages), package_manager)
        write_packages(package_names=packages, package_manager=package_manager, outfile=outfile, stats=stats,
                       processes=processes)

    elif package_manager in (PackageManagerEnum.maven, PackageManagerEnum.jcenter, PackageManagerEnum.jitpack):
        # https://search.maven.org/
        packages = set()
        sys.setrecursionlimit(10000)
        if package_manager == PackageManagerEnum.maven:
            maven_crawl('https://repo1.maven.org/maven2/', packages)
        elif package_manager == PackageManagerEnum.jcenter:
            jcenter_crawl('http://jcenter.bintray.com/', packages)
        elif package_manager == PackageManagerEnum.jitpack:
            jitpack_crawl('https://jitpack.io/api/search', packages)
        else:
            raise Exception("Not implemented for %s yet!" % package_manager)
        logging.warning("there are %d packages in %s", len(packages), package_manager)
        package_names = []
        for package in packages:
            if package_manager in (PackageManagerEnum.maven, PackageManagerEnum.jcenter):
                # remove the trailing '/'
                package = package.strip('/')
                if '/' not in package:
                    logging.warning("found false positive %s, ignoring!", package)
                    continue
                else:
                    group_id, artifact_id = package.rsplit('/', 1)
                    group_id = group_id.replace('/', '.')
            elif package_manager == PackageManagerEnum.jitpack:
                if ':' not in package:
                    logging.warning("found false positive %s, ignoring!", package)
                    continue
                else:
                    group_id, artifact_id = package.split(':', 1)
            else:
                raise Exception("Not implemented for %s yet!" % package_manager)
            package = '%s/%s' % (group_id, artifact_id)
            package_names.append(package)
        # maven doesn't have stats, jcenter and jitpack have stats
        write_packages(package_names=package_names, package_manager=package_manager, outfile=outfile, stats=stats,
                       processes=processes)

    elif package_manager == PackageManagerEnum.nuget:
        # macos install: brew install nuget
        # https://www.nuget.org/packages
        # Get list of all packages using v3 API
        # https://github.com/NuGet/Home/issues/3259
        if infile is None:
            logging.warning("querying nuget for list of packages, this is slow, be patient! "
                            "querying this may timeout and raise error! "
                            "run `nuget list > nuget_raw.txt` separately and use -i to process the results!")
            nuget_cmd = ['nuget', 'list']
            nuget_output = exec_command('nuget list', nuget_cmd, ret_stdout=True)
        else:
            nuget_output = open(infile, 'r').read()
        packages = filter(bool, nuget_output.split('\n'))
        logging.warning("there are %d packages in %s", len(packages), package_manager)
        # for packages that span two lines (maximum), there can be two cases. Previous with space, current with space
        package_names = []
        index = 0
        while index < len(packages):
            package = packages[index]
            # not the last package
            if index < len(packages) - 1:
                next_package = packages[index+1]
                if len(package) > len(next_package) and not(' ' in package and ' ' in next_package):
                    if ' ' in package or ' ' in next_package:
                        package = package + next_package
                    else:
                        package = package + ' ' + next_package
                    index += 1
            pname, version = package.split(' ', 1)
            # FIXME: we are ignoring version information here
            package_names.append(pname)
            index += 1
        write_packages(package_names=package_names, package_manager=package_manager, outfile=outfile, stats=stats,
                       processes=processes)

    elif package_manager == PackageManagerEnum.dockerhub:
        raise Exception("Not implemented yet!")

    elif package_manager == PackageManagerEnum.cpan:
        raise Exception("Not implemented yet!")

    else:
        raise Exception("package manager %s not supported yet!" % package_manager)



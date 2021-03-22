import os
import re
import csv
import sys
import json
import time
import random
import shutil
import pickle
import tarfile
import logging
import datetime
import tempfile
import networkx
import dateutil.parser

from ast import literal_eval
from os.path import basename, dirname, join, exists, splitext, relpath

import proto.python.ast_pb2 as ast_pb
import proto.python.behavior_pb2 as behavior_pb

from multiprocessing import Pool, cpu_count
from functools import partial
from util.enum_util import LanguageEnum, PackageManagerEnum, TraceTypeEnum, DataTypeEnum, FalcoRuleEnum
from util.compress_files import decompress_file, get_file_with_meta
from static_util import get_static_proxy_for_language, taint, astfilter
from pm_util import get_pm_proxy_for_language, get_pm_proxy
from util.job_util import write_proto_to_file, read_proto_from_file, exec_command
from static_proxy.static_base import StaticAnalyzer
from proto.python.info_pb2 import PackageInfo
from proto.python.ast_pb2 import PkgAstResults, AstLookupConfig
from proto.python.behavior_pb2 import DynamicAnalysis


def load_dep_graph(language, popular=False, versions=False):
    # Read tar.gz file in python
    # https://stackoverflow.com/questions/37474767/read-tar-gz-file-in-python
    language2cached_dep_graph = {
        # three files are listed: overall, popular, popular versions
        LanguageEnum.javascript: [
            '../airflow/data/npmjs.with_stats.dep_graph.pickle.tgz',
            '../airflow/npmjs_dags0/npmjs.with_stats.popular.pickle',
            '../airflow/data/npmjs.with_stats.popular.versions.dep_graph.pickle.tgz'
        ],
        LanguageEnum.python: [
            '../airflow/data/pypi.with_stats.dep_graph.pickle.tgz',
            '../airflow/pypi_dags/pypi.with_stats.popular.pickle',
            '../airflow/data/pypi.with_stats.popular.versions.dep_graph.pickle.tgz'
        ],
        LanguageEnum.ruby: [
            '../airflow/data/rubygems.with_stats.dep_graph.pickle.tgz',
            '../airflow/rubygems_dags/rubygems.with_stats.popular.pickle',
            '../airflow/data/rubygems.with_stats.popular.versions.dep_graph.pickle.tgz'
        ],
        LanguageEnum.php: [
            '../airflow/data/packagist.with_stats.dep_graph.pickle.tgz',
            '../airflow/packagist_dags/packagist.with_stats.popular.pickle',
            '../airflow/data/packagist.with_stats.popular.versions.dep_graph.pickle.tgz'
        ],
        LanguageEnum.java: [
            '../airflow/data/maven.dep_graph.pickle.tgz'
        ]
    }
    if popular and not versions:
        index = 1
    elif popular and versions:
        index = 2
    elif not popular and not versions:
        index = 0
    else:
        raise Exception("Unexpected input: popular=%s, versions=%s" % (popular, versions))
    dep_graph_file = language2cached_dep_graph[language][index]
    logging.warning("loading dep graph from %s", dep_graph_file)
    if dep_graph_file.endswith('.tgz'):
        # there is only one file in the tarball archive
        dep_graph = tarfile.open(dep_graph_file, "r:gz")
        for member in dep_graph.getmembers():
            return pickle.load(dep_graph.extractfile(member))
    elif dep_graph_file.endswith('.pickle'):
        return pickle.load(open(dep_graph_file, 'r'))
    else:
        raise Exception("Unexpected format/extension of dep graph file: %s" % dep_graph_file)


def filter_pkg(infile, outfile, language, out_dir, cache_dir, configpath, check_dep=False, check_flow=False):
    """
    Filter packages for further analysis.
    1. Can be filtered by API intact only or including dependencies.
    2. Can be filtered by specific source/sink combinations
    """
    configpb = AstLookupConfig()
    read_proto_from_file(proto=configpb, filename=configpath, binary=False)
    api_filter = set(api.full_name for api in configpb.apis)
    if check_dep:
        # TODO: add dep API tracker
        pass
    if check_flow:
        # TODO: add flow filter
        flow_filter = set()
    reader = csv.DictReader(open(infile, 'r'))
    writer = csv.DictWriter(open(outfile, 'w'), fieldnames=reader.fieldnames)
    writer.writeheader()
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
    static_proxy = get_static_proxy_for_language(language=language)
    for row in reader:
        pkg_name = row['package name']
        astgen_result = static_proxy.get_astgen_result(pm_proxy=pm_proxy, pkg_name=pkg_name, outdir=out_dir, cache_only=True)
        # TODO: add flow filter and dep API tracker
        if astgen_result and any(api_result.full_name in api_filter for api_result in astgen_result.pkgs[0].api_results):
            writer.writerow(row)


def interpret_result(infile, outfile, data_type, language, package_manager=None, outdir=None, cache_dir=None,
                     skip_file=None, compare_ast_options_file=None, detail_mapping=False, detail_filename=False):
    # NOTE: These options are only relevant to compare_ast related jobs.
    compare_ast_options = json.load(open(compare_ast_options_file, 'r')) if compare_ast_options_file and exists(
        compare_ast_options_file) else []
    # This is a check inspired by datagrid and simple_captcha2. Find the packages with recently published privileged old versions.
    privileged_recent_old_version = 'privileged_recent_old_version' in compare_ast_options
    enable_api_interest_filtering = 'enable_api_interest_filtering' in compare_ast_options
    enable_permission_interest_filtering = 'enable_permission_interest_filtering' in compare_ast_options

    if data_type == DataTypeEnum.api:
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        static_proxy = get_static_proxy_for_language(language=language)
        counters = {}
        for row in csv.DictReader(open(infile, 'r')):
            pkg_name = row['package name']
            astgen_result = static_proxy.get_astgen_result(pm_proxy=pm_proxy, pkg_name=pkg_name, outdir=outdir,
                                                           cache_only=True)
            if astgen_result:
                if detail_mapping:
                    counters.setdefault('analyzed', set())
                    counters['analyzed'].add(pkg_name)
                else:
                    counters.setdefault('analyzed', 0)
                    counters['analyzed'] += 1
                for api_result in astgen_result.pkgs[0].api_results:
                    api_full_name = api_result.full_name
                    if detail_filename:
                        api_full_name = '%s:%s' % (api_result.range.start.file_info.filename, api_full_name)
                    if detail_mapping:
                        counters.setdefault(api_full_name, set())
                        counters[api_full_name].add(pkg_name)
                    else:
                        counters.setdefault(api_full_name, 0)
                        counters[api_full_name] += 1
        if detail_mapping:
            # Dump both the stats and the detail mapping
            json.dump({k: list(v) for k, v in counters.items()}, open(outfile, 'w'), indent=2)
            json.dump({k: len(v) for k, v in counters.items()}, open(outfile + ".stats", 'w'), indent=2)
        else:
            json.dump(counters, open(outfile, 'w'), indent=2)
    elif data_type == DataTypeEnum.dependency:
        dep_tree = load_dep_graph(language=language, popular=True)
        logging.info("loaded dep_tree with %d nodes", dep_tree.number_of_nodes())
        counters = {}
        packages = {row['package name'] for row in csv.DictReader(open(infile, 'r'))}
        # FIXME: add support for detail_mapping
        for pkg in dep_tree.nodes():
            if str(pkg) not in packages:
                continue
            dep_count = len(list(dep_tree.successors(pkg)))
            flatten_dep_count = len(networkx.descendants(dep_tree, pkg))
            counters.setdefault('dep_count', [])
            counters['dep_count'].append(dep_count)
            counters.setdefault('flatten_dep_count', [])
            counters['flatten_dep_count'].append(flatten_dep_count)
        json.dump(counters, open(outfile, 'w'), indent=2)
    elif data_type == DataTypeEnum.reverse_dep:
        # dep_tree = load_dep_graph(language=language, popular=True)
        dep_tree = load_dep_graph(language=language)
        logging.info("loaded dep_tree with %d nodes", dep_tree.number_of_nodes())
        pkg2reverse_deps = {}
        for row in csv.DictReader(open(infile, 'r')):
            pkg_manager = row['Package Manager']
            pkg_name = row['Package Name']
            if pkg_manager and pkg_manager != 'N/A' and PackageManagerEnum(pkg_manager) == package_manager:
                if pkg_name in dep_tree:
                    pkg2reverse_deps[pkg_name] = list(networkx.ancestors(dep_tree, pkg_name))
                else:
                    logging.error("skipping %s because its not in the dep graph!", pkg_name)
            else:
                logging.warning("skipping %s because its package manager is %s and the dep graph is not loaded!",
                                pkg_name, pkg_manager)
        json.dump(pkg2reverse_deps, open(outfile, 'w'), indent=2)
    elif data_type == DataTypeEnum.compare_ast:
        # aggregate the compare_ast result files, to see how many files have a newly published version, that contains
        # dangerous function calls
        language2apis_interest = {
            LanguageEnum.python: ["eval", "exec", "base64.b64decode"],
            LanguageEnum.ruby: ["eval", "exec", "builtin_xstring", "Base64.urlsafe_decode64"],
            # base64 for javascript
            # https://developer.mozilla.org/en-US/docs/Web/API/WindowOrWorkerGlobalScope/atob
            # https://www.npmjs.com/package/js-base64
            # https://stackabuse.com/encoding-and-decoding-base64-strings-in-node-js/
            # https://www.w3schools.com/nodejs/met_buffer_from.asp
            LanguageEnum.javascript: ["eval", "child_process.exec", "child_process.execFileSync", "Base64.decode",
                                      "Buffer.from", "Buffer"],
            LanguageEnum.php: ["eval", "exec", "shell_exec", "base64_decode"],
            LanguageEnum.java: ["java.net.URLClassLoader.loadClass", "javax.script.ScriptEngine.eval",
                                "java.lang.System.loadLibrary", "java.lang.Runtime.exec",
                                "java.util.Base64.Decoder.decode"]
        }
        permissions_interest = ("OBFUSCATION", "CODE_GENERATION", "PROCESS_OPERATION", "NETWORK")

        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        apis_interest = language2apis_interest[language]
        packages = [row['package name'] for row in csv.DictReader(open(infile, 'r'))]
        filtered_results = {}
        # FIXME: add support for detail_mapping
        for pkg in packages:
            compare_fname = pm_proxy.get_compare_versions_fname(pkg_name=pkg)
            compare_file = join(outdir, compare_fname)
            if language == LanguageEnum.java:
                # FIXME: maven packages doesn't list release time in the metadata
                versions = pm_proxy.get_versions(pkg_name=pkg)
                # version2time = {v: datetime.date(2019, 1, 1) for v in versions}
                version2time = {v: datetime.datetime.strptime("2019-01-01", "%Y-%m-%d") for v in versions}
            else:
                version2time = {v: d for v, d in pm_proxy.get_versions(pkg_name=pkg, with_time=True)}
                # remove timezone info
                # ref: https://stackoverflow.com/questions/796008/cant-subtract-offset-naive-and-offset-aware-datetimes
                version2time = {v: d.replace(tzinfo=None) for v, d in version2time.items()}
            if not exists(compare_file):
                logging.error("compare versions result is not available for %s, ignoring", pkg)
                continue
            compare_out = json.load(open(compare_file, 'r'))
            if not ('all_apis' in compare_out and 'common_apis' in compare_out):
                logging.warning("skip %s because it doesn't have all_apis and common_apis in compare_out!", pkg)
                continue

            # filter by apis_interest, unique apis in some versions
            if enable_api_interest_filtering:
                if any((api_interest in compare_out['all_apis'] and api_interest not in compare_out['common_apis']) for api_interest in apis_interest):
                    # criteria:
                    # 1. problematic version within 2 years
                    # 2. more good versions than problematic versions
                    bad_version2time = {vs: dt for vs, dt in version2time.items() if vs in compare_out and any(
                        fapi in compare_out[vs]['uniq_apis'] for fapi in apis_interest)}

                    # rule 1
                    now = datetime.datetime.now()
                    two_years = datetime.timedelta(days=2*365)
                    if not any(now - dt < two_years for dt in bad_version2time.values()):
                        logging.warning("skip %s because it doesn't have any problematic version within two years", pkg)
                        continue

                    """
                    # 2. more old versions than new versions compared to problematic version
                    # rule 2
                    if language != LanguageEnum.java:
                        min_date = min(bad_version2time.values())
                        max_date = max(bad_version2time.values())
                        old_version2time = {vs: dt for vs, dt in version2time.items() if dt < min_date}
                        new_version2time = {vs: dt for vs, dt in version2time.items() if dt > max_date}
                        if len(old_version2time) <= len(new_version2time):
                            logging.warning("skip %s because it doesn't have more old versions than new versions", pkg)
                            continue

                    # 3. at most two problematic versions
                    # rule 3
                    if len(bad_version2time) > 2:
                        logging.warning("skip %s because it has more than two problematic versions", pkg)
                        continue

                    """
                    # rule 2
                    if len(bad_version2time) * 2 >= len(version2time):
                        logging.warning("skip %s because it doesn't have more good versions than problematic ones", pkg)
                        continue

                    # save package that satisfied the requirements
                    filtered_results[pkg] = compare_out

            # filter by permissions_interest
            if enable_permission_interest_filtering:
                if any((permission_present.endswith(permissions_interest) for permission_present in compare_out['all_permissions'])):
                    filtered_results[pkg] = compare_out

        logging.warning("from %d packages, found %d packages that seems problematic using heuristics!",
                        len(packages), len(filtered_results))
        json.dump(filtered_results, open(outfile, 'w'), indent=2)
    elif data_type in (DataTypeEnum.domain, DataTypeEnum.ip, DataTypeEnum.file, DataTypeEnum.process,
                       DataTypeEnum.sensitive):
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        counters = {}
        for row in csv.DictReader(open(infile, 'r')):
            pkg_name = row['package name']
            for sudo in (False, True):
                # Merge results from sudo and non-sudo
                dynamic_result = pm_proxy.get_dynamic_result(pkg_name=pkg_name, outdir=outdir, sudo=sudo)
                if dynamic_result:
                    if detail_mapping:
                        counters.setdefault('analyzed', set())
                        counters['analyzed'].add(pkg_name)
                    else:
                        # TODO: this number is problematic and inaccurate, because same package may be counted twice, for sudo and non-sudo.
                        counters.setdefault('analyzed', 0)
                        counters['analyzed'] += 1
                    if data_type in (DataTypeEnum.domain, DataTypeEnum.ip):
                        for net_act in dynamic_result.process_activity.network_activities:
                            if data_type == DataTypeEnum.domain and net_act.domain:
                                if detail_mapping:
                                    counters.setdefault(net_act.domain, set())
                                    counters[net_act.domain].add(pkg_name)
                                else:
                                    counters.setdefault(net_act.domain, 0)
                                    counters[net_act.domain] += 1
                            elif data_type == DataTypeEnum.ip and net_act.ip:
                                if detail_mapping:
                                    counters.setdefault(net_act.ip, set())
                                    counters[net_act.ip].add(pkg_name)
                                else:
                                    counters.setdefault(net_act.ip, 0)
                                    counters[net_act.ip] += 1
                    elif data_type == DataTypeEnum.file:
                        for file_act in dynamic_result.process_activity.file_activities:
                            file_key = '%s:%s' % (file_act.filepath, file_act.mode)
                            if detail_mapping:
                                counters.setdefault(file_key, set())
                                counters[file_key].add(pkg_name)
                            else:
                                counters.setdefault(file_key, 0)
                                counters[file_key] += 1
                    elif data_type == DataTypeEnum.process:
                        for proc_act in dynamic_result.process_activity.child_process_activities:
                            proc_key = '%s:%s' % (proc_act.user, proc_act.cmdline)
                            if detail_mapping:
                                counters.setdefault(proc_key, set())
                                counters[proc_key].add(pkg_name)
                            else:
                                counters.setdefault(proc_key, 0)
                                counters[proc_key] += 1
                    elif data_type == DataTypeEnum.sensitive:
                        for sen_act in dynamic_result.process_activity.sensitive_activities:
                            sen_key = '%s:%s:%s' % (sen_act.user, sen_act.syscall, sen_act.cmdline)
                            if detail_mapping:
                                counters.setdefault(sen_key, set())
                                counters[sen_key].add(pkg_name)
                            else:
                                counters.setdefault(sen_key, 0)
                                counters[sen_key] += 1
                    else:
                        raise Exception("Unexpected data type: %s" % data_type)
        if detail_mapping:
            # Dump both the stats and the detail mapping
            json.dump({k: list(v) for k, v in counters.items()}, open(outfile, 'w'), indent=2)
            json.dump({k: len(v) for k, v in counters.items()}, open(outfile + ".stats", 'w'), indent=2)
        else:
            json.dump(counters, open(outfile, 'w'), indent=2)
    elif data_type == DataTypeEnum.taint:
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        static_proxy = get_static_proxy_for_language(language=language)
        counters = {}
        # FIXME: add support for detail_mapping
        for row in csv.DictReader(open(infile, 'r')):
            pkg_name = row['package name']
            taint_result = static_proxy.get_taint_result(pm_proxy=pm_proxy, pkg_name=pkg_name, outdir=outdir,
                                                         cache_only=True)
            if taint_result:
                counters.setdefault('analyzed', set())
                counters['analyzed'].add(pkg_name)
                # TODO: do some logging for the static taint flows, to find anomolies.
                for taint_flow in taint_result.flows:
                    counters.setdefault(taint_flow.info.name, set())
                    counters[taint_flow.info.name].add(pkg_name)
        json.dump({k: list(v) for k, v in counters.items()}, open(outfile, "w"), indent=2)
        json.dump({k: len(v) for k, v in counters.items()}, open(outfile + ".stats", 'w'), indent=2)
    elif data_type == DataTypeEnum.author:
        raise Exception("Not implemented yet!")
    elif data_type == DataTypeEnum.permission:
        raise Exception("Not implemented yet!")
    elif data_type == DataTypeEnum.install_with_network:
        # map pkg to suspicious dynamic network behaviors
        domain2pkgs = json.load(open(join(dirname(infile), '%s_domain_mapping.json' % package_manager), 'r'))
        ip2pkgs = json.load(open(join(dirname(infile), '%s_ip_mapping.json' % package_manager), 'r'))
        pkg2network = {}
        for net_info2pkgs in (domain2pkgs, ip2pkgs):
            for net_info, pkgs in net_info2pkgs.items():
                # ignore too frequency ip/domains
                if net_info == 'analyzed':
                    continue
                if len(pkgs) > 200:
                    logging.warning("ignoring too frequent network activity %s", net_info)
                    continue
                for pkg in pkgs:
                    pkg2network.setdefault(pkg, [])
                    pkg2network[pkg].append(net_info)
        logging.warning("there are %d packages with unknown dynamic network behaviors", len(pkg2network))
        # FIXME: should we include static network behaviors, e.g. for maven and packagist?
        # get metadata of packages and compare them with
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        static_proxy = get_static_proxy_for_language(language=language)
        results = {}
        for row in csv.DictReader(open(infile, 'r')):
            pkg_name = row['package name']
            if pkg_name not in pkg2network:
                continue
            if language == LanguageEnum.python:
                # for PyPI, find packages that has unexpected IP/domain queries
                raise Exception("Not implemented yet!")
                pass
            elif language == LanguageEnum.javascript:
                # for NpmJS, find packages that has preinstall/install/postinstall hooks and unexpected IP/domain queries
                pkg_info = pm_proxy.get_metadata(pkg_name=pkg_name)
                install_scirpts = ('preinstall', 'install', 'postinstall')
                if 'scripts' in pkg_info and any(s in pkg_info['scripts'] for s in install_scirpts):
                    results.setdefault(pkg_name, {})
                    results[pkg_name]['network'] = pkg2network[pkg_name]
                    results[pkg_name]['scripts'] = pkg_info['scripts']
                    results[pkg_name]['astgen'] = static_proxy.get_astgen_result(pm_proxy=pm_proxy, pkg_name=pkg_name,
                                                                                 outdir=outdir, cache_only=True)
                    # FIXME: how about taint analysis results
            elif language == LanguageEnum.ruby:
                # for RubyGems, find packages that has unexpected IP/domain queries and with similar name to popular packages
                raise Exception("Not implemented yet!")
            elif language == LanguageEnum.php:
                # for Packagist, find packages that have
                raise Exception("Not implemented yet!")
            elif language == LanguageEnum.java:
                # for Maven,
                raise Exception("Not implemented yet!")
        logging.warning("dump %d packages with unknown dynamic network behaviors and install scripts", len(results))
        json.dump(results, open(outfile, 'w'), indent=2)
    elif data_type == DataTypeEnum.correlate_info_api_compare_ast:
        pkg2ver2compare_ast = json.load(open(infile, 'r'))
        if skip_file and exists(skip_file):
            type2list = json.load(open(skip_file, 'r'))
        else:
            type2list = None
        # get the release time for the specific version, and other versions
        # get the sensitive apis, filenames and argument details for manual analysis
        # filter sensitive versions by filenames iteratively.
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        static_proxy = get_static_proxy_for_language(language=language)
        pkg2ver2detail = {}
        for pkg, ver2compare_ast in pkg2ver2compare_ast.items():
            ver_time = sorted(pm_proxy.get_versions(pkg_name=pkg, max_num=-1, with_time=True), key=lambda (version, _): map(lambda digit: int(digit) if digit else 0, version.strip('v').split('.')), reverse=True)
            ver_set = {v for v, t in ver_time}
            for ver, compare_ast in ver2compare_ast.items():
                if ver not in ver_set:
                    continue
                if len(compare_ast['uniq_apis']) > 0 and len(compare_ast['uniq_permissions']) > 0:
                    # the api results
                    astgen_result = static_proxy.get_astgen_result(pm_proxy=pm_proxy, pkg_name=pkg, outdir=outdir, pkg_version=ver, cache_only=True)
                    api2filepath = {}
                    for api_result in astgen_result.pkgs[0].api_results:
                        api_full_name = api_result.full_name
                        if api_full_name not in compare_ast['uniq_apis']:
                           continue
                        filepath = api_result.range.start.file_info.file
                        if type2list and 'filepath' in type2list and any(fp in filepath for fp in type2list['filepath']):
                            continue
                        api2filepath.setdefault(api_full_name, [])
                        api2filepath[api_full_name].append((filepath, api_result.source))
                    if not len(api2filepath):
                        continue

                    # the time
                    pkg2ver2detail.setdefault(pkg, {})
                    pkg2ver2detail[pkg].setdefault(ver, {})
                    pkg2ver2detail[pkg][ver]['time'] = ['%s:%s' % (v, str(t)) for v, t in ver_time]
                    pkg2ver2detail[pkg][ver]['api2filepath'] = api2filepath
            if pkg not in pkg2ver2detail:
                continue
            for ver in pkg2ver2detail[pkg]:
                pkg2ver2detail[pkg][ver]['similar_versions'] = ','.join(pkg2ver2detail[pkg].keys())
            if privileged_recent_old_version:
                # assume that ver_time is alphabetically sorted (1) the old version should have privileged apis, (2) check an old version with recent time
                if len(pkg2ver2detail[pkg]) > 0 and any(ver_time[index-1][1] < ver_time[index][1] > ver_time[index+1][1] for index in range(1, len(ver_time)-1) if ver_time[index][0] in pkg2ver2detail[pkg]):
                    logging.warning("%s has privileged_recent_old_version!", pkg)
                else:
                    logging.debug("%s doesn't have privileged_recent_old_version, ignoring!", pkg)
                    del pkg2ver2detail[pkg]
        json.dump(pkg2ver2detail, open(outfile, 'w'), indent=2)
    else:
        raise Exception("Unhandled data type %s" % data_type)


def compute_content_hash(infile):
    # compute {path: hash} mapping for all files within infile, recursively decompress compressed files
    logging.warning("computing content hash for %s", infile)
    content_hashs = {}
    if get_file_with_meta(infile) is not None:
        content_path = decompress_file(infile)
        for root, dirs, files in os.walk(content_path):
            for fname in files:
                filepath = join(root, fname)
                rel_filepath = relpath(filepath, content_path)
                if get_file_with_meta(filepath) is not None:
                    # for zipped files, recursively inspect them
                    tmp_content_hashs = compute_content_hash(filepath)
                    content_hashs.update({'%s..%s' % (rel_filepath, tmp_filepath): tmp_filehash
                                          for tmp_filepath, tmp_filehash in tmp_content_hashs.items()})
                else:
                    # for normal files, simply compute their sha1 hash
                    content_hashs[rel_filepath] = exec_command('sha1sum', ['sha1sum', filepath], ret_stdout=True).split(' ')[0]
    return content_hashs


def compare_hash(infiles, cache_dirs, outfile, compare_hash_cache=None, inspect_content=False, inspect_api=False,
                 configpath=None):
    """
    Find the packages common among infiles and compare the hashes of same package versions, and output different ones.
    """
    sources = set()
    packages = set()
    source2pm_proxy = {}
    source2static_proxy = {}
    # initialize the packages to analyze
    for index, (infile, cache_dir) in enumerate(zip(infiles, cache_dirs)):
        temp_packages = set()
        for row in csv.DictReader(open(infile, 'r')):
            source = row['source']
            language = row['language']
            sources.add(source)
            if source not in source2pm_proxy:
                source2pm_proxy[source] = get_pm_proxy(pm=PackageManagerEnum(source), cache_dir=cache_dir, isolate_pkg_info=True)
                source2static_proxy[source] = get_static_proxy_for_language(language=LanguageEnum(language))
            temp_packages.add(row['package name'])
        if index == 0:
            packages.update(temp_packages)
        else:
            packages &= temp_packages
    logging.warning("loaded %d packages to analyze among sources %s", len(packages), sources)
    if compare_hash_cache is None:
        results = {}
        # check hash of each package version
        for package in packages:
            tmp_package_results = {}
            common_versions = set()
            for index, source in enumerate(sources):
                logging.warning("computing version hash for pkg %s from %s", package, source)
                pm_proxy = source2pm_proxy[source]
                version2hash = pm_proxy.get_version2hash(pkg_name=package)
                if index == 0:
                    common_versions.update(version2hash)
                else:
                    common_versions &= set(version2hash)
                for version, version_hash in version2hash.items():
                    if version_hash is not None:
                        tmp_package_results.setdefault(version, {})
                        tmp_package_results[version][source] = version_hash
            for version, version_hashs in tmp_package_results.items():
                if (version_hashs) > 1 and len(set(version_hashs.values())) > 1:
                    logging.error("package %s version %s has hash discrepancy: %s!", package, version, version_hashs)
                    results.setdefault(package, {})
                    results[package][version] = version_hashs
    else:
        results = json.load(open(compare_hash_cache, 'r'))
        logging.warning("loaded results for %d packages among sources %s", len(results), sources)
    # optionally inspect content of files to decide whether they are equal or not
    if inspect_content:
        filtered_results = {}
        for package in results:
            for version in results[package]:
                logging.warning("inspecting content for pkg %s ver %s", package, version)
                source2content_hash_dict = {}
                for source in sources:
                    temp_source_dir = tempfile.mkdtemp(prefix='get_%s_content_hash-' % source)
                    pm_proxy = source2pm_proxy[source]
                    download_path = pm_proxy.download(pkg_name=package, pkg_version=version, outdir=temp_source_dir)
                    source2content_hash_dict[source] = compute_content_hash(download_path)
                    shutil.rmtree(temp_source_dir)
                logging.debug("source to content hash mapping is: %s", source2content_hash_dict)
                hash_dicts = source2content_hash_dict.values()
                content_mismatch = False
                for index in range(len(hash_dicts) - 1):
                    if hash_dicts[index] != hash_dicts[index+1]:
                        content_mismatch = True
                        logging.warning("pkg %s ver %s has mismatch content between %s and %s",
                                        package, version, hash_dicts[index], hash_dicts[index+1])
                        break
                if content_mismatch:
                    filtered_results.setdefault(package, {})
                    filtered_results[package].setdefault(version)
                    filtered_results[package][version] = results[package][version]
        logging.warning("there are %d and %d packages before/after content inspection respectively!",
                        len(results), len(filtered_results))
        results = filtered_results
    # optionally inspect api/permission of files to decide whether they are equal or not
    if inspect_api:
        filtered_results = {}
        for package in results:
            for version in results[package]:
                logging.warning("inspecting permission for pkg %s ver %s", package, version)
                source2api_dict = {}
                for source in sources:
                    temp_source_dir = tempfile.mkdtemp(prefix='get_%s_api-' % source)
                    pm_proxy = source2pm_proxy[source]
                    static_proxy = source2static_proxy[source]
                    astgen_result = static_proxy.get_astgen_result(pm_proxy=pm_proxy, pkg_name=package,
                        outdir=temp_source_dir, configpath=configpath, pkg_version=version)
                    if not astgen_result:
                        logging.error("fail to compute astgen_result for pkg %s ver %s source %s", package, version, source)
                        continue
                    # iterate through astgen result to get permissions and apis
                    source2api_dict.setdefault(source, {})
                    for api_result in astgen_result.pkgs[0].api_results:
                        source2api_dict[source].setdefault(api_result.full_name, 0)
                        source2api_dict[source][api_result.full_name] += 1
                    logging.warning("found %d unique api usage for pkg %s ver %s source %s",
                                    len(source2api_dict[source]), package, version, source)
                    shutil.rmtree(temp_source_dir)
                api_dicts = source2api_dict.values()
                api_mismatch = False
                for index in range(len(api_dicts) - 1):
                    if api_dicts[index] != api_dicts[index+1]:
                        api_mismatch = True
                        logging.warning("pkg %s ver %s has mismatch api between %s and %s",
                                        package, version, api_dicts[index], api_dicts[index+1])
                        break
                if api_mismatch:
                    filtered_results.setdefault(package, {})
                    filtered_results[package].setdefault(version)
                    filtered_results[package][version] = results[package][version]
        logging.warning("there are %d and %d packages before/after content inspection respectively!",
                        len(results), len(filtered_results))
        results = filtered_results
    # dump the results to file
    if outfile:
        json.dump(results, open(outfile, 'w'), indent=2)


def compare_ast(infiles, package_names, language, outdir, cache_dir=None, configpath=None, outfile=None,
                cache_only=True):
    static_proxy = get_static_proxy_for_language(language=language)
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
    # process infiles
    astgen_of_infiles = {}
    if infiles and len(infiles) > 0:
        logging.warning("there are %d files to analyze!", len(infiles))
        for infile in infiles:
            logging.warning("analyzing file %s", infile)
            infile_astgenfile = join(outdir, basename(infile) + ".out")
            static_proxy.astgen(inpath=infile, outfile=infile_astgenfile, configpath=configpath)
            astgen_result = PkgAstResults()
            read_proto_from_file(astgen_result, infile_astgenfile, binary=False)
            astgen_of_infiles[infile] = astgen_result
    # process package names
    astgen_of_packages = {}
    if package_names and len(package_names) > 0:
        logging.warning("there are %d packages to analyze!", len(package_names))
        for package_name in package_names:
            package_versions = pm_proxy.get_versions(pkg_name=package_name)
            logging.warning("there are %d versions for package %s to analyze", len(package_versions), package_name)
            for package_version in package_versions:
                logging.warning("analyzing pkg %s ver %s", package_name, package_version)
                astgen_result = static_proxy.get_astgen_result(pm_proxy=pm_proxy, pkg_name=package_name, outdir=outdir,
                                                               configpath=configpath, pkg_version=package_version)
                if not astgen_result:
                    logging.error("failed to load astgen result for pkg %s ver %s, skipping!",
                                  package_name, package_version)
                    continue
                astgen_of_packages.setdefault(package_name, {})
                astgen_of_packages[package_name][package_version] = astgen_result

    # Check for common and unique permissions/APIs/dependencies for packages.
    api2permission = {}
    # load the mapping between api and permission
    configpb = AstLookupConfig()
    read_proto_from_file(proto=configpb, filename=configpath, binary=False)
    if configpb.func_only:
        raise Exception("func_only is not supported yet!")
    for api in configpb.apis:
        # Get top-level protobuf enum value name by number in python
        # https://stackoverflow.com/questions/11502113/how-to-get-top-level-protobuf-enum-value-name-by-number-in-python
        if api.functionality == ast_pb.SOURCE:
            api2permission[api.full_name] = ast_pb.SourceType.Name(api.source_type)
        elif api.functionality == ast_pb.SINK:
            api2permission[api.full_name] = ast_pb.SinkType.Name(api.sink_type)
        elif api.functionality == ast_pb.DANGER:
            api2permission[api.full_name] = ast_pb.SinkType.Name(api.sink_type)
        else:
            logging.debug("ignore api %s with functionality %s", api.full_name, api.functionality)
    logging.warning("loaded %d apis with permissions!", len(api2permission))
    astgen_summary = {}
    astgen_summary.setdefault("common_permissions", set())
    astgen_summary.setdefault("all_permissions", set())
    astgen_summary.setdefault("common_apis", set())
    astgen_summary.setdefault("all_apis", set())
    # summarize results of infiles
    for findex, (fpath, fresult) in enumerate(astgen_of_infiles.items()):
        astgen_summary.setdefault(fpath, {})
        # update permissions
        astgen_summary[fpath].setdefault("permissions", {})
        # update apis
        astgen_summary[fpath].setdefault("apis", {})
        for api_result in fresult.pkgs[0].api_results:
            if api_result.full_name in api2permission:
                api_permission = api2permission[api_result.full_name]
                astgen_summary[fpath]["permissions"].setdefault(api_permission, 0)
                astgen_summary[fpath]["permissions"][api_permission] += 1
                astgen_summary[fpath]["apis"].setdefault(api_result.full_name, 0)
                astgen_summary[fpath]["apis"][api_result.full_name] += 1
        if findex == 0:
            astgen_summary["common_permissions"].update(astgen_summary[fpath]["permissions"])
            astgen_summary["common_apis"].update(astgen_summary[fpath]["apis"])
        else:
            astgen_summary["common_permissions"] &= set(astgen_summary[fpath]["permissions"])
            astgen_summary["common_apis"] &= set(astgen_summary[fpath]["apis"])
        astgen_summary['all_permissions'].update(astgen_summary[fpath]["permissions"])
        astgen_summary['all_apis'].update(astgen_summary[fpath]["apis"])
    # cross infiles comparison
    for fpath in astgen_of_infiles:
        astgen_summary[fpath]["uniq_permissions"] = list(
            set(astgen_summary[fpath]["permissions"]) - astgen_summary["common_permissions"])
        astgen_summary[fpath]["uniq_apis"] = list(
            set(astgen_summary[fpath]["apis"]) - astgen_summary["common_apis"])

    # summarize results of package_names
    for pindex, package_name in enumerate(astgen_of_packages):
        compare_versions_fname = pm_proxy.get_compare_versions_fname(pkg_name=package_name)
        compare_versions_file = join(outdir, compare_versions_fname)
        astgen_summary.setdefault(package_name, {})
        astgen_summary[package_name].setdefault('common_permissions', set())
        astgen_summary[package_name].setdefault('all_permissions', set())
        astgen_summary[package_name].setdefault('common_apis', set())
        astgen_summary[package_name].setdefault('all_apis', set())
        astgen_summary[package_name].setdefault('common_deps', set())
        for vindex, (package_version, presult) in enumerate(astgen_of_packages[package_name].items()):
            astgen_summary[package_name].setdefault(package_version, {})
            # update permissions
            astgen_summary[package_name][package_version].setdefault("permissions", {})
            # update apis
            astgen_summary[package_name][package_version].setdefault("apis", {})
            logging.warning("processing pkg %s ver %s", package_name, package_version)
            for api_result in presult.pkgs[0].api_results:
                if api_result.full_name in api2permission:
                    api_permission = api2permission[api_result.full_name]
                    astgen_summary[package_name][package_version]["permissions"].setdefault(api_permission, 0)
                    astgen_summary[package_name][package_version]["permissions"][api_permission] += 1
                    astgen_summary[package_name][package_version]["apis"].setdefault(api_result.full_name, 0)
                    astgen_summary[package_name][package_version]["apis"][api_result.full_name] += 1
            # update common/all for current package
            if vindex == 0:
                astgen_summary[package_name]["common_permissions"].update(astgen_summary[package_name][package_version]["permissions"])
                astgen_summary[package_name]["common_apis"].update(astgen_summary[package_name][package_version]["apis"])
            else:
                astgen_summary[package_name]["common_permissions"] &= set(astgen_summary[package_name][package_version]["permissions"])
                astgen_summary[package_name]["common_apis"] &= set(astgen_summary[package_name][package_version]["apis"])
            astgen_summary[package_name]["all_permissions"].update(astgen_summary[package_name][package_version]["permissions"])
            astgen_summary[package_name]["all_apis"].update(astgen_summary[package_name][package_version]["apis"])
            # update common/all for all packages
            if pindex == 0 and vindex == 0:
                astgen_summary["common_permissions"].update(astgen_summary[package_name][package_version]["permissions"])
                astgen_summary["common_apis"].update(astgen_summary[package_name][package_version]["apis"])
            else:
                astgen_summary["common_permissions"] &= set(astgen_summary[package_name][package_version]["permissions"])
                astgen_summary["common_apis"] &= set(astgen_summary[package_name][package_version]["apis"])
            astgen_summary["all_permissions"].update(astgen_summary[package_name][package_version]["permissions"])
            astgen_summary["all_apis"].update(astgen_summary[package_name][package_version]["apis"])
            # update dependencies
            astgen_summary[package_name][package_version].setdefault("deps", {})
            package_deps = pm_proxy.get_dep(pkg_name=package_name, pkg_version=package_version, cache_only=cache_only)
            if package_deps:
                astgen_summary[package_name][package_version]["deps"].update(package_deps)
            if not astgen_summary[package_name]["common_deps"]:
                astgen_summary[package_name]["common_deps"].update(astgen_summary[package_name][package_version]["deps"])
            else:
                astgen_summary[package_name]["common_deps"] &= set(astgen_summary[package_name][package_version]["deps"])
        for package_version in astgen_of_packages[package_name]:
            pv_deps = set(astgen_summary[package_name][package_version]["deps"])
            astgen_summary[package_name][package_version]["uniq_deps"] = list(
                pv_deps - astgen_summary[package_name]["common_deps"])
        astgen_summary[package_name]["common_deps"] = list(astgen_summary[package_name]["common_deps"])
    # cross package comparison
    for package_name in astgen_of_packages:
        for package_version in astgen_of_packages[package_name]:
            astgen_summary[package_name]['common_permissions'] = list(astgen_summary[package_name]['common_permissions'])
            astgen_summary[package_name]['all_permissions'] = list(astgen_summary[package_name]['all_permissions'])
            astgen_summary[package_name]['common_apis'] = list(astgen_summary[package_name]['common_apis'])
            astgen_summary[package_name]['all_apis'] = list(astgen_summary[package_name]['all_apis'])
            astgen_summary[package_name][package_version]["uniq_permissions"] = list(
                set(astgen_summary[package_name][package_version]["permissions"]) - astgen_summary["common_permissions"])
            astgen_summary[package_name][package_version]["uniq_apis"] = list(
                set(astgen_summary[package_name][package_version]["apis"]) - astgen_summary["common_apis"])
        # cross package version comparison
        logging.warning("dumping %s output to %s", package_name, compare_versions_file)
        json.dump(astgen_summary[package_name], open(compare_versions_file, 'w'), indent=2)

    # the global common and all permission/apis
    astgen_summary['common_permissions'] = list(astgen_summary['common_permissions'])
    astgen_summary['all_permissions'] = list(astgen_summary['all_permissions'])
    astgen_summary['common_apis'] = list(astgen_summary['common_apis'])
    astgen_summary['all_apis'] = list(astgen_summary['all_apis'])
    if outfile:
        logging.warning("dumping output to %s", outfile)
        json.dump(astgen_summary, open(outfile, 'w'), indent=2)
    else:
        logging.warning("common permissions are %s, total permissions are %s, common apis %s, total apis: %s",
                        astgen_summary['common_permissions'], astgen_summary['all_permissions'],
                        astgen_summary['common_apis'], astgen_summary['all_apis'])


def filter_versions(versions_infile, compare_ast_infile, outfile):
    permissions_interest = ("OBFUSCATION", "CODE_GENERATION", "PROCESS_OPERATION", "NETWORK")
    versions_reader = csv.DictReader(open(versions_infile, 'r'))
    versions_writer = csv.DictWriter(open(outfile, 'w'), fieldnames=versions_reader.fieldnames)
    versions_writer.writeheader()
    compare_ast_results = json.load(open(compare_ast_infile, 'r'))
    logging.warning("loaded compare_ast results for %d packages", len(compare_ast_results))
    before_count = 0
    after_count = 0
    for row in versions_reader:
        before_count += 1
        pkg_name = row['package name']
        all_permissions = compare_ast_results.get(pkg_name, {}).get("all_permissions", [])
        if not any(permission.endswith(permissions_interest) for permission in all_permissions):
            continue
        # FIXME: do we want to filter on uniq_apis or uniq_permissions?
        versions_writer.writerow(row)
        after_count += 1
    logging.warning("there are %d package versions before filtering and %d after filtering", before_count, after_count)


def get_author(infile, outfile, language, cache_dir=None):
    pkg_reader = csv.DictReader(open(infile, 'r'))
    pkg_writer = csv.DictWriter(open(outfile, 'w'), fieldnames=pkg_reader.fieldnames + ['author'])
    pkg_writer.writeheader()
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
    pkg_count = 0
    pkg_author_count = 0
    for row in pkg_reader:
        pkg_name = row['package name']
        pkg_author = pm_proxy.get_author(pkg_name=pkg_name)
        pkg_count += 1
        if pkg_author:
            pkg_author_count += 1
        row['author'] = pkg_author
        pkg_writer.writerow(row)
    logging.warning("there are %d pkgs and %d of them have author information!", pkg_count, pkg_author_count)


def get_versions(infile, outfile, language, max_num=None, min_gap_days=None, with_time=False, cache_dir=None):
    pkg_reader = csv.DictReader(open(infile, 'r'))
    writer_fieldnames = pkg_reader.fieldnames + ['release time'] if with_time else pkg_reader.fieldnames
    pkg_writer = csv.DictWriter(open(outfile, 'w'), fieldnames=writer_fieldnames)
    pkg_writer.writeheader()
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
    pkg_count = 0
    pkg_ver_count = 0
    for row in pkg_reader:
        pkg_name = row['package name']
        if max_num or min_gap_days:
            pkg_versions = pm_proxy.get_versions(pkg_name=pkg_name, max_num=max_num, min_gap_days=min_gap_days, with_time=with_time)
        else:
            pkg_versions = pm_proxy.get_versions(pkg_name=pkg_name, with_time=with_time)
        pkg_count += 1
        pkg_ver_count += len(pkg_versions)
        for pkg_version in pkg_versions:
            try:
                if with_time:
                    row['version'], row['release time'] = pkg_version
                    row['release time'] = row['release time'].strftime('%Y-%m-%d')
                else:
                    row['version'] = pkg_version
                pkg_writer.writerow(row)
            except Exception as e:
                logging.error("error saving pkg %s version %s", pkg_name, pkg_version)
    logging.warning("there are %d pkgs and %d pkg versions!", pkg_count, pkg_ver_count)


def get_pkg_downloads(row, field=None):
    # use either overall or last_month
    if not row['downloads']:
        return None
    row_stats = literal_eval(row['downloads'])
    if not any(item in row_stats for item in ['overall', 'last_month']):
        logging.warning("there is no overall/last_month in downloads %s, pkg %s, language %s, ignoring",
                        row['downloads'], row['package name'], row['language'])
        return None
    # FIXME: for python, this is a mixed problem. some very popular packages doesn't have overall downloads, but just last_month downloads
    if field is None:
        if 'overall' in row_stats:
            return row_stats['overall']
        else:
            return row_stats['last_month']
    else:
        if field not in ('overall', 'last_month'):
            logging.error("unsupported field %s", field)
            return None
        if field == 'overall' and 'overall' in row_stats:
            return row_stats['overall']
        if field == 'last_month' and 'last_month' in row_stats:
            return row_stats['last_month']
    return None


def get_pkg_author_emails(row, language):
    # extract email from string
    # https://stackoverflow.com/questions/17681670/extract-email-sub-strings-from-large-document
    email_regex = re.compile(r'[\w\.-]+@[\w\.-]+')
    row_authors = literal_eval(row['author'])
    authors = set()
    if language == LanguageEnum.python:
        # 'author_email': u'fafhrd91@gmail.com', 'author': u'Nikolay Kim'
        # 'maintainer': u'Nikolay Kim <fafhrd91@gmail.com>, Andrew Svetlov <andrew.svetlov@gmail.com>'
        # 'author_email': u'Anna.Bridge@arm.com, Azim.Khan@arm.com'
        if row_authors.get('author_email', None):
            authors.update(re.findall(email_regex, row_authors['author_email']))
        if row_authors.get('maintainer', None):
            authors.update(re.findall(email_regex, row_authors['maintainer']))
    elif language == LanguageEnum.javascript:
        if row_authors.get('maintainers', None):
            for maintainer in row_authors['maintainers']:
                if isinstance(maintainer, dict):
                    logging.debug("unsupported author format: %s", maintainer)
                else:
                    authors.update(re.findall(email_regex, maintainer))
        if row_authors.get('npmUser', None):
            authors.update(re.findall(email_regex, row_authors['npmUser']))
        if row_authors.get('author', None):
            if isinstance(row_authors['author'], dict):
                logging.debug("unsupported author format: %s", row_authors['author'])
            else:
                authors.update(re.findall(email_regex, row_authors['author']))
    elif language == LanguageEnum.ruby:
        if row_authors.get('owners', None):
            for owner in row_authors['owners']:
                if 'email' in owner:
                    authors.add(owner['email'])
    elif language == LanguageEnum.php:
        # maintainers doesn't have emails
        # auithors are per version
        if row_authors.get('authors', None):
            for ver_id, ver_authors in row_authors['authors'].items():
                for ver_author in ver_authors:
                    if 'email' in ver_author:
                        authors.add(ver_author['email'])
    elif language == LanguageEnum.java:
        if row_authors.get('developers', None):
            for developer in row_authors['developers']:
                if 'email' in developer:
                    authors.add(developer['email'])
    else:
        raise Exception("Unhandled language: %s" % language)
    logging.info("pkg %s has %d authors", row['package name'], len(authors))
    return list(authors)


def select_pkg(infile, outfile, top_n_pkgs=0, threshold=0, field=None):
    # FIXME: maven and jcenter are different, they have don't have downloads. we can rank them by uses (dependents).
    reader = csv.DictReader(open(infile, 'r'))
    all_pkgs = []
    if field == 'use_count':
        rows = list(reader)
        dep_graph = load_dep_graph(language=LanguageEnum(rows[0]['language']))
        for row in rows:
            pkg_name = row['package name']
            pkg_uses = len(networkx.ancestors(dep_graph, pkg_name)) if pkg_name in dep_graph else 0
            all_pkgs.append((pkg_uses, row))
    else:
        if 'downloads' not in reader.fieldnames:
            logging.error("there is no downloads in %s and field is %s", reader.fieldnames, field)
            return
        for row in reader:
            # use either overall or last_month
            pkg_downloads = get_pkg_downloads(row=row, field=field)
            if pkg_downloads is None:
                continue
            all_pkgs.append((pkg_downloads, row))
    logging.warning("there are %d packages in total", len(all_pkgs))
    if top_n_pkgs > 0:
        all_pkgs = sorted(all_pkgs, key=lambda k: k[0], reverse=True)[:top_n_pkgs]
        logging.warning("there are %d packages after filtering by top_n_pkgs %d", len(all_pkgs), top_n_pkgs)
    if threshold > 0:
        all_pkgs = [k for k in all_pkgs if k[0] >= threshold]
        logging.warning("there are %d packages after filtering by threshold %d", len(all_pkgs), threshold)
    if len(all_pkgs) > 0:
        logging.warning("there are %d packages after filtering", len(all_pkgs))
        if field == 'use_count':
            writer = csv.DictWriter(open(outfile, 'w'), fieldnames=reader.fieldnames + ['use_count'])
            writer.writeheader()
            for use_count, row in all_pkgs:
                row['use_count'] = use_count
                writer.writerow(row)
        else:
            writer = csv.DictWriter(open(outfile, 'w'), fieldnames=reader.fieldnames)
            writer.writeheader()
            for _, row in all_pkgs:
                writer.writerow(row)


def select_pm(threshold, pm_stats_file='../data/modulecounts.csv'):
    reader = csv.DictReader(open(pm_stats_file, 'r'))
    latest_row = list(reader)[-1]
    selected = []
    for pm, count in latest_row.items():
        if pm == 'date':
            continue
        if not count:
            continue
        count = int(count)
        if count >= threshold:
            selected.append(pm)
            print("package manager %s has %d packages!" % (pm, count))
    print("the selected packages are %s" % selected)


def split_graph(infile, outdir, k_outdirs=None, num_outputs=None, seedfile=None, dagfile=None):
    """
    Load the dependency graph from infile and split it into num_outputs.
    """
    if infile.endswith('.tgz'):
        # there is only one file in the tarball archive
        tmp_graph = tarfile.open(infile, "r:gz")
        for member in tmp_graph.getmembers():
            graph = pickle.load(tmp_graph.extractfile(member))
        infile = splitext(infile)[0]
    elif infile.endswith('.pickle'):
        graph = pickle.load(open(infile, 'rb'))
    else:
        raise Exception("Unexpected format/extension of dep graph file: %s" % infile)

    graph_size = graph.number_of_nodes()
    infname = basename(infile)
    if num_outputs:
        assert num_outputs > 1
        subgraph_size = graph_size / (num_outputs - 1)
        logging.warning("spliting graph with %d nodes into %d outputs", graph_size, num_outputs)
        outbase, outext = splitext(infname)
        graph_nodes = list(graph.nodes())
        random.shuffle(graph_nodes)
        subgraphs = [graph_nodes[s: min(s+subgraph_size, graph_size)] for s in range(0, graph_size, subgraph_size)]
        for index, subgraph_nodes in enumerate(subgraphs):
            logging.warning("generating the %d subgraph, with %d nodes", index, len(subgraph_nodes))
            outfname = '%s_%d%s' % (outbase, index, outext)
            # if k_outdirs is specified, split the outfiles into k outdirs
            if k_outdirs:
                index_outdir = outdir.rstrip('/') + str(index / (len(subgraphs)/k_outdirs))
            else:
                index_outdir = outdir
            if not exists(index_outdir):
                os.makedirs(index_outdir)
            outfile = join(index_outdir, outfname)
            subgraph_node_set = set(subgraph_nodes)
            # Descendants
            # https://networkx.github.io/documentation/networkx-1.9.1/reference/generated/networkx.algorithms.dag.descendants.html
            for subgraph_node in subgraph_nodes:
                subgraph_node_set.update(networkx.descendants(graph, subgraph_node))

            # generate the subgraph and dump it to disk
            logging.warning("the complete subgraph has %d nodes", len(subgraph_node_set))
            subgraph = networkx.DiGraph(graph.subgraph(subgraph_node_set))
            pickle.dump(subgraph, open(outfile, 'wb'))

            # generate the dag file for subgraph if specified
            if dagfile and exists(dagfile):
                logging.warning("generating the dag file for %d subgraph", index)
                dag_content = open(dagfile, 'r').read()
                dagfname = basename(dagfile)
                dagbase, dagext = splitext(dagfname)
                outdagfname = '%s_%d%s' % (dagbase, index, dagext)
                outdagbase = '%s_%d' % (dagbase, index)
                out_dagfile = join(index_outdir, outdagfname)
                # FIXME: the indir/outdir is not handled here, and assumes that dagfile points to the dags folder.
                out_dag_content = dag_content.replace(dagbase, outdagbase).replace(infname, outfname)
                open(out_dagfile, 'w').write(out_dag_content)
    elif seedfile:
        seed_nodes = [row['package name'] for row in csv.DictReader(open(seedfile, 'r'))]
        logging.warning("generating subgraph, with %d seed nodes", len(seed_nodes))
        subgraph_node_set = set(seed_nodes)
        seed_fname = splitext(basename(seedfile))[0]
        outfname = seed_fname + ".pickle"
        # if k_outdirs is specified, split the seedfile into the first outdir
        if k_outdirs:
            index_outdir = outdir.rstrip('/') + "0"
        else:
            index_outdir = outdir
        if not exists(index_outdir):
            os.makedirs(index_outdir)
        outfile = join(index_outdir, outfname)
        for seed_node in seed_nodes:
            subgraph_node_set.update(networkx.descendants(graph, seed_node))

        # generate the subgraph and dump it to disk
        logging.warning("the complete subgraph has %d nodes, saving to %s", len(subgraph_node_set), outfile)
        subgraph = networkx.DiGraph(graph.subgraph(subgraph_node_set))
        pickle.dump(subgraph, open(outfile, 'wb'))

        # generate the dag file for subraph if specified
        if dagfile and exists(dagfile):
            logging.warning("generating the dag file for %s, graph in %s", seedfile, outfile)
            dag_content = open(dagfile, 'r').read()
            dagfname = basename(dagfile)
            dagbase, dagext = splitext(dagfname)
            outdagfname = "%s%s" % (seed_fname, dagext)
            out_dagfile = join(index_outdir, outdagfname)
            out_dag_content = dag_content.replace(dagbase, seed_fname).replace(infname, outfname)
            open(out_dagfile, 'w').write(out_dag_content)

    else:
        raise Exception("Invalid num_outputs %s and seedfile %s!" % (num_outputs, seedfile))


def aggregate_metadata(infile, cache_dir, language, record_version=False, cache_only=True):
    # NOTE: use get_metadata instead of get_dep, because the latter may install packages, while the former doesn't.
    expected_metadata_path = join(cache_dir, '%s.%s.info.json' % (basename(infile), language))
    if exists(expected_metadata_path):
        return json.load(open(expected_metadata_path, 'r'))
    else:
        pkg2metadata = {}
        pkg_reader = csv.DictReader(open(infile, 'r'))
        """
        isolate_pkg_info should be True to reuse metadata from dynamic analysis.
        Because dynamic analysis stores info into separate folder to avoid malicious packages deleting everything.
        """
        # FIXME: add multiprocess support here to speed up.
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        for row in pkg_reader:
            pkg_name = row['package name']
            if record_version:
                pkg_version = row['version']
                if not pkg_version:
                    raise Exception("record_version is True, but version is not specified in %s", row)
                pkg_info = pm_proxy.get_dep(pkg_name=pkg_name, pkg_version=pkg_version, cache_only=cache_only)
                pkg2metadata.setdefault(pkg_name, {})
                pkg2metadata[pkg_name].setdefault(pkg_version, pkg_info)
            else:
                # NOTE: pypi and maven metadata doesn't have dependencies, so we have to use get_dep.
                if language in (LanguageEnum.python, LanguageEnum.java):
                    pkg_info = pm_proxy.get_dep(pkg_name=pkg_name, cache_only=cache_only)
                else:
                    pkg_info = pm_proxy.get_metadata(pkg_name=pkg_name)
                pkg2metadata.setdefault(pkg_name, pkg_info)
        json.dump(pkg2metadata, open(expected_metadata_path, 'w'), indent=2)
        return pkg2metadata


def remove_cycle_edges_iteratively(graph, edge2score):
    def get_sccs(g):
        return [s for s in networkx.strongly_connected_component_subgraphs(g) if s.number_of_nodes() >= 2]

    # get the initial set of strong connected component subgraphs
    logging.warning("graph %d nodes, there are %d edges before removing", graph.number_of_nodes(),
                    graph.number_of_edges())
    all_sccs = get_sccs(g=graph)
    logging.warning("there are %d strongly connected component subgraphs!", len(all_sccs))
    edge_to_remove = []
    while True:
        if not all_sccs:
            break
        sub_graph = all_sccs.pop()
        pair_max_agony = None
        max_agony = -1
        for pair in sub_graph.edges():
            agony = edge2score.get(pair, 0)
            if agony >= max_agony:
                pair_max_agony = pair
                max_agony = agony
        edge_to_remove.append(pair_max_agony)
        sub_graph.remove_edges_from([pair_max_agony])
        sub_sub_graphs = get_sccs(sub_graph)
        if sub_sub_graphs:
            all_sccs.extend(sub_sub_graphs)
    logging.warning("graph %d nodes, there are %d edges to remove", graph.number_of_nodes(), len(edge_to_remove))
    graph.remove_edges_from(edge_to_remove)
    logging.warning("graph %d nodes, there are %d edges after removing", graph.number_of_nodes(), graph.number_of_edges())


def build_author(infiles, languages, outfile, top_n=200, top_authors=None):
    """
    author have three values: email, name, id
    package have three values: name, downloads, source

    interesting stats:
        how many authors publish in all five package managers?
        who are top authors in each package manager, regarding number of packages and number of downloads separately?
    """
    # FIXME: tempfix for _csv.Error: field larger than field limit (131072)
    csv.field_size_limit(sys.maxsize)
    author_pkg_graph = networkx.DiGraph()
    author2stats = {}
    common_author_set = set()
    for pm_index, (infile, language) in enumerate(zip(infiles, languages)):
        pkg_reader = csv.DictReader(open(infile, 'r'))
        pm_author_set = set()
        pm_dep_tree = load_dep_graph(language=language)
        for row in pkg_reader:
            pkg_name = row['package name']
            pkg_source = row['source']
            pkg_node_id = '%s:%s' % (pkg_source, pkg_name)
            pkg_downloads = get_pkg_downloads(row=row)
            if pkg_downloads is None:
                pkg_downloads = 0
            pkg_uses = len(networkx.ancestors(pm_dep_tree, pkg_name)) if pkg_name in pm_dep_tree else 0
            logging.debug("there are %d packages that uses %s", pkg_uses, pkg_name)
            author_pkg_graph.add_node(pkg_node_id, downloads=pkg_downloads, type='package')
            pkg_author_emails = get_pkg_author_emails(row=row, language=language)
            pm_author_set.update(pkg_author_emails)
            for pkg_author_email in pkg_author_emails:
                # author email/name/id
                author_node_id = pkg_author_email
                author_pkg_graph.add_node(author_node_id, type='author')
                author_pkg_graph.add_edge(author_node_id, pkg_node_id)
                # update author stats
                author2stats.setdefault(pkg_author_email, {})
                author2stats[pkg_author_email].setdefault('pkg_count', 0)
                author2stats[pkg_author_email].setdefault('download_count', 0)
                author2stats[pkg_author_email].setdefault('use_count', 0)
                author2stats[pkg_author_email].setdefault('%s_pkg_count' % language, 0)
                author2stats[pkg_author_email].setdefault('%s_download_count' % language, 0)
                author2stats[pkg_author_email].setdefault('%s_use_count' % language, 0)
                author2stats[pkg_author_email]['pkg_count'] += 1
                author2stats[pkg_author_email]['download_count'] += pkg_downloads
                author2stats[pkg_author_email]['use_count'] += pkg_uses
                author2stats[pkg_author_email]['%s_pkg_count' % language] += 1
                author2stats[pkg_author_email]['%s_download_count' % language] += pkg_downloads
                author2stats[pkg_author_email]['%s_use_count' % language] += pkg_uses
        logging.warning("language %s have %d unique author emails", language, len(pm_author_set))
        if pm_index == 0:
            common_author_set.update(pm_author_set)
        else:
            common_author_set &= pm_author_set
    logging.warning("there are %d unique author emails in total", len(author2stats))
    logging.warning("there are %d author emails (%s) that showed up in all languages",
                    len(common_author_set), common_author_set)
    top_authors_by_pkgs = sorted(author2stats.items(), key=lambda k: k[1]['pkg_count'], reverse=True)[:top_n]
    top_authors_by_downloads = sorted(author2stats.items(), key=lambda k: k[1]['download_count'], reverse=True)[:top_n]
    top_authors_by_uses = sorted(author2stats.items(), key=lambda k: k[1]['use_count'], reverse=True)[:top_n]
    top_authors_set = set(k[0] for k in top_authors_by_pkgs) | set(k[0] for k in top_authors_by_downloads) | set(k[0] for k in top_authors_by_uses)
    logging.warning("the top %s authors in pkg_count are %s", top_n, top_authors_by_pkgs)
    logging.warning("the top %s authors in download_count are %s", top_n, top_authors_by_downloads)
    logging.warning("the top %s authors in use_count are %s", top_n, top_authors_by_uses)
    logging.warning("there are top %d authors in total from the previous three lists", len(top_authors_set))
    if top_authors:
        json.dump({k:v for k, v in author2stats.items() if k in top_authors_set}, open(top_authors, 'w'), indent=2)
    pickle.dump(author_pkg_graph, open(outfile, 'wb'))


def build_dep(infile, outfile, cache_dir, language, record_version=False):
    """
    Build the dependency graph and traverse it in a specified order (algorithm).

    :param infile: list of packages to build dependency graph on.
    :param outfile: re-ordered list of packages in the visit order.
    :param cache_dir: root directory for metadata.
    :param language: language for package manager.
    """
    pkg2metadata = aggregate_metadata(infile=infile, cache_dir=cache_dir, language=language,
                                      record_version=record_version)
    dep_graph = networkx.DiGraph()
    for pkg_name, pkg_info in pkg2metadata.items():
        if record_version:
            # Relies on accurate version, and have to use get_dep.
            for pkg_version, pkg_version_info in pkg_info.items():
                if pkg_version_info is None:
                    continue
                # convert all strings to str. dep_pkg_ver can be unicode and it mess up stuff.
                # https://stackoverflow.com/questions/956867/how-to-get-string-objects-instead-of-unicode-from-json
                pkg_ver_id = str((str(pkg_name), str(pkg_version)))
                dep_pkg_ver_ids = [str((str(dep_pkg), str(dep_ver))) for dep_pkg, dep_ver in pkg_version_info.items()]

                # build the graph
                if pkg_ver_id not in dep_graph:
                    dep_graph.add_node(pkg_ver_id)
                for dep_pkg_ver_id in dep_pkg_ver_ids:
                    if dep_pkg_ver_id not in dep_graph:
                        dep_graph.add_node(dep_pkg_ver_id)
                    dep_graph.add_edges_from([(pkg_ver_id, dep_pkg_ver_id)])
        else:
            # Use get_metadata because no version is needed. Avoid heavy load get_dep.
            dep_pkgs = []
            if language == LanguageEnum.ruby:
                if pkg_info and 'dependencies' in pkg_info and 'runtime' in pkg_info['dependencies']:
                    for dep_pkg in pkg_info['dependencies']['runtime']:
                        dep_pkgs.append(dep_pkg['name'])
            elif language == LanguageEnum.python:
                if pkg_info:
                    dep_pkgs.extend(pkg_info.keys())
            elif language == LanguageEnum.javascript:
                if pkg_info and 'dependencies' in pkg_info:
                    try:
                        dep_pkgs.extend(pkg_info['dependencies'].keys())
                    except:
                        logging.error("error getting dependencies from pkg %s info %s", pkg_name, pkg_info['dependencies'])
            elif language == LanguageEnum.php:
                # FIXME: check the latest version of the package, or the stable version
                if pkg_info and 'package' in pkg_info and 'versions' in pkg_info['package']:
                    # some versions doesn't have time, ignore them
                    pkg_versions = filter(lambda k: 'time' in k, pkg_info['package']['versions'].values())
                    if not pkg_versions:
                        logging.error("%s has no versions (pkg_info: %s)", pkg_name, pkg_info)
                    else:
                        if 'dev-master' in pkg_versions:
                            latest_release = pkg_versions['dev-master']
                        else:
                            latest_release = sorted(pkg_versions, key=lambda k: dateutil.parser.parse(k['time']), reverse=True)[0]
                        dep_pkgs.extend(filter(lambda k: '/' in k, latest_release.get('require', {}).keys()))
            elif language == LanguageEnum.java:
                if pkg_info:
                    dep_pkgs.extend(pkg_info.keys())
            else:
                raise Exception("Unhandled language: %s" % language)

            # build the graph
            if pkg_name not in dep_graph:
                dep_graph.add_node(pkg_name)
            for dep_pkg_name in dep_pkgs:
                if dep_pkg_name not in dep_graph:
                    dep_graph.add_node(dep_pkg_name)
                dep_graph.add_edges_from([(pkg_name, dep_pkg_name)])

    # break the cycles in the dep graph to make them DAG (directed acyclic graph)
    if not networkx.is_directed_acyclic_graph(dep_graph):
        # algorithms to break cycles
        # https://cs.stackexchange.com/questions/90481/how-to-remove-cycles-from-a-directed-graph
        # https://github.com/zhenv5/breaking_cycles_in_noisy_hierarchies
        # remove self loops from graph
        self_loops = list(dep_graph.selfloop_edges())
        logging.warning("remove %d self_loops from graph!", len(self_loops))
        dep_graph.remove_edges_from(self_loops)
        # use pagerank algorithm to remove edges
        edge2score = networkx.pagerank(dep_graph, alpha=0.85)
        remove_cycle_edges_iteratively(graph=dep_graph, edge2score=edge2score)
    # save the graph to a file
    logging.warning("dumping dep graph with %d nodes and %d edges to %s",
                    dep_graph.number_of_nodes(), dep_graph.number_of_edges(), outfile)
    pickle.dump(dep_graph, open(outfile, 'wb'))


def interpret_dep(pkg_info_pb, dep_file, fmt, language):
    if fmt == 'json':
        if language == LanguageEnum.javascript:
            dep_pkgs = json.load(open(dep_file, 'r'))
            for dep_pkg_name, dep_pkg_info in dep_pkgs.items():
                dependency_pb = pkg_info_pb.dependencies.add()
                dependency_pb.package_name = dep_pkg_name
                dependency_pb.package_version = dep_pkg_info['version']
        elif language == LanguageEnum.ruby:
            dep_pkgs = json.load(open(dep_file, 'r'))
            for dep_pkg_name, dep_pkg_version in dep_pkgs.items():
                dependency_pb = pkg_info_pb.dependencies.add()
                dependency_pb.package_name = dep_pkg_name
                dependency_pb.package_version = dep_pkg_version
        elif language == LanguageEnum.php:
            raise Exception("Not implemented yet!")
        else:
            logging.error("cannot handle dependency for language %s fmt %s", language, fmt)
    elif fmt == 'requirement':
        if language == LanguageEnum.python:
            dep_pkgs = [dep_pkg.split('==')[:2] for dep_pkg in filter(bool, open(dep_file, 'r').read().split('\n'))]
            for dep_pkg_name, dep_pkg_version in dep_pkgs:
                dependency_pb = pkg_info_pb.dependencies.add()
                dependency_pb.package_name = dep_pkg_name
                dependency_pb.package_version = dep_pkg_version
        else:
            logging.error("cannot handle dependency for language %s fmt %s", language, fmt)
    else:
        raise Exception("Unhandled dependency format: %s" % fmt)


def interpret_metadata(pkg_info_pb, metadata_file, fmt, language):
    if fmt == 'json':
        # TODO: add development dependencies
        metadata = json.load(open(metadata_file, 'r'))
        if language == LanguageEnum.ruby:
            # ruby: 'name', 'version', 'authors', 'homepage_uri', 'licenses'
            pkg_info_pb.info.package_name = metadata['name']
            pkg_info_pb.info.package_version = metadata['version']
            pkg_info_pb.info.authors.extend(metadata['authors'].split(','))
            pkg_info_pb.info.homepage = metadata['homepage_uri']
            pkg_info_pb.info.license = ','.join(metadata['licenses'])
        elif language == LanguageEnum.python:
            # python: 'Name', 'License', 'Author', 'Home-page', 'Version', 'Author-email'
            pkg_info_pb.info.package_name = metadata['Name']
            pkg_info_pb.info.package_version = metadata['Version']
            pkg_info_pb.info.authors.append(metadata['Author'])
            pkg_info_pb.info.homepage = metadata['Home-page']
            pkg_info_pb.info.email = metadata['Author-email']
            pkg_info_pb.info.license = metadata['License']
        elif language == LanguageEnum.javascript:
            # javascript: 'name', 'license', 'author', 'version', 'homepage', 'repository' -> 'url'/'type', 'time'
            pkg_info_pb.info.package_name = metadata['name']
            pkg_info_pb.info.package_version = metadata['version']
            pkg_info_pb.info.authors.append(metadata['author'])
            pkg_info_pb.info.homepage = metadata['homepage']
            pkg_info_pb.info.license = metadata.get('license', "")
            pkg_info_pb.info.repository.url = metadata['repository']['url']
            pkg_info_pb.info.repository.type = metadata['repository']['type']
            for release_name, release_time in metadata['time'].items():
                pkg_release_info = pkg_info_pb.info.releases.add()
                pkg_release_info.name = release_name
                pkg_release_info.timestamp = release_time
        elif language == LanguageEnum.java:
            raise Exception("Not implemented yet!")
        elif language == LanguageEnum.php:
            raise Exception("Not implemented yet!")
        else:
            logging.error("cannot handle metadata for language %s fmt %s", language, fmt)
    else:
        raise Exception("Unhandled metadata format: %s" % fmt)


def get_pkg_info_pb(pkg_name, language, cache_dir=None, pkg_version=None):
    # FIXME: currently only fetches cached information
    pkg_info = PackageInfo()
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
    # build dependency tree from the dependency information
    dep_fname = pm_proxy.get_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=pm_proxy.dep_format)
    # TODO: deal with flatten dependencies here
    flatten_dep_fname = pm_proxy.get_flatten_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                       fmt=pm_proxy.dep_format)
    # summarize and get author information, release information from metadata
    metadata_fname = pm_proxy.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                 fmt=pm_proxy.metadata_format)
    if cache_dir and exists(cache_dir):
        dep_fpath = join(cache_dir, dep_fname)
        if not exists(dep_fpath):
            logging.error("cannot find dep for pkg_name=%s, pkg_version=%s", pkg_name, pkg_version)
        else:
            interpret_dep(pkg_info_pb=pkg_info, dep_file=dep_fpath, fmt=pm_proxy.dep_format, language=language)
        metadata_fpath = join(cache_dir, metadata_fname)
        if not exists(metadata_fpath):
            logging.error("cannot find metadata for pkg_name=%s, pkg_version=%s", pkg_name, pkg_version)
        else:
            interpret_metadata(pkg_info_pb=pkg_info, metadata_file=metadata_fpath, fmt=pm_proxy.metadata_format,
                               language=language)
    return pkg_info


def interpret_strace(dynamic_pb, trace_file, outdir, sudo=False):
    # TODO: find a tool to parse the strace logs
    raise Exception("not implemented yet!")


def get_falco_alerts(trace_file, sysdig_path="../sysdig", progress_path="/tmp/interpret_trace.progress"):
    temp_dir = tempfile.mkdtemp(prefix="falco-")
    logging.warning("collecting falco alerts from %s at %s", trace_file, temp_dir)
    # the falco config and fules
    for fname in ['falco_rules.local.yaml', 'falco_rules.yaml', 'falco.yaml']:
        shutil.copyfile(join(sysdig_path, fname), join(temp_dir, fname))
    # the .env file, with customized DATADIR
    temp_data_dir = 'DATADIR=%s' % dirname(trace_file)
    open(join(temp_dir, '.env'), 'w').write(
        re.sub(re.compile('DATADIR=.*'), temp_data_dir,
               open(join(sysdig_path, '.env')).read()))
    temp_falco_container_name = 'container_name: %s' % basename(temp_dir)
    temp_falco_container_command = 'command: falco -A -c /etc/falco/falco.yaml -e %s' % trace_file
    # the docker-compose-falco.yml file, with customized container_name and command
    open(join(temp_dir, 'docker-compose-falco.yml'), 'w').write(
        re.sub(re.compile('container_name:.*'), temp_falco_container_name,
               re.sub(re.compile('command:.*'), temp_falco_container_command,
                      open(join(sysdig_path, 'docker-compose-falco.yml')).read())))
    falco_up_cmd = ['docker-compose', '-f', 'docker-compose-falco.yml', 'up']
    exec_command('falco alert up', falco_up_cmd, cwd=temp_dir)
    # the events.txt is the expected output file
    temp_falco_events = join(temp_dir, 'events.txt')
    logging.warning("parsing falco alerts stored at %s", temp_falco_events)
    falco_alerts = []
    if not exists(temp_falco_events):
        logging.warning("no events file was generated for %s", trace_file)
    else:
        for falco_alert in open(temp_falco_events, 'r'):
            try:
                falco_alerts.append(json.loads(falco_alert))
            except Exception as e:
                logging.error("failed parsing alert line %s: %s", falco_alert, str(e))
    # cleanup stuff
    falco_down_cmd = ['docker-compose', '-f', 'docker-compose-falco.yml', 'down']
    exec_command('falco alert down', falco_down_cmd, cwd=temp_dir)
    shutil.rmtree(temp_dir)
    # track progress
    with open(progress_path, 'a') as progress_f:
        progress_f.write(trace_file + '\n')
    return falco_alerts


def is_valid_hostname(hostname):
    if not hostname:
        return False
    # reference: https://stackoverflow.com/questions/2532053/validate-a-hostname-string
    if len(hostname) > 255:
        return False
    if hostname[-1] == ".":
        hostname = hostname[:-1] # strip exactly one dot from the right, if present
    # must have a dot in the name
    if '.' not in hostname:
        return False
    allowed = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(allowed.match(x) for x in hostname.split("."))


def get_pkg_data2falco_alerts(falco_alerts):
    pkg_data2falco_alerts = {}
    for falco_alert in falco_alerts:
        falco_output_fields = falco_alert.get('output_fields', {})
        container_name = falco_output_fields.get('container.name', None)
        if not container_name or container_name == 'host':
            logging.debug("ignoring falco alert %s because its container name is %s", falco_alert, container_name)
            continue
        sanitized_pkg_name, pkg_version, pkg_job = container_name.rsplit('..', 2)
        if pkg_version == 'None':
            pkg_version = None
        pkg_sudo = pkg_job.endswith('sudo')
        pkg_data = (sanitized_pkg_name, pkg_version, pkg_sudo)
        if not hasattr(FalcoRuleEnum, falco_alert['rule']):
            logging.info("ignoring falco rule: %s", falco_alert['rule'])
            continue
        pkg_data2falco_alerts.setdefault(pkg_data, {})
        falco_rule = FalcoRuleEnum(falco_alert['rule'])
        if falco_rule in (FalcoRuleEnum.outgoing_domain, FalcoRuleEnum.incoming_domain):
            pkg_data2falco_alerts[pkg_data].setdefault(falco_rule, set())
            domain_data = falco_alert['output_fields']['evt.arg.data']
            domain_candidates = [dc.strip('.') for dc in domain_data.split('..')]
            domains = filter(is_valid_hostname, domain_candidates)
            if len(domains) == 0:
                continue
            pkg_data2falco_alerts[pkg_data][falco_rule].add(domains[0])
        elif falco_rule in (FalcoRuleEnum.outgoing_ip,):
            pkg_data2falco_alerts[pkg_data].setdefault(falco_rule, set())
            if falco_alert['output_fields']['fd.sip'] is None:
                continue
            pkg_data2falco_alerts[pkg_data][falco_rule].add(falco_alert['output_fields']['fd.sip'])
        elif falco_rule in (FalcoRuleEnum.incoming_ip,):
            pkg_data2falco_alerts[pkg_data].setdefault(falco_rule, set())
            if falco_alert['output_fields']['fd.cip'] is None:
                continue
            pkg_data2falco_alerts[pkg_data][falco_rule].add(falco_alert['output_fields']['fd.cip'])
        elif falco_rule in (FalcoRuleEnum.write_file, FalcoRuleEnum.read_file,
                            FalcoRuleEnum.stat_file):
            pkg_data2falco_alerts[pkg_data].setdefault(falco_rule, set())
            if falco_alert['output_fields']['fd.name'] is None:
                continue
            pkg_data2falco_alerts[pkg_data][falco_rule].add(falco_alert['output_fields']['fd.name'])
        elif falco_rule in (FalcoRuleEnum.spawn_process,):
            pkg_data2falco_alerts[pkg_data].setdefault(falco_rule, set())
            if falco_alert['output_fields']['user.name'] is None or falco_alert['output_fields']['proc.name'] is None or falco_alert['output_fields']['proc.cmdline'] is None:
                continue
            op_tuple = (falco_alert['output_fields']['user.name'], falco_alert['output_fields']['proc.name'], falco_alert['output_fields']['proc.cmdline'])
            pkg_data2falco_alerts[pkg_data][falco_rule].add(op_tuple)
        elif falco_rule in (FalcoRuleEnum.sensitive_operation,):
            pkg_data2falco_alerts[pkg_data].setdefault(falco_rule, set())
            # setuid/setgid: user.name
            if falco_alert['output_fields']['user.name'] is None or falco_alert['output_fields']['proc.cmdline'] is None:
                continue
            # track the syscall if specified
            if 'evt.type' in falco_alert['output_fields']:
                op_tuple = (falco_alert['output_fields']['user.name'], falco_alert['output_fields']['proc.cmdline'], falco_alert['output_fields']['evt.type'])
            else:
                op_tuple = (falco_alert['output_fields']['user.name'], falco_alert['output_fields']['proc.cmdline'], None)
            pkg_data2falco_alerts[pkg_data][falco_rule].add(op_tuple)
        else:
            logging.info("ignoring falco rule: %s", falco_rule)
            continue
    return pkg_data2falco_alerts


def get_dynamic_pb(pkg_sudo, pkg_alerts):
    dynamic_pb = DynamicAnalysis()
    dynamic_pb.exe_user = 'sudo' if pkg_sudo else 'maloss'
    dynamic_pb.process_activity.main_process = True
    for falco_rule, falco_values in pkg_alerts.items():
        logging.warning("collected %d unique %s", len(falco_values), falco_rule)
        if falco_rule in (FalcoRuleEnum.incoming_domain, FalcoRuleEnum.outgoing_domain, FalcoRuleEnum.incoming_ip,
                          FalcoRuleEnum.outgoing_ip):
            for falco_value in falco_values:
                network_act = dynamic_pb.process_activity.network_activities.add()
                if str(falco_rule).endswith('domain'):
                    network_act.domain = falco_value
                elif str(falco_rule).endswith('ip'):
                    # TODO: add protocol
                    network_act.ip = falco_value
                else:
                    logging.error("unhandled falco rule %s value %s", falco_rule, falco_value)
        elif falco_rule in (FalcoRuleEnum.write_file, FalcoRuleEnum.read_file, FalcoRuleEnum.stat_file):
            for falco_value in falco_values:
                file_act = dynamic_pb.process_activity.file_activities.add()
                file_act.filepath = falco_value
                if falco_rule == FalcoRuleEnum.write_file:
                    file_act.mode = 'w'
                elif falco_rule == FalcoRuleEnum.read_file:
                    file_act.mode = 'r'
                elif falco_rule == FalcoRuleEnum.stat_file:
                    file_act.mode = 'e'
                else:
                    logging.error("unhandled falco rule %s value %s", falco_rule, falco_value)
        elif falco_rule in (FalcoRuleEnum.spawn_process,):
            for user_name, proc_name, proc_cmdline in falco_values:
                proc_act = dynamic_pb.process_activity.child_process_activities.add()
                proc_act.user = user_name
                proc_act.exe = proc_name
                proc_act.cmdline = proc_cmdline
        elif falco_rule in (FalcoRuleEnum.sensitive_operation,):
            for user_name, proc_cmdline, evt_type in falco_values:
                sensitive_act = dynamic_pb.process_activity.sensitive_activities.add()
                # user, commandline
                sensitive_act.user = user_name
                sensitive_act.cmdline = proc_cmdline
                sensitive_act.syscall = evt_type
        else:
            logging.warning("unhandled falco rule: %s", falco_rule)
    return dynamic_pb


def save_dynamic_pb(dynamic_pb, dynamic_fpath, binary=False):
    logging.warning("saving %d network %d file %d process %d sensitive activies to %s",
                    len(dynamic_pb.process_activity.network_activities),
                    len(dynamic_pb.process_activity.file_activities),
                    len(dynamic_pb.process_activity.child_process_activities),
                    len(dynamic_pb.process_activity.sensitive_activities), dynamic_fpath)
    if exists(dynamic_fpath):
        old_dynamic_pb = DynamicAnalysis()
        read_proto_from_file(old_dynamic_pb, dynamic_fpath, binary=binary)
        # NOTE: reference get_dynamic_pb to see if there are other fields that need to be copied.
        old_dynamic_pb.process_activity.network_activities.extend(dynamic_pb.process_activity.network_activities)
        old_dynamic_pb.process_activity.file_activities.extend(dynamic_pb.process_activity.file_activities)
        old_dynamic_pb.process_activity.child_process_activities.extend(dynamic_pb.process_activity.child_process_activities)
        old_dynamic_pb.process_activity.sensitive_activities.extend(dynamic_pb.process_activity.sensitive_activities)
        dynamic_pb = old_dynamic_pb
    write_proto_to_file(dynamic_pb, dynamic_fpath, binary=binary)
    logging.warning("saved %d network %d file %d process %d sensitive activies to %s",
                    len(dynamic_pb.process_activity.network_activities),
                    len(dynamic_pb.process_activity.file_activities),
                    len(dynamic_pb.process_activity.child_process_activities),
                    len(dynamic_pb.process_activity.sensitive_activities), dynamic_fpath)


def interpret_sysdig(trace_file, language, outdir, cache_dir=None, binary=False):
    logging.warning("invoking falco on %s to get triggered alerts!", trace_file)
    falco_alerts = get_falco_alerts(trace_file=trace_file)

    logging.warning("parsing %d triggered alerts, map each package to corresponding events", len(falco_alerts))
    pkg_data2falco_alerts = get_pkg_data2falco_alerts(falco_alerts=falco_alerts)

    logging.warning("iterate through %d package data and save their events", len(pkg_data2falco_alerts))
    pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
    # FIXME: the saving step could introduce race conditions. currently ignoring them!
    for pkg_data, pkg_alerts in pkg_data2falco_alerts.items():
        # prepare dynamic pb
        sanitized_pkg_name, pkg_version, pkg_sudo = pkg_data
        dynamic_pb = get_dynamic_pb(pkg_sudo=pkg_sudo, pkg_alerts=pkg_alerts)
        # save to file or merge with existing file
        dynamic_fpath = join(outdir, pm_proxy.get_dynamic_fname(pkg_name=sanitized_pkg_name, pkg_version=pkg_version,
                                                                sudo=pkg_sudo, sanitized=True))
        save_dynamic_pb(dynamic_pb=dynamic_pb, dynamic_fpath=dynamic_fpath, binary=binary)


def interpret_trace(language, outdir, cache_dir=None, trace_type=None, trace_dir=None, pkg_name=None, pkg_version=None,
                    binary=False, processes=1, skip_file=None):
    """
    FIXME: currently only supports sysdig traces. look at existing strace-analyzer tools, for strace parsing

    Add the functionality to check for malicious behaviors in strace logs, in particular
    1. Stealer
    1.1. Find potential attempts to access sensitive files or folders
    1.2. Identify the IPs or domains that a package talks to during installation
    2. Backdoor
    2.1. Identify the packages that writes outside its own folder (/tmp/, /.../dist-packages/xxx/)
    2.2. Find processes/daemons that the packages start during installation
    3. Sabotage
    3.1. Find potential attempts to remove files outside its own folder
    3.2. Find potential attempts to encrypt files outside its own folder

    Unwanted software:
    1. Adware
    1.1. Identify the IPs or domains that a package talks to during installation
    2. POC packages
    2.1. Proof of concept that some malicious activity can be done.
    """
    if skip_file and exists(skip_file):
        skip_traces = set(filter(bool, open(skip_file, 'r').read().split('\n')))
        logging.warning("there are %d traces to skip!", len(skip_traces))
    else:
        skip_traces = set()
    # initialize data and objects
    if trace_type == TraceTypeEnum.strace:
        # FIXME: this is not implemented yet
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=cache_dir, isolate_pkg_info=True)
        # analyze trace logs
        if trace_dir and exists(trace_dir):
            #  analyze the non-sudo and sudo trace
            for sudo in (False, True):
                trace_fpath = join(trace_dir, pm_proxy.get_trace_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                                       sudo=sudo))
                dynamic_pb = DynamicAnalysis()
                if not exists(trace_fpath):
                    logging.error("cannot find trace for pkg_name=%s, pkg_version=%s, sudo=%s", pkg_name, pkg_version, sudo)
                else:
                    interpret_strace(dynamic_pb=dynamic_pb, trace_file=trace_fpath, outdir=outdir, sudo=sudo)
    elif trace_type == TraceTypeEnum.sysdig:
        # FIXME: maybe add progress tracking to skip processed trace files, in case of interruption
        sysdig_traces = [join(trace_dir, trace_fname) for trace_fname in os.listdir(trace_dir)]
        logging.warning("processing %d sysdig traces!", len(sysdig_traces))
        if skip_traces:
            sysdig_traces = list(set(sysdig_traces) - skip_traces)
            logging.warning("processing %d sysdig traces after filtering by %d skip traces!", len(sysdig_traces), len(skip_traces))
        if processes > 1:
            pool = Pool(processes=processes)
            partial_interpret_sysdig = partial(interpret_sysdig, language=language, outdir=outdir, cache_dir=cache_dir,
                                               binary=binary)
            pool.map(partial_interpret_sysdig, sysdig_traces)
        else:
            for sysdig_trace in sysdig_traces:
                interpret_sysdig(trace_file=sysdig_trace, language=language, outdir=outdir, cache_dir=cache_dir,
                                 binary=binary)
    else:
        raise Exception("Unhandled tracing type: %s!" % trace_type)


def grep_worker(pkg_name, outfile, pattern, language):
    try:
        # download the package
        tempdir = tempfile.mkdtemp(prefix="grep-")
        pm_proxy = get_pm_proxy_for_language(language=language, cache_dir=None, isolate_pkg_info=None)
        pm_proxy.download(pkg_name=pkg_name, outdir=tempdir)
        tempdir_files = os.listdir(tempdir)
        if len(tempdir_files) == 0:
            logging.error("fail to download pkg %s", pkg_name)
            return
        else:
            pkg_file = join(tempdir, tempdir_files[0])
        # decompress the package
        analyze_path, is_decompress_path, _, _, _ = StaticAnalyzer._sanitize_astgen_args(
            inpath=pkg_file, outfile=pkg_file, root=None, configpath=None, language=language)
        # grep for specified patterns in the package
        output = exec_command('grep pkg', ['grep', '-r', pattern, analyze_path], ret_stdout=True)
        if output:
            open(outfile, 'a').write('%s,%s\n' % (pkg_name, output))
        # cleanup the residues
        StaticAnalyzer._cleanup_astgen(analyze_path=analyze_path, is_decompress_path=is_decompress_path)
        shutil.rmtree(tempdir)
    except Exception as e:
        logging.error("fail to grep through pkg %s, error %s", pkg_name, str(e))


def grep(infile, outfile, pattern, language, processes=1):
    pkg_names = [row['package name'] for row in csv.DictReader(open(infile, 'r'))]
    grep_worker_partial = partial(grep_worker, outfile=outfile, pattern=pattern, language=language)
    pool = Pool(processes=processes)
    pool.map(grep_worker_partial, pkg_names)


def cross_check(base_behavior_file, base_package_manager):
    # TODO: manually cross check malicious domain/ip/file activities
    # search for malware with the same name across package managers
    logging.warning("the base behavior file is %s, and the base package manager is %s",
                    base_behavior_file, base_package_manager)
    pass


def analysis_wrapper(pkg_name, ignore_dep, outfile, job, language, configpath):
    tmpdir = tempfile.mkdtemp()
    open(outfile, 'a').write("processing job %s pkg %s language %s ignore_dep %s at %s\n" %
                             (job, pkg_name, language, ignore_dep, tmpdir))
    start_time = time.time()
    if job == 'astfilter':
        astfilter(pkg_name=pkg_name, language=language, outdir=tmpdir, cache_dir=tmpdir, configpath=configpath,
                  ignore_dep=ignore_dep)
    elif job == 'taint':
        taint(pkg_name=pkg_name, language=language, outdir=tmpdir, cache_dir=tmpdir, configpath=configpath,
              ignore_dep=ignore_dep)
    else:
        raise Exception("unknown job %s" % job)
    shutil.rmtree(tmpdir)
    open(outfile, 'a').write("processing job %s for pkg %s language %s ignore_dep %s took: %s\n" %
                             (job, pkg_name, language, ignore_dep, time.time() - start_time))


def speedup(infile, outfile, number, language, configpath='../config/astgen_python_smt.config'):
    packages = [row['package name'] for row in csv.DictReader(open(infile, 'r'))]
    logging.warning("loaded %d packages from %s", len(packages), infile)
    random.shuffle(packages)
    selected_packages = packages[:number]
    logging.warning("randomly selected %d from %d packages", len(selected_packages), len(packages))

    # run api analysis without summaries (estimate by ignoring the dependencies)
    astfilter_nosummary = partial(analysis_wrapper, ignore_dep=True, outfile=outfile, job='astfilter',
                                  language=language, configpath=configpath)
    pool = Pool(processes=cpu_count())
    pool.map(astfilter_nosummary, selected_packages)
    pool.close()
    pool.join()
    # run api analysis with summaries
    astfilter_summary = partial(analysis_wrapper, ignore_dep=False, outfile=outfile, job='astfilter',
                                language=language, configpath=configpath)
    pool = Pool(processes=cpu_count())
    pool.map(astfilter_summary, selected_packages)
    pool.close()
    pool.join()
    # run taint analysis without summaries (estimate by ignoring the dependencies)
    taint_nosummary = partial(analysis_wrapper, ignore_dep=True, outfile=outfile, job='taint',
                              language=language, configpath=configpath)
    pool = Pool(processes=cpu_count())
    pool.map(taint_nosummary, selected_packages)
    pool.close()
    pool.join()
    # run taint analysis with summaries
    taint_summary = partial(analysis_wrapper, ignore_dep=False, outfile=outfile, job='taint',
                            language=language, configpath=configpath)
    pool = Pool(processes=cpu_count())
    pool.map(taint_summary, selected_packages)
    pool.close()
    pool.join()

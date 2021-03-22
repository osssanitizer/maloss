import json
import os
import re
import logging
import pickle
import datetime
import networkx
import itertools
from os.path import splitext, exists, join, basename
from util.job_util import read_proto_from_file
from proto.python.behavior_pb2 import DynamicAnalysis


class PackageManagerProxy(object):
    # TODO: add install failure handlers, i.e. what to do if a package is removed or fail to install
    # TODO: add get metadata failure handlers, i.e. what to do if a package is removed or info retrieval fails
    # TODO: add get dependency failure handlers, i.e. what to do if a package is removed or dep retrieval fails

    def __init__(self):
        # do nothing, but initialize placeholders for instance variables
        self.registry = None
        self.cache_dir = None
        self.isolate_pkg_info = False
        self.metadata_format = None
        self.dep_format = None

    @staticmethod
    def get_dir_for_pkgname(pkg_name, cache_dir):
        dir_for_pkgname = join(cache_dir, PackageManagerProxy.get_sanitized_pkgname(pkg_name))
        if not exists(dir_for_pkgname):
            os.makedirs(dir_for_pkgname)
        return dir_for_pkgname

    def get_pkg_info_dir(self, pkg_name):
        if self.isolate_pkg_info:
            return self.get_dir_for_pkgname(pkg_name=pkg_name, cache_dir=self.cache_dir)
        else:
            return self.cache_dir

    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        # download package to specified outdir. by default, download the source package without dependencies
        pass

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        # install package (with sudo) in install_dir and optionally store the trace to outdir
        pass

    def install_file(self, infile, trace=False, trace_string_size=1024, sudo=False, install_dir=None, outdir=None):
        # install package file (with sudo) in install_dir and optionally store the trace to outdir
        pass

    def uninstall(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                  outdir=None):
        # uninstall package (with sudo) in install_dir and optionally store the trace to outdir
        pass

    def get_metadata(self, pkg_name, pkg_version=None):
        # load the metadata information for a package or get and cache it in cache_dir
        pass

    def get_metadata_file(self, pkg_name, pkg_version=None):
        # get path to the metadata for a package or get and cache it and return path
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
            return join(pkg_info_dir, self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                              fmt=self.metadata_format))
        else:
            logging.error("get_metadata_file: cache dir is not specified!")
            return None

    def get_versions(self, pkg_name, max_num=15, min_gap_days=30, with_time=False):
        # read the metadata and get (major) versions of the specified package
        pass

    def get_author(self, pkg_name):
        # read the metadata and get author name and email of the specified package
        pass

    def get_version_hash(self, pkg_name, pkg_version, algorithm='sha1'):
        # get the hash of the package version
        pass

    def get_version2hash(self, pkg_name, max_num=15, min_gap_days=30, algorithm='sha1'):
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            version2hash_fname = self.get_version2hash_fname(pkg_name=pkg_name)
            version2hash_file = join(pkg_info_dir, version2hash_fname)
            if exists(version2hash_file):
                logging.warning("get_version2hash: using cached version2hash_file %s!", version2hash_file)
                try:
                    return json.load(open(version2hash_file, 'r'))
                except:
                    logging.debug("fail to load version2hash_file: %s, regenerating!", version2hash_file)
        versions = self.get_versions(pkg_name=pkg_name, max_num=max_num, min_gap_days=min_gap_days)
        version2hash = {}
        if versions is not None:
            for version in versions:
                version_hash = self.get_version_hash(pkg_name=pkg_name, pkg_version=version, algorithm=algorithm)
                version2hash[version] = version_hash
        # optionally cache version2hash
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            version2hash_fname = self.get_version2hash_fname(pkg_name=pkg_name)
            version2hash_file = join(pkg_info_dir, version2hash_fname)
            json.dump(version2hash, open(version2hash_file, 'w'), indent=2)
        return version2hash

    def bfs_all_deps(self, dep_func_name, pkg_name, pkg_version=None, temp_env=None):
        # use breadth first search to find all/flattened dependencies
        # https://eddmann.com/posts/depth-first-search-and-breadth-first-search-in-python/
        visited, queue = set(), [(pkg_name, pkg_version)]
        while queue:
            vertex = queue.pop(0)
            if vertex not in visited:
                visited.add(vertex)
                dep_name, dep_version = vertex
                queue.extend(
                    set(getattr(self, dep_func_name)(pkg_name=dep_name, pkg_version=dep_version, install_env=temp_env).items())
                    - visited)
        # dependencies excludes the start package
        return dict(visited - {(pkg_name, pkg_version)})

    def get_dep(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        # dict of dependencies and their versions: {dep_pkg1: dep_pkg1_version, dep_pkg2: dep_pkg2_version, ...}
        # NOTE: the dependencies are direct dependencies, not flattened dependencies.
        # query for metadata (e.g. authors) and cache them
        self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        # load the dependency information for a package or get and cache it in cache_dir
        pass

    def get_dep_file(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        # get path to the dependency information for a package or get and cache it and return path
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            self.get_dep(pkg_name=pkg_name, pkg_version=pkg_version, flatten=flatten, cache_only=cache_only)
            if flatten:
                dep_fname = self.get_flatten_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            else:
                dep_fname = self.get_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            return join(pkg_info_dir, dep_fname)
        else:
            logging.error("get_dep_file: cache dir is not specified!")
            return None

    def install_dep(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                    outdir=None):
        # install package dependency (with sudo) in install_dir and optionally store the trace to outdir
        pass

    def has_install(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # get package metadata and check for install fields in the package
        pass

    def test(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        # test the package if test command is available
        pass

    def has_test(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # get package metadata and check for test fields in the package
        pass

    def main(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        # run the package if main executable are available
        pass

    def has_main(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # get package metadata and check for main/start fields in the package
        pass

    def exercise(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                 outdir=None, timeout=None):
        # import the package and trigger the events that it registers
        pass

    def has_exercise(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # get package metadata and check for exercise fields in the package
        pass

    def build(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
              outdir=None):
        # FIXME: not implemented yet, not a priority
        # clone the repo and build it (inspired by malware event-stream/flatmap-stream)
        pass

    def has_build(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # FIXME: not implemented yet, not a priority
        # has build script or can be built
        pass

    def get_dynamic_result(self, pkg_name, outdir, pkg_version=None, sudo=False):
        dynamic_fname = self.get_dynamic_fname(pkg_name=pkg_name, pkg_version=pkg_version, sudo=sudo)
        dynamic_file = join(outdir, dynamic_fname)
        dynamic_result = None
        if exists(dynamic_file):
            logging.warning("get_dynamic_result: loading dynamic_file %s!", dynamic_file)
            dynamic_result = DynamicAnalysis()
            read_proto_from_file(dynamic_result, dynamic_file, binary=False)
        else:
            logging.warning("skipping pkg %s ver %s due to unavailability!", pkg_name, pkg_version)
        return dynamic_result

    @staticmethod
    def filter_versions(version_date, max_num=15, min_gap_days=30, with_time=False):
        if len(version_date) <= max_num:
            return [version for version, _ in version_date] if not with_time else version_date
        # skip alpha versions (v1.2.3 and 1.2.3 are both allowed)
        version_date = filter(lambda k: k[0].strip('v').replace('.', '').isdigit(), version_date)
        if len(version_date) == 0:
            return []
        if max_num <= 0:
            return [version for version, _ in version_date] if not with_time else version_date
        else:
            max_date = version_date[0][1]
            min_gap_days_delta = datetime.timedelta(days=min_gap_days)
            if len(version_date) <= max_num:
                return [version for version, _ in version_date] if not with_time else version_date
            else:
                versions = []
                # sorted versions by upload dates, and choose them based on a gap of min_gap_days
                sorted_version_date = sorted(version_date, key=lambda (ver, dt): dt, reverse=True)
                for _, ver_grp in itertools.groupby(
                        sorted_version_date,
                        lambda (ver, dt): int((max_date - dt).total_seconds()/min_gap_days_delta.total_seconds())):
                    # v1.2.3 and 1.2.3 are both allowed
                    sorted_ver_grp = sorted(ver_grp, key=lambda (ver, dt): map(lambda digit: int(digit) if digit else 0, ver.strip('v').split('.')), reverse=True)
                    if with_time:
                        versions.append(sorted_ver_grp[0])
                    else:
                        versions.append(sorted_ver_grp[0][0])
                return versions[:max_num]

    @staticmethod
    def get_sanitized_pkgname(pkg_name):
        """
        FIXME: keep this consistent with get_sanitized_pkgname in maloss/main/detector.py

        1. Npmjs, Maven and Packagist have scoped packages (i.e. gid/aid), where '/' is not allowed in docker name
        2. Npmjs group id starts with '@' (e.g. @invelo/module), where '@' is not allowed in docker name
        3. Rubygems packages may start with characters not allowed for docker name, such as '-' and '_'
        4. Other invalid docker name characters
            https://github.com/npm/validate-npm-package-name
            Npmjs may contain '!', '*', '~', "'", '(', ')', although not allowed in the above link.
                e.g. https://www.npmjs.com/package/@(._.)/oooooo
                e.g. https://www.npmjs.com/package/foo~
                e.g. https://www.npmjs.com/package/@bre!zh/emitter
                e.g. https://www.npmjs.com/package/highcharts-*
                e.g. https://www.npmjs.com/package/marqueexss-test123'
            Maven may contain '+'
                e.g. http://repo1.maven.org/maven2/com/github/xdyuchen/mvp+android/
        """
        # NOTE: step 2 and 3 is not needed for filename, step 1 and 4 is applicable
        if not pkg_name:
            return pkg_name
        # case 1
        if '/' in pkg_name:
            pkg_name = pkg_name.replace('/', '..')
        # case 2
        # if pkg_name.startswith('@'):
        #     pkg_name = pkg_name.strip('@')
        # case 3
        # valid_start = re.compile(r'[a-zA-Z0-9]')
        # if not re.match(valid_start, pkg_name[0]):
        #     pkg_name = 'san..%s' % pkg_name
        # case 4
        invalid_name = re.compile(r'[^a-zA-Z0-9_.-]')
        pkg_name = re.sub(invalid_name, '..', pkg_name)
        return pkg_name

    @staticmethod
    def get_trace_fname(pkg_name, pkg_version=None, sudo=False):
        # FIXME: what if the trace_fname is too long!
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        trace_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        if sudo:
            trace_fname += ':sudo'
        return trace_fname + '.strace'

    @staticmethod
    def get_trace_dep_fname(pkg_name, pkg_version=None, sudo=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        trace_dep_fname = PackageManagerProxy.get_trace_fname(
            pkg_name=pkg_name, pkg_version=pkg_version, sudo=sudo)
        return splitext(trace_dep_fname)[0] + '.dep.strace'

    @staticmethod
    def get_metadata_fname(pkg_name, pkg_version=None, sudo=False, fmt='json'):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        metadata_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        if sudo:
            metadata_fname += ':sudo'
        return '%s.metadata.%s' % (metadata_fname, fmt)

    @staticmethod
    def get_versions_fname(pkg_name, fmt='json'):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        versions_fname = "%s.versions.%s" % (pkg_name, fmt)
        return versions_fname

    @staticmethod
    def get_version2hash_fname(pkg_name, fmt='json'):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        version2hash_fname = "%s.version2hash.%s" % (pkg_name, fmt)
        return version2hash_fname

    @staticmethod
    def get_dep_fname(pkg_name, pkg_version=None, sudo=False, fmt='json'):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        dep_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        if sudo:
            dep_fname += ':sudo'
        return '%s.dep.%s' % (dep_fname, fmt)

    @staticmethod
    def get_flatten_dep_fname(pkg_name, pkg_version=None, sudo=False, fmt='json'):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        dep_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        if sudo:
            dep_fname += ':sudo'
        return '%s.flatten_dep.%s' % (dep_fname, fmt)

    @staticmethod
    def get_astgen_fname(pkg_name, pkg_version=None, binary=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        astgen_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        suffix = 'pb' if binary else 'txt'
        return '%s.astgen.%s' % (astgen_fname, suffix)

    @staticmethod
    def get_compare_versions_fname(pkg_name, fmt='json'):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        compare_versions_fname = "%s.compare_versions.%s" % (pkg_name, fmt)
        return compare_versions_fname

    @staticmethod
    def get_astfilter_fname(pkg_name, pkg_version=None, binary=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        astfilter_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        suffix = 'pb' if binary else 'txt'
        return '%s.astfilter.%s' % (astfilter_fname, suffix)

    @staticmethod
    def get_taint_fname(pkg_name, pkg_version=None, binary=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        taint_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        suffix = 'pb' if binary else 'txt'
        return '%s.taint.%s' % (taint_fname, suffix)

    @staticmethod
    def get_danger_fname(pkg_name, pkg_version=None, binary=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        danger_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        suffix = 'pb' if binary else 'txt'
        return '%s.danger.%s' % (danger_fname, suffix)

    @staticmethod
    def get_static_fname(pkg_name, pkg_version=None, binary=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        static_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        suffix = 'pb' if binary else 'txt'
        return '%s.static.%s' % (static_fname, suffix)

    @staticmethod
    def get_dynamic_fname(pkg_name, pkg_version=None, sudo=False, binary=False, sanitized=False):
        if not sanitized:
            pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        dynamic_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        if sudo:
            dynamic_fname += ':sudo'
        suffix = 'pb' if binary else 'txt'
        return '%s.dynamic.%s' % (dynamic_fname, suffix)

    @staticmethod
    def get_concolic_fname(pkg_name, pkg_version=None, sudo=False, binary=False, sanitized=False):
        if not sanitized:
            pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        concolic_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        if sudo:
            concolic_fname += ':sudo'
        suffix = 'pb' if binary else 'txt'
        return '%s.dynamic.%s' % (concolic_fname, suffix)

    @staticmethod
    def get_analysis_result_fname(pkg_name, pkg_version=None, binary=False):
        pkg_name = PackageManagerProxy.get_sanitized_pkgname(pkg_name=pkg_name)
        analysis_result_fname = '%s:%s' % (pkg_name, pkg_version) if pkg_version else '%s:latest' % pkg_name
        suffix = 'pb' if binary else 'txt'
        return '%s.result.%s' % (analysis_result_fname, suffix)

    @staticmethod
    def decorate_strace(pkg_name, pkg_version, trace, trace_string_size, sudo, outdir, command, is_dep=False):
        if trace and outdir is not None:
            if not exists(outdir):
                os.makedirs(outdir)
            if is_dep:
                trace_fname = PackageManagerProxy.get_trace_dep_fname(
                    pkg_name=pkg_name, pkg_version=pkg_version, sudo=sudo)
            else:
                trace_fname = PackageManagerProxy.get_trace_fname(
                    pkg_name=pkg_name, pkg_version=pkg_version, sudo=sudo)
            trace_file = join(outdir, trace_fname)
            strace_cmd = ['strace', '-fqv', '-s', str(trace_string_size), '-o', trace_file]
            if sudo:
                strace_cmd = ['sudo'] + strace_cmd
            return strace_cmd + command
        else:
            return command

    @staticmethod
    def decorate_strace_file(infile, trace, trace_string_size, sudo, outdir, command):
        if trace and outdir is not None:
            if not exists(outdir):
                os.makedirs(outdir)
            # craft the trace filename
            trace_fname = basename(infile)
            if sudo:
                trace_fname += ':sudo'
            trace_fname += '.strace'
            trace_file = join(outdir, trace_fname)
            strace_cmd = ['strace', '-fqv', '-s', str(trace_string_size), '-o', trace_file]
            if sudo:
                strace_cmd = ['sudo'] + strace_cmd
            return strace_cmd + command
        else:
            return command


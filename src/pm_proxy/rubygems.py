import json
import logging
import re
import os
import glob
import shutil
import tempfile
import dateutil.parser
from os.path import exists, join

import requests

from util.job_util import exec_command
from pm_proxy.pm_base import PackageManagerProxy


class RubygemsProxy(PackageManagerProxy):
    # Provide a standard and simplified way to build and package Ruby C and Java extensions using Rake as glue.
    # https://github.com/rake-compiler/rake-compiler
    def __init__(self, registry=None, cache_dir=None, isolate_pkg_info=False):
        super(RubygemsProxy, self).__init__()
        self.registry = registry
        self.cache_dir = cache_dir
        self.isolate_pkg_info = isolate_pkg_info
        self.metadata_format = 'json'
        self.dep_format = 'json'

    def _get_pkg_fname(self, pkg_name, pkg_version=None, suffix='gem'):
        # gem fetch the following gems: e.g. google-protobuf-3.7.0-x86_64-linux.gem, protobuf-3.10.0.gem
        if pkg_version is None:
            return '%s-*.%s' % (pkg_name, suffix)
        else:
            return '%s-%s*.%s' % (pkg_name, pkg_version, suffix)

    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        # download using gem fetch
        logging.warning("consider platform to download %s ver %s", pkg_name, pkg_version)
        download_cmd = ['gem', 'fetch', pkg_name]
        if pkg_version:
            download_cmd += ['-v', pkg_version]
        if binary:
            logging.warning("support for binary downloading is not added yet!")
        # ruby download with dependencies
        # https://gist.github.com/Milly/909564
        if with_dep:
            logging.warning("support for downloading dependencies is not added yet!")
        exec_command('gem fetch', download_cmd, cwd=outdir)
        download_path = join(outdir, self._get_pkg_fname(pkg_name=pkg_name, pkg_version=pkg_version))
        download_paths = glob.glob(download_path)
        if len(download_paths) == 1:
            return download_paths[0]
        logging.error("failed to download pkg %s ver %s using gem fetch", pkg_name, pkg_version)

        # download using wget, ignore the platform
        logging.warning("fallback to ignore platform to download pkg %s ver %s")
        # ignore platform
        # https://rubygems.org/api/v1/gems/json-jruby.json
        # https://rubygems.org/gems/json-jruby-1.5.0-java.gem
        pkg_info = self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        if pkg_info is None:
            return None
        gem_uri = pkg_info['gem_uri']
        if gem_uri:
            # FIXME: use wget, rather than curl, to follow redirects
            download_fname = gem_uri.rsplit('/', 1)[-1]
            download_cmd = ['wget', gem_uri, '-O', download_fname]
            if binary:
               logging.warning("support for binary downloading is not added yet!")
            if with_dep:
                logging.warning("support for downloading dependencies is not added yet!")
            exec_command('gem fetch (wget)', download_cmd, cwd=outdir)
            download_path = join(outdir, download_fname)
            if exists(download_path):
                return download_path
        logging.error("failed to download pkg %s ver %s", pkg_name, pkg_version)
        return None

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        install_cmd = ['gem', 'install', pkg_name]
        if pkg_version:
            install_cmd += ['-v', pkg_version]
        if install_dir:
            # NOTE: --install-dir and --user-install are conflicting options, and cannot be both specified
            install_cmd += ['--install-dir', install_dir]
            if sudo:
                install_cmd = ['sudo'] + install_cmd
        else:
            if sudo:
                install_cmd = ['sudo'] + install_cmd
            else:
                install_cmd += ['--user-install']
        install_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                           trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                           command=install_cmd)
        exec_command('gem install', install_cmd)

    def install_file(self, infile, trace=False, trace_string_size=1024, sudo=False, install_dir=None, outdir=None):
        install_cmd = ['gem', 'install', infile]
        if sudo:
            install_cmd = ['sudo'] + install_cmd
        else:
            install_cmd += ['--user-install']
        install_cmd = self.decorate_strace_file(infile=infile, trace=trace, trace_string_size=trace_string_size,
                                                sudo=sudo, outdir=outdir, command=install_cmd)
        exec_command('gem install file', install_cmd)

    def uninstall(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                  outdir=None):
        uninstall_cmd = ['gem', 'uninstall', pkg_name]
        if pkg_version:
            uninstall_cmd += ['-v', pkg_version]
        if sudo:
            uninstall_cmd = ['sudo'] + uninstall_cmd
        else:
            uninstall_cmd += ['--user-install']
        uninstall_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                             trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                             command=uninstall_cmd)
        exec_command('gem uninstall', uninstall_cmd)

    def get_metadata(self, pkg_name, pkg_version=None):
        # rubygems API: https://guides.rubygems.org/rubygems-org-api/
        # e.g. curl https://rubygems.org/api/v1/gems/rails.json
        # e.g. curl https://rubygems.org/api/v1/versions/coulda.json
        # e.g. curl https://rubygems.org/api/v1/versions/rails/latest.json
        # load cached metadata information
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            metadata_fname = self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.metadata_format)
            metadata_file = join(pkg_info_dir, metadata_fname)
            if exists(metadata_file):
                logging.warning("get_metadata: using cached metadata_file %s!", metadata_file)
                if self.metadata_format == 'json':
                    try:
                        return json.load(open(metadata_file, 'r'))
                    except:
                        logging.debug("fail to load metadata_file: %s, regenerating!", metadata_file)
                else:
                    logging.error("get_metadata: output format %s is not supported!", self.metadata_format)
                    return None
        # use rubygems API to get metadata
        if self.registry and self.registry != 'https://rubygems.org':
            logging.warning("Using non-default registry for ruby: %s", self.registry)
            metadata_url = "%s/api/v1/gems/%s.json" % (self.registry, pkg_name)
        else:
            metadata_url = "https://rubygems.org/api/v1/gems/%s.json" % pkg_name
        try:
            metadata_content = requests.request('GET', metadata_url)
            pkg_info = json.loads(metadata_content.text)
        except:
            logging.error("fail in get_metadata for pkg %s, ignoring!", pkg_name)
            return None
        # count the number of develop dependencies and runtime dependencies
        develop_dependencies = {}
        runtime_dependencies = {}
        if pkg_info and 'dependencies' in pkg_info:
            if 'development' in pkg_info['dependencies']:
                develop_dependencies = {dep_info['name'] for dep_info in pkg_info['dependencies']['development']}
            if 'runtime' in pkg_info['dependencies']:
                runtime_dependencies = {dep_info['name'] for dep_info in pkg_info['dependencies']['runtime']}
        logging.warning("package %s has %d development dependencies!", pkg_name, len(develop_dependencies))
        logging.warning("package %s has %d runtime dependencies!", pkg_name, len(runtime_dependencies))
        # optionally cache metadata
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            metadata_fname = self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                     fmt=self.metadata_format)
            metadata_file = join(pkg_info_dir, metadata_fname)
            if self.metadata_format == 'json':
                json.dump(pkg_info, open(metadata_file, 'w'), indent=2)
            else:
                logging.error("get_metadata: output format %s is not supported!", self.metadata_format)
        return pkg_info

    def get_versions(self, pkg_name, max_num=15, min_gap_days=30, with_time=False):
        # load cached versions information
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            versions_fname = self.get_versions_fname(pkg_name=pkg_name)
            versions_file = join(pkg_info_dir, versions_fname)
            if exists(versions_file):
                logging.warning("get_versions: using cached versions_file %s!", versions_file)
                try:
                    versions_info = json.load(open(versions_file, 'r'))
                    version_date = [(version_info['number'], dateutil.parser.parse(version_info['created_at']))
                                    for version_info in versions_info if 'created_at' in version_info]
                    return self.filter_versions(version_date=version_date, max_num=max_num, min_gap_days=min_gap_days,
                                                with_time=with_time)
                except:
                    logging.error("fail to load versions_file: %s, regenerating!", versions_file)
        # use rubygems API to get versions infomrmation
        if self.registry and self.registry != 'https://rubygems.org':
            logging.warning("Using non-default registry for ruby: %s", self.registry)
            versions_url = "%s/api/v1/versions/%s.json" % (self.registry, pkg_name)
        else:
            versions_url = "https://rubygems.org/api/v1/versions/%s.json" % pkg_name
        try:
            logging.warning("fetching versions info for %s", pkg_name)
            versions_content = requests.request('GET', versions_url)
            versions_info = json.loads(versions_content.text)
        except:
            logging.error("fail in get_versions for pkg %s, ignoring!", pkg_name)
            return []
        # optionally cache versions information
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            versions_fname = self.get_versions_fname(pkg_name=pkg_name)
            versions_file = join(pkg_info_dir, versions_fname)
            json.dump(versions_info, open(versions_file, 'w'), indent=2)
        # filter versions
        version_date = [(version_info['number'], dateutil.parser.parse(version_info['created_at']))
                        for version_info in versions_info if 'created_at' in version_info]
        return self.filter_versions(version_date=version_date, max_num=max_num, min_gap_days=min_gap_days,
                                    with_time=with_time)

    def get_author(self, pkg_name):
        pkg_info = self.get_metadata(pkg_name=pkg_name)
        if pkg_info is None:
            return {}
        authors = pkg_info.get('authors', None)
        # use rubygems API to get owners information
        owners_url = "https://rubygems.org/api/v1/gems/%s/owners.json" % pkg_name
        try:
            logging.warning("fetching owners info for %s", pkg_name)
            owners_content = requests.request('GET', owners_url)
            owners_info = json.loads(owners_content.text)
        except:
            logging.error("fail in get_author for pkg %s, ignoring!", pkg_name)
            owners_info = None
        return {'authors': authors, 'owners': owners_info}

    def _get_gem_dep_pkgs(self, pkg_name, pkg_version=None):
        # Alternatively, use gem dependency, but it is regex-based and tricky to parse.
        pkg_info = self.get_metadata(pkg_name=pkg_name, pkg_version=pkg_version)
        if pkg_info and 'dependencies' in pkg_info and 'runtime' in pkg_info['dependencies']:
            pkg_info_deps = pkg_info['dependencies']['runtime']
            if pkg_info_deps:
                return [dep_info['name'] for dep_info in pkg_info_deps]
        return []

    def _get_gem_list_pkgs(self, pkg_name, pkg_version=None, install_env=None):
        # NOTE: pkg_version is a placeholder for callbacks and is not used here.
        dep_pkg_names = self._get_gem_dep_pkgs(pkg_name=pkg_name, pkg_version=pkg_version)
        # run gem list to get the dependencies
        list_cmd = ['gem', 'list']
        installed_pkgs_str = exec_command('gem list', list_cmd, ret_stdout=True, env=install_env)
        # e.g. google-protobuf (3.6.1 x86_64-linux)
        # e.g. couchbase (1.3.15)
        # e.g. csv (default: 1.0.0)
        # e.g. parser (2.5.1.2, 2.5.1.0)
        installed_pkgs = [
            (dep_name, dep_version.split(': ')[-1].split(', ')[0].split(' ')[0]) for dep_name, dep_version in
            [installed_pkg.strip(')').split(' (') for installed_pkg in
             filter(bool, installed_pkgs_str.split('\n'))]
        ]
        dep_pkgs = {dep_name: dep_version for dep_name, dep_version in installed_pkgs if dep_name in dep_pkg_names}
        return dep_pkgs

    def get_dep(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        # FIXME: Alternatively, specify customized install directory for gems, similar to npmjs
        # https://stackoverflow.com/questions/16098757/specify-gem-installation-directory
        super(RubygemsProxy, self).get_dep(pkg_name=pkg_name, pkg_version=pkg_version, flatten=flatten,
                                           cache_only=cache_only)
        # load cached dependency information
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            if flatten:
                dep_fname = self.get_flatten_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            else:
                dep_fname = self.get_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            dep_file = join(pkg_info_dir, dep_fname)
            if exists(dep_file):
                logging.warning("get_dep: using cached dep_file %s!", dep_file)
                if self.dep_format == 'json':
                    try:
                        return json.load(open(dep_file, 'r'))
                    except:
                        logging.debug("fail to load dep_file: %s, regenerating!", dep_file)
                else:
                    logging.error("get_dep: output format %s is not supported!", self.dep_format)
                    return None
        if cache_only:
            return None
        # option 1: show the dependencies of an installed gem, e.g. gem dependency REGEXP
        # option 2: get dependency from json file, but we may be installing the wrong version
        temp_install_dir = tempfile.mkdtemp(prefix='get_dep-')
        self.install(pkg_name=pkg_name, pkg_version=pkg_version, install_dir=temp_install_dir)
        # run gem depedency and gem list to get the dependencies
        temp_env = os.environ.copy()
        temp_env["GEM_HOME"] = temp_install_dir
        dep_pkgs = self._get_gem_list_pkgs(pkg_name=pkg_name, pkg_version=pkg_version, install_env=temp_env)
        # recursively get the flatten dependency packages, useful for static analysis
        flatten_dep_pkgs = self.bfs_all_deps(dep_func_name='_get_gem_list_pkgs', pkg_name=pkg_name,
                                             pkg_version=pkg_version, temp_env=temp_env) if len(dep_pkgs) > 0 else {}
        logging.warning("%s has %d deps and %d flatten deps", pkg_name, len(dep_pkgs), len(flatten_dep_pkgs))
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            dep_fname = self.get_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            dep_file = join(pkg_info_dir, dep_fname)
            flatten_dep_fname = self.get_flatten_dep_fname(pkg_name=pkg_name, pkg_version=pkg_version, fmt=self.dep_format)
            flatten_dep_file = join(pkg_info_dir, flatten_dep_fname)
            if self.dep_format == 'json':
                json.dump(dep_pkgs, open(dep_file, 'w'), indent=2)
                json.dump(flatten_dep_pkgs, open(flatten_dep_file, 'w'), indent=2)
            else:
                logging.error("get_dep: output format %s is not supported!", self.dep_format)
        # remove the installation directory
        shutil.rmtree(temp_install_dir)
        return flatten_dep_pkgs if flatten else dep_pkgs

    def install_dep(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                    outdir=None):
        # install the package, get its dependency, and then install the dependencies
        # https://stackoverflow.com/questions/23213849/what-is-the-syntax-for-gem-install-multiple-gems-specifying-versions-for-each
        dep_pkgs = self.get_dep(pkg_name=pkg_name, pkg_version=pkg_version)
        # NOTE: name:version doesn't work for all gem commands, particularly gem uninstall doesn't support this
        dep_pkgs_args = ['%s:%s' % (dep_name, dep_version) for dep_name, dep_version in dep_pkgs.items()]
        install_dep_cmd = ['gem', 'install'] + dep_pkgs_args + ['--ignore-dependencies']
        if sudo:
            install_dep_cmd = ['sudo'] + install_dep_cmd
        else:
            install_dep_cmd = install_dep_cmd + ['--user-install']
        install_dep_cmd = self.decorate_strace(pkg_name=pkg_name, pkg_version=pkg_version, trace=trace,
                                               trace_string_size=trace_string_size, sudo=sudo, outdir=outdir,
                                               command=install_dep_cmd, is_dep=True)
        exec_command('gem install dependency', install_dep_cmd, cwd=install_dir)

    def has_install(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # ruby packages have pre_install and post_install hooks
        # ruby packages have extensions, use extconf.rb to perform random malicious behavior
        # http://blog.costan.us/2008/11/post-install-post-update-scripts-for.html
        return True

    def test(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        pass

    def has_test(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        return False

    def main(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
             outdir=None, timeout=None):
        # run the python scripts created for package main.
        main_cmd = ['python', 'main.py', pkg_name, '-m', 'rubygems']
        exec_command('python main.py', main_cmd, cwd='pm_proxy/scripts', timeout=timeout)

    def has_main(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        # assume that the package is installed and check for folder bin, and executables there
        gem_path_cmd = ['gem', 'path', pkg_name.replace('-', '/')]
        gem_path = exec_command('gem path', gem_path_cmd, ret_stdout=True).strip()
        # FIXME: this assumes that the executables are placed inside bin folder. This may not hold all the time.
        bin_path = join(gem_path, 'bin')
        return exists(bin_path)

    def exercise(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                 outdir=None, timeout=None):
        # run the ruby script created for package exercise.
        exercise_cmd = ['ruby', 'exercise.rb', pkg_name]
        exec_command('ruby exercise.rb', exercise_cmd, cwd='pm_proxy/scripts', timeout=timeout)

    def has_exercise(self, pkg_name, pkg_version=None, binary=False, with_dep=False):
        return True


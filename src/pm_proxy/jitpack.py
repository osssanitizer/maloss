import os
import json
import shutil
import logging
import tempfile
import requests
from xml.etree.ElementTree import fromstring, tostring
from os.path import join, exists, getsize, expanduser

from util.job_util import exec_command
from pm_proxy.pm_base import PackageManagerProxy


class JitpackProxy(PackageManagerProxy):
    def __init__(self, registry=None, cache_dir=None, isolate_pkg_info=False):
        super(JitpackProxy, self).__init__()
        self.registry = registry
        self.cache_dir = cache_dir
        self.isolate_pkg_info = isolate_pkg_info
        self.metadata_format = 'pom'
        self.dep_format = 'json'

    def _get_pkg_fname(self, pkg_name, pkg_version, suffix='jar'):
        _, aid = pkg_name.split('/')
        return '%s-%s.%s' % (aid, pkg_version, suffix)

    def _get_pkg_dir(self, pkg_name, pkg_version):
        gid, aid = pkg_name.split('/')
        return '%s/%s/%s' % (gid.replace('.', '/'), aid, pkg_version)

    def download(self, pkg_name, pkg_version=None, outdir=None, binary=False, with_dep=False):
        # Download artifact from jitpack
        # https://coderwall.com/p/qbozzq/download-an-artifact-from-jitpack-io-using-maven
        # mvn dependency:get -DremoteRepositories=https://jitpack.io -Dartifact=com.github.dubasdey:coinbase-pro-client:0.0.4 -Dtransitive=false -Ddest=/tmp/
        # mvn dependency:get -DremoteRepositories=https://jitpack.io -Dartifact=com.google.protobuf:protobuf-java:3.5.1 -Dtransitive=false -Ddest=/tmp/
        # FIXME: assumes that pkg_version is always specified
        if binary:
            logging.warning("support for binary downloading is not added yet!")
        if with_dep:
            logging.warning("support for packing dependencies is not added yet!")
        possible_extensions = ('jar', 'aar', 'war')
        for extension in possible_extensions:
            # /tmp/protobuf-java-3.5.1.jar
            if extension != 'jar':
                download_artifact = '%s:%s:%s' % (pkg_name.replace('/', ':'), pkg_version, extension)
            else:
                download_artifact = '%s:%s' % (pkg_name.replace('/', ':'), pkg_version)
            download_cmd = ['mvn', 'dependency:get', '-DremoteRepositories=https://jitpack.io',
                            '-Dartifact=%s' % download_artifact, '-Dtransitive=false', '-Ddest=%s' % outdir]
            exec_command('mvn dependency:get', download_cmd)
            # cleanup intermediate folders
            temp_install_path = expanduser(join('~/.m2/repository', self._get_pkg_dir(pkg_name=pkg_name, pkg_version=pkg_version)))
            shutil.rmtree(temp_install_path)
            # check if download path exists to see if the download is successful or not
            download_path = join(outdir, self._get_pkg_fname(pkg_name=pkg_name, pkg_version=pkg_version, suffix=extension))
            if exists(download_path):
                return download_path
        logging.error("failed to download pkg %s ver %s", pkg_name, pkg_version)
        return None

    def install(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, install_dir=None, outdir=None,
                sudo=False):
        pass

    def install_file(self, infile, trace=False, trace_string_size=1024, sudo=False, install_dir=None, outdir=None):
        pass

    def uninstall(self, pkg_name, pkg_version=None, trace=False, trace_string_size=1024, sudo=False, install_dir=None,
                  outdir=None):
        pass

    def get_metadata(self, pkg_name, pkg_version=None):
        # Download pom file from jitpack
        # mvn dependency:get -DremoteRepositories=https://jitpack.io -Dartifact=com.github.dubasdey:coinbase-pro-client:0.0.4:pom -Dtransitive=false -Ddest=/tmp/
        # load cached metadata information
        pkg_info_dir = self.get_pkg_info_dir(pkg_name=pkg_name)
        if pkg_info_dir is not None:
            metadata_fname = self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                     fmt=self.metadata_format)
            metadata_file = join(pkg_info_dir, metadata_fname)
            if exists(metadata_file):
                logging.warning("get_metadata: using cached metadata_file %s!", metadata_file)
                if self.metadata_format == 'pom':
                    return fromstring(open(metadata_file, 'r').read())
                else:
                    logging.error("get_metadata: output format %s is not supported!", self.metadata_format)
                    return None
        # Jitpack metadata is loaded by running dependency:get command
        try:
            download_pom = '%s:%s:%s' % (pkg_name.replace('/', ':'), pkg_version, 'pom')
            download_cmd = ['mvn', 'dependency:get', '-DremoteRepositories=https://jitpack.io',
                            '-Dartifact=%s' % download_pom, '-Dtransitive=false']
            exec_command('mvn dependency:get', download_cmd)
            # cleanup intermediate folders
            temp_install_path = expanduser(join('~/.m2/repository', self._get_pkg_dir(pkg_name=pkg_name, pkg_version=pkg_version)))
            metadata_content = open(join(temp_install_path, self._get_pkg_fname(pkg_name=pkg_name, pkg_version=pkg_version, suffix='pom')), 'r').read()
            shutil.rmtree(temp_install_path)
            # check if download path exists to see if the download is successful or not
            pkg_info = fromstring(metadata_content)
        except:
            logging.error("fail in get_metadata for pkg %s, ignoring!", pkg_name)
            return None
        if pkg_info_dir is not None:
            if not exists(pkg_info_dir):
                os.makedirs(pkg_info_dir)
            metadata_fname = self.get_metadata_fname(pkg_name=pkg_name, pkg_version=pkg_version,
                                                     fmt=self.metadata_format)
            metadata_file = join(pkg_info_dir, metadata_fname)
            if self.metadata_format == 'pom':
                open(metadata_file, 'w').write(metadata_content)
            else:
                logging.error("get_metadata: output format %s is not supported!", self.metadata_format)
        return pkg_info

    def get_versions(self, pkg_name, max_num=15, min_gap_days=30, with_time=False):
        # FIXME: the max_num and min_gap_days are not checked and enforced!
        # FIXME: the versions info is not cached
        # curl https://jitpack.io/api/builds/com.github.jitpack/maven-simple
        gid, aid = pkg_name.split('/')
        versions_url = "https://jitpack.io/api/builds/%s" % pkg_name
        try:
            versions_content = requests.request('GET', versions_url)
            versions_info = json.loads(versions_content.text)
        except Exception as e:
            logging.error("fail to get versions_info for %s", pkg_name)
            return []
        if not gid in versions_info or not aid in versions_info[gid]:
            return []
        return [version for version, status in versions_info[gid][aid].items() if status == 'ok']

    def get_version_hash(self, pkg_name, pkg_version, algorithm='sha1'):
        if algorithm not in ('sha1', 'md5'):
            raise Exception("algorithm %s is not supported!" % algorithm)
        # https://jitpack.io/api/builds/com.github.dubasdey/coinbase-pro-client/0.0.4
        temp_repo_dir = tempfile.mkdtemp(prefix='get_version_hash-')
        self.download(pkg_name=pkg_name, pkg_version=pkg_version, outdir=temp_repo_dir)
        possible_extensions = ('jar', 'aar', 'war')
        version_hash = None
        for extension in possible_extensions:
            temp_repo_filepath = join(temp_repo_dir, self._get_pkg_fname(pkg_name=pkg_name, pkg_version=pkg_version, suffix=extension))
            if not exists(temp_repo_filepath) or getsize(temp_repo_filepath) == 0:
                continue
            hash_command = '%ssum' % algorithm
            version_hash = exec_command(hash_command, [hash_command, temp_repo_filepath], ret_stdout=True)
            version_hash = version_hash.split(' ')[0]
            break
        shutil.rmtree(temp_repo_dir)
        if version_hash is None:
            logging.error("fail in get_version_hash for pkg %s ver %s, ignoring!", pkg_name, pkg_version)
            return None
        return version_hash

    def get_dep(self, pkg_name, pkg_version=None, flatten=False, cache_only=False):
        super(JitpackProxy, self).get_dep(pkg_name=pkg_name, pkg_version=pkg_version, flatten=flatten,
                                          cache_only=cache_only)
        raise Exception("not implemented yet! current version only deals with maven central and jar files!")
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
        # use maven dependency to get the dependencies
        temp_repo_dir = tempfile.mkdtemp(prefix='get_dep-')
        # https://stackoverflow.com/questions/3342908/how-to-get-a-dependency-tree-for-an-artifact
        # http://maven.apache.org/plugins/maven-dependency-plugin/tree-mojo.html
        dep_pkgs = {}
        flatten_dep_pkgs = {}
        try:
            pom_filename = 'pom.xml'
            dep_tree_filename = 'dep_tree.txt'
            metadata_file = self.get_metadata_file(pkg_name=pkg_name, pkg_version=pkg_version)
            shutil.copy(metadata_file, join(temp_repo_dir, pom_filename))
            get_dep_cmd = ['mvn', 'dependency:tree', '-DoutputFile=%s' % dep_tree_filename, '-DoutputType=text']
            exec_command('mvn dependency:tree', get_dep_cmd, cwd=temp_repo_dir)
            dep_tree_file = join(temp_repo_dir, dep_tree_filename)
            for line in open(dep_tree_file, 'r'):
                line = line.strip('\n')
                if not line:
                    continue
                line_parts = line.split(' ')
                if len(line_parts) <= 1:
                    continue
                elif len(line_parts) == 2:
                    dep_pkg_info = line_parts[-1].split(':')
                    if len(dep_pkg_info) != 5:
                        logging.error("pkg %s has dependency with unexpected format: %s", pkg_name, line)
                    gid, aid, _, vid, dep_type = dep_pkg_info
                    # TODO: do we want compile dependency or test dependency (dep_type), currently recording both
                    dep_name = '%s/%s' % (gid, aid)
                    dep_pkgs[dep_name] = vid
                    flatten_dep_pkgs[dep_name] = vid
                else:
                    dep_pkg_info = line_parts[-1].split(':')
                    if len(dep_pkg_info) != 5:
                        logging.error("pkg %s has indirect dependency with unexpected format: %s", pkg_name, line)
                    gid, aid, _, vid, dep_type = dep_pkg_info
                    dep_name = '%s/%s' % (gid, aid)
                    flatten_dep_pkgs[dep_name] = vid
        except Exception as e:
            logging.error("failed while getting dependencies (%s) for pkg %s: %s!", flatten_dep_pkgs, pkg_name, str(e))
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
        # remove the repo directory
        shutil.rmtree(temp_repo_dir)
        return flatten_dep_pkgs if flatten else dep_pkgs

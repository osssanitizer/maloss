import os
import re
import csv
import sys
import docker
import logging
import subprocess
import config as appconfig
import logger as applogger

from progressbar import ProgressBar
from os.path import exists, join, dirname, realpath


# FIXME: solve the cgroup error caused by too many docker containers
clean_cmd = 'sudo sh -c "echo 1 > /proc/sys/vm/drop_caches"'


def get_pkg_list(pkgfile, skipfile=None):
    pkgs = []
    reader = csv.DictReader(open(pkgfile, 'r'))
    with_version = False
    for row in reader:
        if row['version']:
            with_version = True
            pkgs.append((row['package name'], row['version'], row['language']))
        else:
            pkgs.append((row['package name'], row['language']))
    logging.warning("loaded %d packages (with_version=%s) to process!", len(pkgs), with_version)
    if skipfile and exists(skipfile):
        pkgs_done = {line.split(':')[0] for line in open(skipfile, 'r')}
        pkgs = filter(lambda k: k[0] not in pkgs_done, pkgs)
        logging.warning("after skipping processed ones, left %d packages (with_version=%s) to process!",
                        len(pkgs), with_version)
    return pkgs, with_version


def get_sanitized_pkgname(pkgname):
    """
    FIXME: keep this consistent with get_sanitized_pkgname in maloss/src/pm_proxy/pm_base.py

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
    if not pkgname:
        logging.error("invalid pkg %s", pkgname)
        return pkgname
    # case 1
    if '/' in pkgname:
        pkgname = pkgname.replace('/', '..')
    # case 2
    if pkgname.startswith('@'):
        pkgname = pkgname.strip('@')
    # case 3
    valid_start = re.compile(r'[a-zA-Z0-9]')
    if not re.match(valid_start, pkgname[0]):
        pkgname = 'san..%s' % pkgname
    # case 4
    invalid_name = re.compile(r'[^a-zA-Z0-9_.-]')
    pkgname = re.sub(invalid_name, '..', pkgname)
    return pkgname


def get_dir_for_language_pkgname(analyzer, dirstr, language, pkgname=None):
    dirvalue = getattr(analyzer, dirstr)
    dir_for_language = join(dirvalue, str(language))
    dir_for_language_pkgname = join(dir_for_language, get_sanitized_pkgname(pkgname)) if pkgname else dir_for_language
    if not exists(dir_for_language_pkgname):
        os.makedirs(dir_for_language_pkgname)
        os.chmod(dir_for_language_pkgname, 0o777)
        analyzer.logger.info("changing permissions dir %s", dir_for_language_pkgname)
    return dir_for_language_pkgname


def prune_containers(name="malossscan/maloss"):
    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"ancestor": name}, all=True)
    for container in containers:
        container.remove()


def get_container_name_prefix(pkgname, pkgversion=None):
    return '%s..%s..' % (get_sanitized_pkgname(pkgname), pkgversion)


def get_container_name(pkgname, pkgversion=None, job=None):
    return '%s..%s..%s' % (get_sanitized_pkgname(pkgname), pkgversion, job)


###########################################################
# Get metadata and versions information
###########################################################
def get_metadata(analyzer, pkgname, language, pkgversion=None):
    """
    Invoke the get_metadata call to fetch metadata and versions information.
    """
    analyzer.logger.info("analyzing pkg %s version %s for language %s", pkgname, pkgversion, language)
    # prepare the command, use common directory for packages, and output metadata into a specific folder
    metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language)
    get_metadata_cmd = "python main.py get_metadata -n %s -l %s -c %s --isolate_pkg_info" % (pkgname, language, metadata_dir)
    if pkgversion:
        get_metadata_cmd += " -v %s" % pkgversion
    get_metadata_logs = None
    try:
        srcdir = join(dirname(realpath(__file__)), "../src")
        get_metadata_logs = subprocess.check_output(get_metadata_cmd, shell=True, cwd=srcdir)
    except subprocess.CalledProcessError as cpe:
        analyzer.logger.error("failed to get_metadata for pkg %s ver %s: %s", pkgname, pkgversion, str(cpe))
    analyzer.logger.info("get_metadata job logs:\n%s", get_metadata_logs)


###########################################################
# Get metadata and dependency information
###########################################################
def get_dep(analyzer, pkgname, language, pkgversion=None, native=False):
    """
    Simply invoke the get_dep call to get metadata and dependency information.
    """
    analyzer.logger.info("analyzing pkg %s version %s for language %s", pkgname, pkgversion, language)
    analyzer.logger.info("check history is %s", analyzer.CHECK_HISTORY)

    # run the command either natively in a separate container
    get_dep_logs = None
    if native:
        # prepare the command, use common directory for packages, and output metadata into a specific folder
        metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language)
        get_dep_cmd = "python main.py get_dep -n %s -l %s -c %s --isolate_pkg_info" % (pkgname, language, metadata_dir)
        if pkgversion:
            get_dep_cmd += " -v %s" % pkgversion
        try:
            srcdir = join(dirname(realpath(__file__)), "../src")
            get_dep_logs = subprocess.check_output(get_dep_cmd, shell=True, cwd=srcdir)
        except subprocess.CalledProcessError as cpe:
            analyzer.logger.error("failed to get_dep for pkg %s ver %s: %s", pkgname, pkgversion, str(cpe))
    else:
        docker_client = docker.from_env()
        # prepare the command
        get_dep_cmd = "python main.py get_dep -n %s -l %s -c %s" % (pkgname, language, "/home/maloss/metadata")
        if pkgversion:
            get_dep_cmd += " -v %s" % pkgversion
        # get container names
        get_dep_name = get_container_name(pkgname=pkgname, pkgversion=pkgversion, job="get_dep")
        # create output directories and change their permissions to nobody:nogroup
        metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language,
                                                    pkgname=pkgname)
        analyzer.logger.info("running get_dep job for pkg %s, version %s language %s", pkgname, pkgversion, language)
        get_dep_kwargs = {'name': get_dep_name,
                          'volumes': {metadata_dir: {"bind": "/home/maloss/metadata", "mode": "rw"}},
                          'remove': True}
        if analyzer.MEMORY_LIMIT is not None:
            get_dep_kwargs['mem_limit'] = analyzer.MEMORY_LIMIT
        get_dep_logs = docker_client.containers.run("malossscan/maloss", command=get_dep_cmd, **get_dep_kwargs)
    analyzer.logger.info("get_dep job logs:\n%s", get_dep_logs)


def stop_get_dep(analyzer, pkgname, language, pkgversion=None):
    analyzer.logger.warning("stopping job get_dep for pkg %s version %s for language %s", pkgname, pkgversion, language)
    docker_client = docker.from_env()
    get_dep_containers = docker_client.containers.list(
        filters={'name': get_container_name_prefix(pkgname=pkgname, pkgversion=pkgversion)})
    for container in get_dep_containers:
        try:
            container.stop(timeout=analyzer.DOCKER_TIMEOUT)
            container.remove()
        except Exception as re:
            analyzer.logger.error("failed to remove container %s: %s", container.name, re)


###########################################################
# Compare packages and/or their versions
###########################################################
def compare(analyzer, pkgname, language):
    """
    Invoke the compare call to compare packages and/or their versions.
    """
    analyzer.logger.info("analyzing pkg %s for language %s", pkgname, language)
    metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language)
    result_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="RESULT_DIR", language=language)
    astgen_config = "/home/maloss/config/astgen.config"
    compare_cmd = "python main.py compare_ast -n %s -l %s -d %s -o %s -c %s" % (
        pkgname, language, metadata_dir, result_dir, astgen_config)
    compare_logs = None
    try:
        srcdir = join(dirname(realpath(__file__)), "../src")
        compare_logs = subprocess.check_output(compare_cmd, shell=True, cwd=srcdir)
    except subprocess.CalledProcessError as cpe:
        analyzer.logger.error("failed to compare for pkg %s: %s", pkgname, str(cpe))
    analyzer.logger.info("compare job logs:\n%s", compare_logs)


###########################################################
# Run api analysis for packages
###########################################################
def astfilter_local(analyzer, pkgname, language, pkgversion=None):
    """
    Invoke the astgen call to run astgen analysis on specified package.
    """
    analyzer.logger.info("analyzing pkg %s version %s for language %s", pkgname, pkgversion, language)
    metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language)
    result_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="RESULT_DIR", language=language)
    astgen_config = "/home/maloss/config/astgen.config"
    astfilter_cmd = "python main.py astfilter --ignore_dep -n %s -l %s -d %s -o %s -c %s" % (
        pkgname, language, metadata_dir, result_dir, astgen_config)
    if pkgversion:
        astfilter_cmd += " -v %s" % pkgversion
    astfilter_logs = None
    try:
        srcdir = join(dirname(realpath(__file__)), "../src")
        astfilter_logs = subprocess.check_output(astfilter_cmd, shell=True, cwd=srcdir)
    except subprocess.CalledProcessError as cpe:
        analyzer.logger.error("failed to astfilter for pkg %s version %s: %s", pkgname, pkgversion, str(cpe))
    analyzer.logger.info("astfilter job logs:\n%s", astfilter_logs)


###########################################################
# Run taint analysis for packages
###########################################################
def taint_local(analyzer, pkgname, language, pkgversion=None):
    """
    Invoke the taint call to run taint analysis on specified package.
    """
    analyzer.logger.info("analyzing pkg %s version %s for language %s", pkgname, pkgversion, language)
    metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language)
    result_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="RESULT_DIR", language=language)
    astgen_config = "/home/maloss/config/astgen.config"
    taint_cmd = "python main.py taint --ignore_dep -n %s -l %s -d %s -o %s -c %s" % (
        pkgname, language, metadata_dir, result_dir, astgen_config)
    if pkgversion:
        taint_cmd += " -v %s" % pkgversion
    taint_logs = None
    try:
        srcdir = join(dirname(realpath(__file__)), "../src")
        taint_logs = subprocess.check_output(taint_cmd, shell=True, cwd=srcdir)
    except subprocess.CalledProcessError as cpe:
        analyzer.logger.error("failed to taint for pkg %s version %s: %s", pkgname, pkgversion, str(cpe))
    analyzer.logger.info("taint job logs:\n%s", taint_logs)


###########################################################
# Installation analysis
###########################################################
def install(analyzer, pkgname, language, pkgversion=None, native=False):
    """
    The installation analysis can be done in three steps or two steps (depending on tracing mechanism).
    First, run install to get the dependencies (strace).
    Second, install dependencies and then install the package with tracing (strace/sysdig).
    Third, optionally repeat the Second step with sudo privilege (strace/sysdig).
    """
    analyzer.logger.info("analyzing pkg %s version %s for language %s", pkgname, pkgversion, language)
    analyzer.logger.info("check history is %s", analyzer.CHECK_HISTORY)
    docker_client = docker.from_env()
    install_cmd = "python main.py install -n %s -l %s -c %s -o %s" % (
        pkgname, language, "/home/maloss/metadata", "/home/maloss/result")
    install_sudo_cmd = install_cmd + " -s"
    if pkgversion:
        install_cmd += " -v %s" % pkgversion
        install_sudo_cmd += " -v %s" % pkgversion

    # get container names
    install_name = get_container_name(pkgname=pkgname, pkgversion=pkgversion, job="i")
    install_sudo_name = get_container_name(pkgname=pkgname, pkgversion=pkgversion, job="i_sudo")

    # create output directories and change their permissions to nobody:nogroup
    metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language,
                                                pkgname=pkgname)
    # the docker arguments
    install_kwargs = {'name': install_name,
                      'volumes': {metadata_dir: {"bind": "/home/maloss/metadata", "mode": "rw"}},
                      'remove': True}
    install_sudo_kwargs = {'name': install_sudo_name,
                           'volumes': {metadata_dir: {"bind": "/home/maloss/metadata", "mode": "rw"}},
                           'remove': True}
    if analyzer.TRACING == 'Strace':
        # Step 1, get dependencies separately
        get_dep(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)

        # container caps for tracing using strace
        container_caps = ['SYS_PTRACE']
        install_cmd += " -t"
        install_sudo_cmd += " -t"
        result_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="RESULT_DIR", language=language,
                                                  pkgname=pkgname)
        install_kwargs['cap_add'] = container_caps
        install_kwargs['volumes'][result_dir] = {"bind": "/home/maloss/result", "mode": "rw"}
        install_sudo_kwargs['cap_add'] = container_caps
        install_sudo_kwargs['volumes'][result_dir] = {"bind": "/home/maloss/result", "mode": "rw"}
    elif analyzer.TRACING == 'Sysdig':
        analyzer.logger.info("no separate get_dep or container_caps for sysdig tracing, because sysdig sits in kernel")
    elif analyzer.TRACING is None:
        analyzer.logger.warning("TRACING utility not specified, not tracing now!")
    else:
        analyzer.logger.error("Unhandled TRACING utility: %s", analyzer.TRACING)
    # Step 2
    analyzer.logger.info("running install job for pkg %s, version %s language %s", pkgname, pkgversion, language)
    if analyzer.MEMORY_LIMIT is not None:
        install_kwargs['mem_limit'] = analyzer.MEMORY_LIMIT
    install_logs = docker_client.containers.run("malossscan/maloss", command=install_cmd, **install_kwargs)
    analyzer.logger.info("install job logs:\n%s", install_logs)
    # Step 3
    analyzer.logger.info("running sudo install job for pkg %s, version %s language %s", pkgname, pkgversion, language)
    if analyzer.MEMORY_LIMIT is not None:
        install_sudo_kwargs['mem_limit'] = analyzer.MEMORY_LIMIT
    install_sudo_logs = docker_client.containers.run("malossscan/maloss", command=install_sudo_cmd, **install_sudo_kwargs)
    analyzer.logger.info("sudo install job logs:\n%s", install_sudo_logs)


def stop_install(analyzer, pkgname, language, pkgversion=None):
    analyzer.logger.warning("stopping job install for pkg %s version %s for language %s", pkgname, pkgversion, language)
    docker_client = docker.from_env()
    install_containers = docker_client.containers.list(
        filters={'name': get_container_name_prefix(pkgname=pkgname, pkgversion=pkgversion)})
    for container in install_containers:
        try:
            container.stop(timeout=analyzer.DOCKER_TIMEOUT)
            container.remove()
        except Exception as re:
            analyzer.logger.error("failed to remove container %s: %s", container.name, re)


###########################################################
# Dynamic analysis
###########################################################
def dynamic_analysis(analyzer, pkgname, language, pkgversion=None, native=False):
    """
    Run dynamic analysis twice, with and without sudo permission. Only supports sysdig tracing!
    """
    analyzer.logger.info("analyzing pkg %s version %s for language %s", pkgname, pkgversion, language)
    analyzer.logger.info("check history is %s", analyzer.CHECK_HISTORY)
    docker_client = docker.from_env()
    dynamic_get_dep_cmd = "python main.py get_dep -n %s -l %s -c %s" % (pkgname, language, "/home/maloss/metadata")
    dynamic_cmd = "python main.py dynamic -n %s -l %s -c %s -o %s" % (
        pkgname, language, "/home/maloss/metadata", "/home/maloss/result")
    dynamic_sudo_cmd = dynamic_cmd + " -s"
    if pkgversion:
        dynamic_get_dep_cmd += " -v %s" % pkgversion
        dynamic_cmd += " -v %s" % pkgversion
        dynamic_sudo_cmd += " -v %s" % pkgversion

    # get container names
    dynamic_name = get_container_name(pkgname=pkgname, pkgversion=pkgversion, job="d")
    dynamic_sudo_name = get_container_name(pkgname=pkgname, pkgversion=pkgversion, job="d_sudo")

    # create output directories and change their permissions to nobody:nogroup
    metadata_dir = get_dir_for_language_pkgname(analyzer=analyzer, dirstr="METADATA_DIR", language=language,
                                                pkgname=pkgname)

    # the docker arguments
    dynamic_kwargs = {'name': dynamic_name,
                      'volumes': {metadata_dir: {"bind": "/home/maloss/metadata", "mode": "rw"}},
                      'remove': True}
    dynamic_sudo_kwargs = {'name': dynamic_sudo_name,
                           'volumes': {metadata_dir: {"bind": "/home/maloss/metadata", "mode": "rw"}},
                           'remove': True}

    if analyzer.TRACING == 'Strace':
        raise Exception("Strace support is deprecated!")
    elif analyzer.TRACING == 'Sysdig':
        # no caps needed for tracing, because sysdig sits in kernel
        analyzer.logger.info("no separate get_dep or container_caps for sysdig tracing, because sysdig sits in kernel")
    elif analyzer.TRACING is None:
        analyzer.logger.warning("TRACING utility not specified, not tracing now!")
    else:
        analyzer.logger.error("Unhandled TRACING utility: %s", analyzer.TRACING)

    # Run dynamic analysis
    analyzer.logger.info("running dynamic analysis job for pkg %s, version %s language %s", pkgname, pkgversion, language)

    if analyzer.MEMORY_LIMIT is not None:
        dynamic_kwargs['mem_limit'] = analyzer.MEMORY_LIMIT
    dynamic_logs = docker_client.containers.run("malossscan/maloss", command=dynamic_cmd, **dynamic_kwargs)
    analyzer.logger.info("dynamic analysis job logs:\n%s", dynamic_logs)

    # Run dynamic analysis with sudo permissions
    analyzer.logger.info("running sudo dynamic analysis job for pkg %s, version %s language %s", pkgname, pkgversion, language)

    if analyzer.MEMORY_LIMIT is not None:
        dynamic_sudo_kwargs['mem_limit'] = analyzer.MEMORY_LIMIT
    dynamic_sudo_logs = docker_client.containers.run("malossscan/maloss", command=dynamic_sudo_cmd, **dynamic_sudo_kwargs)
    analyzer.logger.info("sudo dynamic analysis job logs:\n%s", dynamic_sudo_logs)


def stop_dynamic_analysis(analyzer, pkgname, language, pkgversion=None):
    analyzer.logger.warning("stopping job dynamic analysis for pkg %s version %s for language %s", pkgname, pkgversion, language)
    docker_client = docker.from_env()
    dynamic_containers = docker_client.containers.list(
        filters={'name': get_container_name_prefix(pkgname=pkgname, pkgversion=pkgversion)})
    for container in dynamic_containers:
        try:
            container.stop(timeout=analyzer.DOCKER_TIMEOUT)
            container.remove()
        except Exception as re:
            analyzer.logger.error("failed to remove container %s: %s", container.name, re)


def run_analysis(analyzer, pkgfile, skipfile=None, native=False):
    # check if path exists
    if not exists(pkgfile):
        analyzer.logger.error("%s does not exist", pkgfile)
        exit(1)

    # load packages
    pkgs, with_version = get_pkg_list(pkgfile, skipfile=skipfile)
    if not pkgs:
        analyzer.logger.error("no packages loaded from %s", pkgfile)
        exit(1)

    # start analysis
    analyzer.logger.info("there are %d packages (with_version=%s) to be analyzed", len(pkgs), with_version)

    # if requested parallelism
    if analyzer.QUEUING and analyzer.QUEUING == 'Celery':
        from celery import group
        if analyzer.MODE == "Metadata":
            from celery_tasks import get_metadata_worker as analysis_worker
        elif analyzer.MODE == "Dependency":
            from celery_tasks import get_dep_worker as analysis_worker
        elif analyzer.MODE == "Compare":
            from celery_tasks import compare_worker as analysis_worker
        elif analyzer.MODE == "AstfilterLocal":
            from celery_tasks import astfilter_local_worker as analysis_worker
        elif analyzer.MODE == "TaintLocal":
            from celery_tasks import taint_local_worker as analysis_worker
        elif analyzer.MODE == "Install":
            from celery_tasks import install_worker as analysis_worker
        elif analyzer.MODE == "Dynamic":
            from celery_tasks import dynamic_worker as analysis_worker
        else:
            raise Exception("Unhandled mode: %s" % analyzer.MODE)
        if with_version:
            job = group(analysis_worker.s(pkgname=pname, language=lang, pkgversion=pver, native=native)
                        for pname, pver, lang in pkgs)
        else:
            job = group(analysis_worker.s(pkgname=pname, language=lang, pkgversion=None, native=native)
                        for pname, lang in pkgs)
        job.apply_async()
    else:
        progress = ProgressBar()
        for pkg_info in progress(pkgs):
            pkgversion = None
            if with_version:
                pkgname, pkgversion, language = pkg_info
            else:
                pkgname, language = pkg_info
            if analyzer.MODE == "Metadata":
                get_metadata(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
            elif analyzer.MODE == "Dependency":
                get_dep(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion, native=native)
            elif analyzer.MODE == "Compare":
                compare(analyzer=analyzer, pkgname=pkgname, language=language)
            elif analyzer.MODE == "AstfilterLocal":
                astfilter_local(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
            elif analyzer.MODE == "TaintLocal":
                taint_local(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
            elif analyzer.MODE == "Install":
                install(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion, native=native)
            elif analyzer.MODE == "Dynamic":
                dynamic_analysis(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion, native=native)
            else:
                raise Exception("Unhandled mode: %s" % analyzer.MODE)


def crawl_website(analyzer, url):
    # TODO: add implementation here
    raise Exception("Not implemented yet!")


def run_crawl(analyzer, urlfile, skipfile=None):
    # check if path exists
    if not exists(urlfile):
        analyzer.logger.error("%s does not exist", urlfile)
        exit(1)

    # load urls
    urls = [row['url'] for row in csv.DictReader(open(urlfile))]
    if skipfile and exists(skipfile):
        skip_urls = [row['url'] for row in csv.DictReader(open(skipfile))]
        urls = set(urls) - set(skip_urls)
    analyzer.logger.info("there are %d urls to be crawled", len(urls))

    # if requested parallelism
    if analyzer.QUEUING and analyzer.QUEUING == 'Celery':
        from celery import group
        from celery_tasks import crawl_website_worker
        job = group(crawl_website_worker.s(url=url) for url in urls)
        job.apply_async()
    else:
        progress = ProgressBar()
        for url in progress(urls):
            crawl_website(analyzer=analyzer, url=url)


###########################################################
# Celery config
###########################################################
def celery_check(analyzer):
    """
    Function to check if Celery workers are up and running.
    """
    try:
        from celery import Celery
        broker = analyzer.CELERY_BROKER_URL
        backend = analyzer.CELERY_RESULTS_BACKEND
        app = Celery('celery_tasks', broker=broker, backend=backend)
        app.config_from_object('celery_config')
        if not app.control.inspect().stats() and not app.control.inspect().ping():
            raise Exception("Start celery workers. None running.")
        return True

    except IOError as e:
        msg = "Error connecting to the backend: " + str(e)
        from errno import errorcode
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            raise Exception("Check that the RabbitMQ server is running.")

    except ImportError as e:
        raise Exception("Celery module not available. Please install")


class Analyzer(object):
    def __init__(self, mode, config_path='config'):
        self.MODE = mode
        self.DRY_RUN = None
        self.CELERY_BROKER_URL = None
        self.CELERY_RESULT_BACKEND = None

        # get configuration
        config = appconfig.Config(file_path=config_path)
        if not config:
            exit(1)
        self.config = config

        ###########################################################
        # Mode specific configuration
        ###########################################################
        # logging infrastructure for all modes
        self.LOGFILE_PREFIX = config.get("LOGFILE_PREFIX", mode)
        logger = None
        try:
            logger = applogger.Logger("Results", self.LOGFILE_PREFIX).get()
        except Exception as e:
            print("Error setting up 'Results' logger: %s" % (str(e)))
            exit(1)
        self.logger = logger
        self.FAILURE_FILE = config.get("FAILURE_FILE", mode)
        self.METADATA_DIR = os.environ.get("METADATA_DIR", config.get("METADATA_DIR", mode))
        self.RESULT_DIR = os.environ.get("RESULT_DIR", config.get("RESULT_DIR", mode))
        # for static
        val = config.get("USE_INTER_PROCEDURE", mode)
        self.USE_INTER_PROCEDURE = self.str2bool(val) if val else False
        val = config.get("USE_FLOW_TRACKING", mode)
        self.USE_FLOW_TRACKING = self.str2bool(val) if val else False
        val = config.get("USE_MULTI_LANGUAGE", mode)
        self.USE_MULTI_LANGUAGE = self.str2bool(val) if val else False
        # for dynamic
        val = config.get("USE_FUZZER", mode)
        self.USE_FUZZER = self.str2bool(val) if val else False

        ###########################################################
        # Infrastructure check
        ###########################################################
        self.TRACING = config.get("TRACING", "Infrastructure")
        self.QUEUING = config.get("QUEUING", "Infrastructure")

        ###########################################################
        # Algorithm config
        ###########################################################
        val = config.get("DRY_RUN", "Algorithm")
        self.DRY_RUN = self.str2bool(val) if val else False
        val = config.get("CHECK_HISTORY", "Algorithm")
        self.CHECK_HISTORY = self.str2bool(val) if val else False
        val = config.get("SKIP_MISSING_METADATA", "Algorithm")
        self.SKIP_MISSING_METADATA = self.str2bool(val) if val else False
        val = config.get("DETECT_STEALER", "Algorithm")
        self.DETECT_STEALER = self.str2bool(val) if val else False
        val = config.get("DETECT_BACKDOOR", "Algorithm")
        self.DETECT_BACKDOOR = self.str2bool(val) if val else False
        val = config.get("DETECT_SABOTAGE", "Algorithm")
        self.DETECT_SABOTAGE = self.str2bool(val) if val else False
        self.MEMORY_LIMIT = config.get("MEMORY_LIMIT", "Algorithm")
        val = config.get("SOFT_TIMEOUT", "Algorithm")
        self.SOFT_TIMEOUT = int(val) if val else 7200
        val = config.get("TIMEOUT", "Algorithm")
        self.TIMEOUT = int(val) if val else 7800
        val = config.get("DOCKER_TIMEOUT", "Algorithm")
        self.DOCKER_TIMEOUT = int(val) if val else 120

        ###########################################################
        # Check for tracing and parallelism
        ###########################################################
        if self.TRACING == "Sysdig":
            import psutil
            if self.QUEUING != "Celery" or "celery" in (p.name() for p in psutil.process_iter()):
                # check availability of sysdig in the system
                if "sysdig" not in (p.name() for p in psutil.process_iter()):
                    logger.error("Please start sysdig and retry!")
                    exit(1)
                # remove exited maloss containers in the system
                prune_containers(name="malossscan/maloss")
            logger.warning("Using Sysdig for tracing!")
        elif self.TRACING == "Strace":
            logger.warning("Using Strace for tracing!")
        elif self.TRACING is None:
            logger.warning("TRACING utility not specified, not tracing now!")
        else:
            logger.error("Please specify tracing utility, Strace or Sysdig, currently %s!", self.TRACING)
            exit(1)
        if not self.QUEUING:
            logger.warning("Non-parallel instance. May be slow!")
            return
        elif self.QUEUING == "Celery":
            logger.warning("Celery based parallel instance. Should be fast!")
        else:
            logger.error("Unsupported queuing protocol: %s", self.QUEUING)
            exit(1)

        # get broker url and backend config
        val = config.get("CELERY_BROKER_URL", "Celery")
        self.CELERY_BROKER_URL = val.strip() if val else 'amqp://'
        val = config.get("CELERY_RESULTS_BACKEND", "Celery")
        self.CELERY_RESULTS_BACKEND = val.strip() if val else 'rpc://'

        # if already a worker
        if mode == "Celery":
            return

        # check if celery workers are running
        try:
            celery_check(self)
        except Exception as e:
            logger.error("%s", str(e))
            exit(1)

    @staticmethod
    def str2bool(v):
        return v.lower() in ("yes", "true", "t", "1", "enabled")


###########################################################
# Main
###########################################################
if __name__ == "__main__":
    # parse args
    import sys
    import options
    opts = options.Options(sys.argv[1:])
    if not opts:
        exit(1)

    # get args
    mode, args = opts.argv()

    # create analyzer
    analyzer = Analyzer(mode=mode)
    if not analyzer:
        exit(1)
    if analyzer.MODE == "CrawlWebsite":
        run_crawl(analyzer=analyzer, urlfile=args[0], skipfile=args[1])
    elif analyzer.MODE == "Dependency":
        run_analysis(analyzer=analyzer, pkgfile=args[0], skipfile=args[1], native=args[2])
    else:
        run_analysis(analyzer=analyzer, pkgfile=args[0], skipfile=args[1])

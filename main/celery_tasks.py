from celery import Celery
from celery.signals import task_prerun
from celery.signals import after_setup_task_logger
from celery.exceptions import WorkerLostError, SoftTimeLimitExceeded
from os.path import exists, dirname
from detector import Analyzer, get_metadata, get_dep, compare, astfilter_local, taint_local, install, dynamic_analysis
from detector import stop_get_dep, stop_install, stop_dynamic_analysis, crawl_website


###########################################################
# init state
###########################################################
analyzer = Analyzer("Celery")
if not analyzer:
    print("Celery failed to init analyzer!")
    exit(1)

broker = analyzer.CELERY_BROKER_URL
backend = analyzer.CELERY_RESULTS_BACKEND
soft_time_limit = analyzer.SOFT_TIMEOUT
time_limit = analyzer.TIMEOUT
app = Celery('celery_tasks', broker=broker, backend=backend)
app.config_from_object('celery_config')  # use custom config file
logger = None


###########################################################
# Init
###########################################################
def init_task(**kwargs):
    if not analyzer:
        exit(1)


###########################################################
# Logger
###########################################################
def setup_logging(**kw):
    global logger
    logger = analyzer.logger
    logger.propagate = False


###########################################################
# TASK to crawl web content
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def crawl_website_worker(url):
    try:
        crawl_website(analyzer=analyzer, url=url)
    except WorkerLostError as wle:
        logger.error("crawl_website_worker: %s", str(wle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("crawl_website_worker: %s", str(stle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("crawl_website_worker: %s (type: %s)", str(e), type(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to get metadata and versions for packages
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def get_metadata_worker(pkgname, language, pkgversion=None, native=False):
    try:
        get_metadata(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
    except WorkerLostError as wle:
        logger.error("get_metadata_worker: %s", str(wle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("get_metadata_worker: %s", str(stle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("get_metadata_worker: %s (type: %s)", str(e), type(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to get metadata and dependency for packages
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def get_dep_worker(pkgname, language, pkgversion=None, native=False):
    try:
        get_dep(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion, native=native)
    except WorkerLostError as wle:
        logger.error("get_dep_worker: %s", str(wle))
        if not native:
            try:
                stop_get_dep(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
            except Exception as e:
                logger.error("fail to stop get_dep_worker for pkg %s language %s version %s: %s",
                             pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("get_dep_worker: %s", str(stle))
        if not native:
            try:
                stop_get_dep(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
            except Exception as e:
                logger.error("fail to stop get_dep_worker for pkg %s language %s version %s: %s",
                             pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("get_dep_worker: %s (type: %s)", str(e), type(e))
        if not native:
            try:
                stop_get_dep(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
            except Exception as e:
                logger.error("fail to stop get_dep_worker for pkg %s language %s version %s: %s",
                             pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to compare packages and/or their versions
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def compare_worker(pkgname, language, pkgversion=None, native=False):
    try:
        compare(analyzer=analyzer, pkgname=pkgname, language=language)
    except WorkerLostError as wle:
        logger.error("compare_worker: %s", str(wle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("compare_worker: %s", str(stle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("compare_worker: %s (type: %s)", str(e), type(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to run api analysis for packages
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def astfilter_local_worker(pkgname, language, pkgversion=None, native=False):
    try:
        astfilter_local(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
    except WorkerLostError as wle:
        logger.error("astfilter_local_worker: %s", str(wle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("astfilter_local_worker: %s", str(stle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("astfilter_local_worker: %s (type: %s)", str(e), type(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to run taint analysis for packages
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def taint_local_worker(pkgname, language, pkgversion=None, native=False):
    try:
        taint_local(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
    except WorkerLostError as wle:
        logger.error("taint_local_worker: %s", str(wle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("taint_local_worker: %s", str(stle))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("taint_local_worker: %s (type: %s)", str(e), type(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to install packages
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def install_worker(pkgname, language, pkgversion=None, native=False):
    try:
        install(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion, native=native)
    except WorkerLostError as wle:
        logger.error("install_worker: %s", str(wle))
        try:
            stop_install(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
        except Exception as e:
            logger.error("fail to stop install_worker for pkg %s language %s version %s: %s",
                         pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("install_worker: %s", str(stle))
        try:
            stop_install(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
        except Exception as e:
            logger.error("fail to stop install_worker for pkg %s language %s version %s: %s",
                         pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("install_worker: %s (type: %s)", str(e), type(e))
        try:
            stop_install(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
        except Exception as e:
            logger.error("fail to stop install_worker for pkg %s language %s version %s: %s",
                         pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


###########################################################
# TASK to analyze packages dynamically
###########################################################
@app.task(soft_time_limit=soft_time_limit, time_limit=time_limit, acks_late=False)
def dynamic_worker(pkgname, language, pkgversion=None, native=False):
    try:
        dynamic_analysis(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion, native=native)
    except WorkerLostError as wle:
        logger.error("dynamic_worker: %s", str(wle))
        try:
            stop_dynamic_analysis(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
        except Exception as e:
            logger.error("fail to stop dynamic_worker for pkg %s language %s version %s: %s",
                         pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except SoftTimeLimitExceeded as stle:
        logger.error("dynamic_worker: %s", str(stle))
        try:
            stop_dynamic_analysis(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
        except Exception as e:
            logger.error("fail to stop dynamic_worker for pkg %s language %s version %s: %s",
                         pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0
    except Exception as e:
        logger.error("dynamic_worker: %s (type: %s)", str(e), type(e))
        try:
            stop_dynamic_analysis(analyzer=analyzer, pkgname=pkgname, language=language, pkgversion=pkgversion)
        except Exception as e:
            logger.error("fail to stop dynamic_worker for pkg %s language %s version %s: %s",
                         pkgname, language, pkgversion, str(e))
        if analyzer.FAILURE_FILE and exists(dirname(analyzer.FAILURE_FILE)):
            open(analyzer.FAILURE_FILE, 'a').write(pkgname + '\n')
        return 0


# need to use registered instance for sender argument.
task_prerun.connect(init_task)
after_setup_task_logger.connect(setup_logging)


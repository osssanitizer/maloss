#!/usr/bin/python3
import os
import sys
import time
import docker
import shutil
import psutil
import socket
import argparse
import datetime
import dateutil.parser
import logger as applogger
from os.path import join, realpath, basename, dirname, exists, getmtime
from dotenv import load_dotenv
from crontab import CronTab
from subprocess import call
from multiprocessing import cpu_count

file_path = realpath(__file__)
dir_path = dirname(file_path)


def running_sysdig():
    return "sysdig" in (p.name() for p in psutil.process_iter())


def start_sysdig(logger=None):
    logger.info("starting sysdig!")
    sysdig_cmd = ['docker-compose', 'up', '-d']
    sysdig_path = join(dir_path, "../sysdig")
    try:
        call(sysdig_cmd, cwd=sysdig_path)
        logger.info("started sysdig")
    except Exception as re:
        logger.error("failed to start sysdig: %s", re)


def stop_sysdig(logger=None):
    logger.info("stopping sysdig!")
    sysdig_cmd = ['docker-compose', 'down']
    sysdig_path = join(dir_path, "../sysdig")
    try:
        new_env = os.environ.copy()
        new_env['COMPOSE_HTTP_TIMEOUT'] = str(600)
        call(sysdig_cmd, cwd=sysdig_path, env=new_env)
        logger.info("stopped sysdig")
    except Exception as re:
        logger.error("failed to stop sysdig: %s", re)


def wait_sysdig(max_retries=50, logger=None):
    # check availability of sysdig in the system
    retries = max_retries
    while retries > 0:
        # reload the module to get the updated process information
        # https://stackoverflow.com/questions/437589/how-do-i-unload-reload-a-python-module
        if not running_sysdig():
            logger.info("sysdig not started yet! waiting for it!")
            time.sleep(5)
            retries -= 1
        else:
            break
    if not running_sysdig():
        logger.error("failed to start sysdig!")
        raise Exception("Failed starting sysdig!")


def get_current_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect(("8.8.8.8", 80))
    return sock.getsockname()[0]


def save_sysdig_data(inactive_timeout=3600, logger=None):
    load_dotenv(dotenv_path=join(dir_path, "../sysdig/.env"))
    trace_dir = os.getenv("TRACEDIR")
    pm_data_dir = os.getenv("DATADIR")
    current_ip = get_current_ip()
    if not exists(pm_data_dir):
        os.makedirs(pm_data_dir)
    for fname in os.listdir(trace_dir):
        trace_fpath = join(trace_dir, fname)
        last_modified = getmtime(trace_fpath)
        if time.time() - last_modified > inactive_timeout:
            # Use IP as suffix to differentiate files from different hosts, to avoid conflict
            pm_fpath = join(pm_data_dir, '%s.%s' % (fname, current_ip))
            logger.info("moving inactive file %s to %s", trace_fpath, pm_fpath)
            shutil.move(trace_fpath, pm_fpath)
        else:
            logger.info("skipping active file %s", trace_fpath)
    # somehow sysdig stopped writing data to files
    return not(len(os.listdir(trace_dir)) == 0 and running_sysdig())


def container_stop_wrap(container):
    try:
        container.stop()
    except Exception:
        container.stop(timeout=600)


def remove_container(container, logger=None):
    if container.status == 'running':
        logger.warning("removing overtime container in running state: %s", container.name)
        try:
            container_stop_wrap(container=container)
            container.remove()
        except Exception as re:
            logger.error("failed to remove overtime container in running state: %s, Error: %s", container.name, re)
        logger.warning("removed overtime container in running state: %s", container.name)
        return True
    elif container.status in ('created', 'exited', 'restarting', 'paused'):
        logger.warning("removing overtime container in %s state: %s", container.status, container.name)
        try:
            container.remove()
        except Exception as ce:
            logger.error("failed to remove overtime container in running state: %s, Error: %s", container.name, ce)
        logger.warning("removed overtime container in %s state: %s", container.status, container.name)
        return True
    elif container.status in ('removing',):
        logger.warning("skipping overtime container in removing state: %s", container.name)
    elif container.status == 'dead':
        logger.error("something terrible happened, causing dead container %s!", container.name)
        return False
    else:
        raise Exception("Unexpected docker status {0}: {1}".format(container.status, container.name))


def stop_maloss(logger=None):
    logger.info("stopping maloss!")
    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"ancestor": "malossscan/maloss"}, all=True)
    for container in containers:
        remove_container(container=container, logger=logger)


def running_celery():
    return any("celery" in ' '.join(p.cmdline()) for p in psutil.process_iter())


def start_celery_worker(processes=-1, logger=None):
    # starts the celery workers
    logger.info("starting celery workers!")
    ts = time.strftime('%Y_%m_%d_%H_%M_%S')
    celery_start_cmd = ["python3", "-m", "celery", "worker", "--detach", "-A", "celery_tasks",
                        "--logfile=/tmp/celery_tasks_{0}.log".format(ts), "-c", str(processes)]
    call(celery_start_cmd, cwd=dir_path)
    logger.info("started celery workers!")


def stop_celery_worker(logger=None):
    logger.info("killing all celery processes")
    try:
        for p in psutil.process_iter():
            if "celery" in ' '.join(p.cmdline()):
                p.kill()
    except Exception as e:
        logger.error("failed to kill all celery processes: %s", e)
    logger.info("killed all celery processes")


def register_cleanup(processes, user, interval=-1, sysdig=False, logger=None):
    logger.info("registering cleanup cron job!")
    # Managing Cron Jobs Using Python
    # https://code.tutsplus.com/tutorials/managing-cron-jobs-using-python--cms-28231
    # Cleanup command needs sudo
    # https://superuser.com/questions/871704/why-does-root-cron-job-script-need-sudo-to-run-properly
    user_cron = CronTab(user=user)
    # cleanup containers 10 minutes before they timeout
    cleanup_cmd = "sudo python3 %s cleanup -p %d -t %d" % (file_path, processes,  7200)
    if sysdig:
        cleanup_cmd += " -s"
    for user_job in user_cron:
        logger.info("checking cron job %s", user_job)
        if user_job.is_enabled():
            if file_path in str(user_job):
                logger.info("cleanup cron job already registered! deleting it %s", user_job)
                user_job.delete()

    cleanup_job = user_cron.new(command=cleanup_cmd, comment="maloss cleanup job every {0} minutes".format(interval))
    cleanup_job.minute.every(interval)
    user_cron.write()
    logger.info("registered cleanup cron job!")


def remove_cleanup(user, logger=None):
    logger.info("removing cleanup cron job!")
    user_cron = CronTab(user=user)
    for user_job in user_cron:
        logger.info("checking cron job %s", user_job)
        if user_job.is_enabled():
            if file_path in str(user_job):
                logger.info("deleting cleanup cron job %s", user_job)
                user_job.delete()
    user_cron.write()
    logger.info("removed cleanup cron job!")


def start(processes, cleanup_user, cleanup_interval, sysdig=False, skip_register=False, logger=None):
    if sysdig and not running_sysdig():
        # need sysdig and sysdig is not started yet!
        start_sysdig(logger=logger)
        wait_sysdig(logger=logger)
    start_celery_worker(processes=processes, logger=logger)
    if not skip_register:
        register_cleanup(processes=processes, user=cleanup_user, interval=cleanup_interval, sysdig=sysdig, logger=logger)


def stop(user, sysdig=False, logger=None):
    # remove the cleanup script first to avoid conflict
    remove_cleanup(user=user, logger=logger)
    stop_celery_worker(logger=logger)
    if sysdig and running_sysdig():
        stop_sysdig(logger=logger)
    save_sysdig_data(inactive_timeout=-1, logger=logger)
    stop_maloss(logger=logger)


def restart(celery_processes, sysdig=False, logger=None):
    logger.info("restarting docker daemon")
    # kill all celery processes
    stop_celery_worker(logger=logger)

    # stop the docker daemon
    logger.info("stopping docker daemon")
    stop_cmd = ['service', 'docker', 'stop']
    call(stop_cmd)
    logger.info("stopped docker daemon")

    # remove all the docker container files
    logger.info("removing all docker container files")
    rm_cmd = ['rm', '-rf', '/var/lib/docker/containers/*']
    call(rm_cmd)
    logger.info("removed all docker container files")

    # remove the systemd dababase to allow docker restart
    logger.info("removing systemd database if exists")
    rm_cmd = ['rm', '/var/lib/systemd/catalog/database']
    call(rm_cmd)
    logger.info("removed systemd database if exists")

    # start the docker daemon
    logger.info("starting docker daemon")
    start_cmd = ['service', 'docker', 'start']
    call(start_cmd)
    logger.info("started docker daemon")
    time.sleep(60)

    # start the jobs without registering cleanup jobs
    if sysdig and not running_sysdig():
        start_sysdig(logger=logger)
        wait_sysdig(logger=logger)
    start_celery_worker(processes=celery_processes, logger=logger)


def cleanup(processes, timeout, sysdig=False, max_containers=-1, restart_containers=-1, logger=None):
    """
    There are three steps that we want to take to schedule the tasks
    """
    logger.info("starting cleanup job!")

    # Move the generated sysdig trace files to save space
    if not save_sysdig_data(logger=logger):
        logger.error("there is no sysdig output file, but sysdig is still running, triggering restart!")
        restart(celery_processes=processes, sysdig=sysdig, logger=logger)
        return

    # Set the docker containers threshold
    if not max_containers or max_containers <= 0:
        max_containers = cpu_count()
    if not restart_containers or restart_containers <= 0:
        restart_containers = cpu_count() * 3

    # If sysdig is still running, but celery is not, this is weird. Force restart.
    docker_client = docker.from_env()
    containers = docker_client.containers.list(filters={"ancestor": "malossscan/maloss"}, all=True)
    if sysdig and running_sysdig() and not running_celery():
        logger.info("inspecting existing docker containers for removal, due to stopped celery processes!")
    else:
        # Check if the number of containers has exceeded the limit
        if len(containers) < max_containers:
            logger.info("things look good so far.")
            return
        elif len(containers) >= restart_containers:
            logger.error("there are too many containers (%d), triggering restart!", len(containers))
            restart(celery_processes=processes, sysdig=sysdig, logger=logger)
            return
        else:
            logger.info("inspecting existing docker containers for removal!")

    # Identify the docker containers to be removed
    current = datetime.datetime.now(dateutil.tz.tzutc())
    for container in containers:
        # The timestamp is encoded
        # https://stackoverflow.com/questions/127803/how-do-i-parse-an-iso-8601-formatted-date
        created = dateutil.parser.parse(container.attrs['State']['StartedAt'])
        time_delta = (current - created).total_seconds()
        if time_delta <= timeout:
            logger.debug("container %s is healthy, skipping", container.name)
            continue
        logger.warning("inspecting overtime container %s", container)
        if not remove_container(container=container, logger=logger):
            logger.error("failed to remove container %s, triggering restart!", container.name)
            restart(celery_processes=processes, sysdig=sysdig, logger=logger)
            return

    # Recover from bad situations
    if (sysdig and not running_sysdig()) or (not running_celery()):
        start(processes=processes, cleanup_user=None, cleanup_interval=None, sysdig=sysdig, skip_register=True, logger=logger)


if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser(prog="scheduler", usage="usage: scheduler cmd args",
                                     description="Schedule the celery workers and cleanup jobs.")
    subparsers = parser.add_subparsers(help='Command (e.g. start)', dest='cmd')
    parser_start = subparsers.add_parser("start", help="Start the celery workers and register cleanup job")
    parser_start.add_argument("-p", "--processes", dest="processes", required=True, type=int,
                              help="Number of processes to spawn for celery workers, e.g. 7 for a 8-core machine")
    parser_start.add_argument("-u", "--user", dest="user", required=True, help="The user to install cron job for.")
    parser_start.add_argument("-i", "--interval", dest="interval", default=10, type=int,
                              help="Interval (minutes) of cleanup cron job, e.g. 10 minutes")
    parser_start.add_argument("-s", "--sysdig", dest="sysdig", action="store_true", help="With sysdig monitoring.")

    parser_cleanup = subparsers.add_parser("cleanup", help="Run the cleanup job")
    parser_cleanup.add_argument("-p", "--processes", dest="processes", required=True, type=int,
                                help="Number of processes to spawn for celery workers, e.g. 7 for a 8-core machine")
    parser_cleanup.add_argument("-t", "--timeout", dest="timeout", required=True, type=int,
                                help="Maximum life time (seconds) for running containers, e.g. 7200 seconds")
    parser_cleanup.add_argument("-c", "--max_containers", dest="max_containers", type=int,
                                help="Maximum number of containers allowed to co-exist, o.w. triggers the cleanup.")
    parser_cleanup.add_argument("-r", "--restart_containers", dest="restart_containers", type=int,
                                help="The number of containers that triggers restart of everything.")
    parser_cleanup.add_argument("-s", "--sysdig", dest="sysdig", action="store_true", help="With sysdig monitoring.")

    parser_stop = subparsers.add_parser("stop", help="Stop the analysis and remove cron job")
    parser_stop.add_argument("-u", "--user", dest="user", required=True, help="The user to remove cron job from.")
    parser_stop.add_argument("-s", "--sysdig", dest="sysdig", action="store_true", help="With sysdig monitoring.")
    args = parser.parse_args(sys.argv[1:])

    # initialize the logger
    logfile = "/tmp/maloss_scheduler.log"

    # call the jobs
    if args.cmd == "start":
        logger = applogger.Logger(name="Dump", path=logfile, mode="w").get()
        logger.info("running scheduler start")
        start(processes=args.processes, cleanup_user=args.user, cleanup_interval=args.interval,
              sysdig=args.sysdig, logger=logger)
    elif args.cmd == "cleanup":
        # initialize the logger
        logger = applogger.Logger(name="Dump", path=logfile, mode="a").get()
        logger.info("running scheduler cleanup")
        cleanup(processes=args.processes, timeout=args.timeout, max_containers=args.max_containers,
                restart_containers=args.restart_containers, sysdig=args.sysdig, logger=logger)
    elif args.cmd == "stop":
        # initialize the logger
        logger = applogger.Logger(name="Dump", path=logfile, mode="a").get()
        logger.info("running scheduler stop")
        stop(user=args.user, sysdig=args.sysdig, logger=logger)
    else:
        raise Exception("Unhandled job: {0}".format(args.cmd))

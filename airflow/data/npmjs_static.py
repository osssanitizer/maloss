import re
import pickle
import logging
import networkx

from airflow import DAG
from airflow.operators.bash_operator import BashOperator
from datetime import datetime, timedelta


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2019, 1, 1),
    'email': ['airflow@example.com'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
    # 'queue': 'bash_queue',
    # 'pool': 'backfill',
    'priority_weight': 10,
    # 'end_date': datetime(2016, 1, 1),
}

# don't auto-schedule the dag
# https://airflow.readthedocs.io/en/stable/scheduler.html
dag = DAG('npmjs_static', default_args=default_args, schedule_interval=None)
# periodically run the dag
# dag = DAG('tutorial', default_args=default_args, schedule_interval=timedelta(days=1))

# load dep_tree for packages, relative to AIRFLOW_HOME
npmjs_dep_path = "./dags/npmjs.with_stats.dep_graph.pickle"
dep_tree = pickle.load(open(npmjs_dep_path, "rb"))
logging.info("loaded dep_tree with %d nodes", dep_tree.number_of_nodes())


def get_sanitized_pkgname(pkg_name):
    invalid_name = re.compile(r'[^a-zA-Z0-9_.-]')
    pkg_name = re.sub(invalid_name, '..', pkg_name)
    return pkg_name


def get_bash_op(pkg_name, dag, configpath='/home/maloss/config/astgen_javascript_smt.config', cache_dir='/home/maloss/metadata', outdir='/home/maloss/result'):
    return BashOperator(
        task_id=get_sanitized_pkgname(pkg_name=pkg_name),
        execution_timeout=timedelta(hours=2),
        bash_command='cd /home/maloss/src/ && python main.py astfilter --ignore_dep_version -n %s -c %s -d %s -o %s -l javascript' % (pkg_name, configpath, cache_dir, outdir),
        dag=dag)


# all analysis jobs
# get all leaves
# https://networkx.github.io/documentation/latest/reference/algorithms/generated/networkx.algorithms.simple_paths.all_simple_paths.html
# leaves = (v for v, d in dep_tree.out_degree() if d == 0)
pkg2op = {}
for pkg in dep_tree.nodes():
    pkg = str(pkg)
    dep_pkgs = list(dep_tree.successors(pkg))
    logging.debug("%s has %d dep_pkgs", pkg, len(dep_pkgs))
    if not get_sanitized_pkgname(pkg_name=pkg):
        continue
    if pkg not in pkg2op:
        pkg2op[pkg] = get_bash_op(pkg_name=pkg, dag=dag)
    else:
        continue
    pkg_task = pkg2op[pkg]
    dep_tasks = set()
    for dep_pkg in dep_pkgs:
        dep_pkg = str(dep_pkg)
        # avoid cycles
        if dep_pkg == pkg or not get_sanitized_pkgname(pkg_name=dep_pkg):
            continue
        if dep_pkg not in pkg2op:
            pkg2op[dep_pkg] = get_bash_op(pkg_name=dep_pkg, dag=dag)
        dep_tasks.add(pkg2op[dep_pkg])
    # default trigger rule is all_success
    # use all_done instead
    pkg_task << list(dep_tasks)

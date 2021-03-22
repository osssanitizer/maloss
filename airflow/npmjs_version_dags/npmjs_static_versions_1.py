import re
import ast
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
dag = DAG('npmjs_static_versions_1', default_args=default_args, schedule_interval=None)
# periodically run the dag
# dag = DAG('tutorial', default_args=default_args, schedule_interval=timedelta(days=1))

# load dep_tree for packages, relative to AIRFLOW_HOME
npmjs_dep_path = "./dags/npmjs.with_stats.popular.versions.dep_graph_1.pickle"
dep_tree = pickle.load(open(npmjs_dep_path, "rb"))
logging.info("loaded dep_tree with %d nodes", dep_tree.number_of_nodes())


def get_sanitized_pkgname(pkg_name):
    invalid_name = re.compile(r'[^a-zA-Z0-9_.-]')
    pkg_name = re.sub(invalid_name, '..', pkg_name)
    return pkg_name


def invalid_dependency(pkg_name, pkg_version):
    return pkg_version.startswith(('http://', 'https://'))


def get_bash_op(pkg_name, pkg_version, dag, configpath='/home/maloss/config/astgen_javascript_smt.config', cache_dir='/home/maloss/metadata', outdir='/home/maloss/result'):
    return BashOperator(
        task_id='%s..%s' % (get_sanitized_pkgname(pkg_name=pkg_name), pkg_version),
        execution_timeout=timedelta(hours=2),
        bash_command='cd /home/maloss/src/ && python main.py astfilter -n %s -v %s -c %s -d %s -o %s -l javascript' % (pkg_name, pkg_version, configpath, cache_dir, outdir),
        dag=dag)


# all analysis jobs
# get all leaves
# https://networkx.github.io/documentation/latest/reference/algorithms/generated/networkx.algorithms.simple_paths.all_simple_paths.html
# leaves = (v for v, d in dep_tree.out_degree() if d == 0)
pkg2op = {}
for pkg_ver_id in dep_tree.nodes():
    pkg_ver_id = str(pkg_ver_id)
    pkg, ver = ast.literal_eval(pkg_ver_id)
    dep_pkg_ver_ids = list(dep_tree.successors(pkg_ver_id))
    logging.debug("%s has %d dep_pkgs", pkg, len(dep_pkg_ver_ids))
    # skip invalid packages
    if invalid_dependency(pkg_name=pkg, pkg_version=ver):
        logging.warning("skipping invalid pkg: %s %s", pkg, ver)
        continue
    if pkg_ver_id not in pkg2op:
        pkg2op[pkg_ver_id] = get_bash_op(pkg_name=pkg, pkg_version=ver, dag=dag)
    else:
        continue
    pkg_ver_task = pkg2op[pkg_ver_id]
    dep_pkg_ver_tasks = set()
    for dep_pkg_ver_id in dep_pkg_ver_ids:
        dep_pkg, dep_ver = ast.literal_eval(dep_pkg_ver_id)
        # skip invalid packages
        if invalid_dependency(pkg_name=dep_pkg, pkg_version=dep_ver):
            logging.warning("skipping invalid pkg: %s %s", dep_pkg, dep_ver)
            continue
        # avoid cycles
        if dep_pkg_ver_id == pkg_ver_id:
            continue
        if dep_pkg_ver_id not in pkg2op:
            pkg2op[dep_pkg_ver_id] = get_bash_op(pkg_name=dep_pkg, pkg_version=dep_ver, dag=dag)
        dep_pkg_ver_tasks.add(pkg2op[dep_pkg_ver_id])
    # default trigger rule is all_success
    # use all_done instead
    pkg_ver_task << list(dep_pkg_ver_tasks)



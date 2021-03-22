#!/bin/bash
if [ $# -eq 2 ]
then
    DAG_PATH=$1
    SCRIPT_PATH=$2
else
    echo "$0 DAG_PATH SCRIPT_PATH"
    exit 1
fi

# run the dag script
# ./test_dag.sh packagist_dags/ packagist_dags/packagist_static_0.py
# ./test_dag.sh maven_dags/ maven_dags/maven_static_0.py
# ./test_dag.sh npmjs_dags0/ npmjs_dags0/npmjs_static_0.py
# ./test_dag.sh npmjs_dags1/ npmjs_dags1/npmjs_static_20.py
# ./test_dag.sh npmjs_dags2/ npmjs_dags2/npmjs_static_40.py
# ./test_dag.sh npmjs_dags3/ npmjs_dags3/npmjs_static_60.py
# ./test_dag.sh pypi_dags/ pypi_dags/pypi_static_0.py 
# ./test_dag.sh rubygems_dags/ rubygems_dags/rubygems_static_0.py 
# ./test_dag.sh packagist_version_dags packagist_version_dags/packagist_static_versions_0.py
# ./test_dag.sh maven_version_dags0/ maven_version_dags0/maven_static_versions_0.py
# ./test_dag.sh maven_version_dags1/ maven_version_dags1/maven_static_versions_20.py
# ./test_dag.sh maven_version_dags2/ maven_version_dags2/maven_static_versions_40.py
# ./test_dag.sh maven_version_dags3/ maven_version_dags3/maven_static_versions_60.py
# ./test_dag.sh npmjs_version_dags npmjs_version_dags/npmjs_static_versions_0.py
# ./test_dag.sh pypi_version_dags pypi_version_dags/pypi_static_versions_0.py
# ./test_dag.sh rubygems_version_dags rubygems_version_dags/rubygems_static_versions_0.py

ln -s $DAG_PATH dags
python $SCRIPT_PATH
rm dags

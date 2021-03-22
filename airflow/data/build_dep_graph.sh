#!/bin/bash

cd ../../src/

# build the dep graph
# python main.py build_dep -c /data/maloss/info/python -l python ../data/pypi.with_stats.csv ../airflow/data/pypi.with_stats.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/javascript -l javascript ../data/npmjs.with_stats.csv ../airflow/data/npmjs.with_stats.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/ruby -l ruby ../data/rubygems.with_stats.csv ../airflow/data/rubygems.with_stats.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/php -l php ../data/packagist.with_stats.csv ../airflow/data/packagist.with_stats.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/java -l java ../data/maven.csv ../airflow/data/maven.dep_graph.pickle


# split the dep graph
# python main.py split_graph ../airflow/data/pypi.with_stats.dep_graph.pickle ../airflow/pypi_dags/ -d ../airflow/data/pypi_static.py -n 20
# python main.py split_graph ../airflow/data/npmjs.with_stats.dep_graph.pickle ../airflow/npmjs_dags/ -d ../airflow/data/npmjs_static.py -n 40
# python main.py split_graph ../airflow/data/npmjs.with_stats.dep_graph.pickle ../airflow/npmjs_dags/ -d ../airflow/data/npmjs_static.py -n 80 -k 4
# python main.py split_graph ../airflow/data/rubygems.with_stats.dep_graph.pickle ../airflow/rubygems_dags/ -d ../airflow/data/rubygems_static.py -n 20
# python main.py split_graph ../airflow/data/packagist.with_stats.dep_graph.pickle ../airflow/packagist_dags/ -d ../airflow/data/packagist_static.py -n 20
# python main.py split_graph ../airflow/data/maven.dep_graph.pickle ../airflow/maven_dags/ -d ../airflow/data/maven_static.py -n 20


# split the popular dep graph
# python main.py split_graph ../airflow/data/pypi.with_stats.dep_graph.pickle ../airflow/pypi_dags/ -d ../airflow/data/pypi_static.py -s ../data/pypi.with_stats.popular.csv
# python main.py split_graph ../airflow/data/npmjs.with_stats.dep_graph.pickle ../airflow/npmjs_dags/ -d ../airflow/data/npmjs_static.py -s ../data/npmjs.with_stats.popular.csv -k 4
# python main.py split_graph ../airflow/data/rubygems.with_stats.dep_graph.pickle ../airflow/rubygems_dags/ -d ../airflow/data/rubygems_static.py -s ../data/rubygems.with_stats.popular.csv
# python main.py split_graph ../airflow/data/packagist.with_stats.dep_graph.pickle ../airflow/packagist_dags/ -d ../airflow/data/packagist_static.py -s ../data/packagist.with_stats.popular.csv


# build the version dep graph
# python main.py build_dep -c /data/maloss/info/python -v -l python ../data/pypi.with_stats.popular.versions.csv ../airflow/data/pypi.with_stats.popular.versions.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/javascript -v -l javascript ../data/npmjs.with_stats.popular.versions.csv ../airflow/data/npmjs.with_stats.popular.versions.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/ruby -v -l ruby ../data/rubygems.with_stats.popular.versions.csv ../airflow/data/rubygems.with_stats.popular.versions.dep_graph.pickle
# python main.py build_dep -c /data/maloss/info/php -v -l php ../data/packagist.with_stats.popular.versions.csv ../airflow/data/packagist.with_stats.popular.versions.dep_graph.pickle


# split the version dep graph
python main.py split_graph ../airflow/data/pypi.with_stats.popular.versions.dep_graph.pickle ../airflow/pypi_version_dags/ -d ../airflow/data/pypi_static_versions.py -n 10
python main.py split_graph ../airflow/data/npmjs.with_stats.popular.versions.dep_graph.pickle ../airflow/npmjs_version_dags/ -d ../airflow/data/npmjs_static_versions.py -n 10
python main.py split_graph ../airflow/data/rubygems.with_stats.popular.versions.dep_graph.pickle ../airflow/rubygems_version_dags/ -d ../airflow/data/rubygems_static_versions.py -n 10
python main.py split_graph ../airflow/data/packagist.with_stats.popular.versions.dep_graph.pickle ../airflow/packagist_version_dags/ -d ../airflow/data/packagist_static_versions.py -n 10

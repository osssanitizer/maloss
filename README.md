# Table of Contents

* [Introduction](#introduction)
* [Prerequisite](#prerequisite)
    * [Basics](#basics)
    * [Dependencies](#dependencies)
* [Development](#development)
    * [Structure](#structure)
    * [Instructions](#instructions)
* [HowTo](#howto)
    * [select_pm](#select_pm)
    * [select_pkg](#select_pkg)
    * [crawl](#crawl)
    * [edit_dist](#edit_dist)
    * [download](#download)
    * [get_versions](#get_versions)
    * [get_author](#get_author)
    * [get_dep](#get_dep)
    * [get_stats](#get_stats)
    * [build_dep](#build_dep)
    * [build_author](#build_author)
    * [split_graph](#split_graph)
    * [install](#install)
    * [astgen](#astgen)
    * [astfilter](#astfilter)
    * [taint](#taint)
    * [filter_pkg](#filter_pkg)
    * [static](#static)
    * [dynamic](#dynamic)
    * [interpret_trace](#interpret_trace)
    * [interpret_result](#interpret_result)
    * [compare_ast](#compare_ast)
    * [filter_versions](#filter_versions)
    * [compare_hash](#compare_hash)
    * [grep_pkg](#grep_pkg)
    * [speedup](#speedup)
* [Tool](#tool)
    * [Internet-wide scanning](#internet-wide-scanning)
    * [Statistics for different package managers](#statistics-for-different-package-managers)
    * [Static analysis tools for different languages](#static-analysis-tools-for-different-languages)
    * [AST parsers for different languages](#ast-parsers-for-different-languages)
* [Resource](#resource)
* [Reference](#reference)


# Introduction #

This project analyzes open source projects for malware. 

Due to the high demand of the community, we decide to open source the code as it is now, to allow collaboration.
The majority of the code is updated until May 2019, which indicates that some components may *not* work any more.
Especially the components that depends on external tools (e.g. Sysdig, Airflow) or APIs (e.g. Npm). 

We are actively working on the testing and improvements. Please find the [todo list here](TODO.md). 
For how to run commands, please refer to [howto section](#howto). For how to deploy on machines, please refer to [deploy instructions](DEPLOY.md). For how to request access to the supply chain attack samples, please refer to [request instructions](malware/README.md)

This repository is open sourced under MIT license. If you find this repository helpful, please cite our paper:

```
@inproceedings{duan2021measuring,
  title={Towards Measuring Supply Chain Attacks on Package Managers for Interpreted Languages},
  author={Duan, Ruian and Alrawi, Omar and Kasturi, Ranjita Pai and Elder, Ryan and Saltaformaggio, Brendan and Lee, Wenke},
  booktitle = {28th Annual Network and Distributed System Security Symposium, {NDSS}},
  month     = Feb,
  year      = {2021},
  url       = {https://www.ndss-symposium.org/wp-content/uploads/ndss2021_1B-1_23055_paper.pdf}
}
```


# Prerequisite #

## Basics ##
- docker
    - [install docker](https://docs.docker.com/install/linux/docker-ce/ubuntu/)
- basic setup for ubuntu
    - `sudo ./setup.sh`
- for other OS (i.e. MacOS and Windows), please look at `setup.sh` and figure out their equivalencies

## Dependencies ##
- To test and run the project locally, you need dependencies. There are two ways to prepare dependencies
- build the maloss docker image and test inside it
    - build docker image
        - `sudo docker build -t maloss .`
    - re-build docker image without cache (used when re-building image)
        - `sudo docker build -t maloss . --no-cache`
    - run the docker image and map your local source root to it
        - `sudo docker run -it --rm -v $(pwd):/code maloss /bin/bash`
    - change to the mapped mounted source root and start making changes
        - `cd /code`
- install dependencies locally and test it
    - the instructions are for ubuntu 16.04. if you find them not working on other systems, please fix and commit the necessary changes. these instructions are simply copied from the Dockerfile, look into it for troubleshooting.
    - for js and python static analysis development
        - `pip install -r src/requirements.txt --user`
    - for the others (TODO: simplify this giant list)
        - `sudo apt-get install -yqq curl php git ruby-full rubygems-integration nuget python python-pip python3-pip npm jq strace`
        - `sudo ./src/install_dep.sh`


# Development #

## Structure ##
- *registries* folder contains source code for mirroring package managers. To run the program, you would need 10TB for Npm, 5TB for PyPI and 5TB for RubyGems.
- *src* folder contains source code for static, dynamic and metadata analysis.
- *main* folder contains source code for dynamic orchestration.
- *airflow* folder contains source code for static Orchestration.
- *sysdig* folder contains setup and config for dynamic tracing.
- *data* contains honeypot setup and statistics.
- *config* contains config for static analysis.
- *doc* contains manually labeled APIs which is used to derive *config*.
- *testdata* contains test samples.
- *ref* contains related work.
- *benignware* contains some benign packages.
- *malware* contains *the list* of malicious samples, which can be used for protection. 
- [*maloss-samples*](https://github.com/osssanitizer/maloss-samples) is a private repo that contains the supply chain attack samples and are updated periodically. Please fill out the [Google Form](https://forms.gle/MwsN6fydMRWL1j5V9) to request access. We will respond ASAP.

## Instructions ##
- In this project, we are currently using *celery* + *rabbitmq* to run our metadata and dynamic analyses in a distributed manner. we are using *airflow* + *celery* to run our static analyses.
    - The *src/* folder contains the code for each individual analyses and should be minimized and self-contained. 
        - In particular, for static/dynamic/metadata analysis, the jobs in *src/* folder should be handling only one package and one versoin.
        - Each individual analyses should be developed and contained in this folder.
    - The *main/* folder handles distributed computing for metadata and dynamic analyses.
        - The master node load the list of jobs (packages and their versions to analyze), send them to the rabbitmq broker.
        - The slave nodes connect to the broker and fetches jobs from broker.
        - Each individual analyses may need to change *.env* in this folder.
    - The *airflow/* folder handles distributed computing for static analyses.
        - The master node loads the DAG of jobs (packages connected by dependency relations), send them to the redis broker.
        - The slave nodes connect to te broker and fetches jobs from broker.
        - Each individual analyses may need to change *.env* in this folder.
- In this project, we run each analysis using docker. The following steps show how to start or debug the distributed jobs for metadata and dynamic analyses.
    - on worker
        - create customized `main/config` from `main/config.tmpl`
        - build docker image
            - `sudo docker build -t maloss .`
        - re-build docker image without cache (used when re-building image)
            - `sudo docker build -t maloss . --no-cache`
        - for testing, run docker image and attach to it
            - `sudo docker run -it --rm --cap-add=SYS_PTRACE -v /tmp/result:/home/maloss/result -v /tmp/metadata:/home/maloss/metadata maloss /bin/bash`
        - for production, refer to *DEPLOY.md*
    - on master
        - create customized `main/config` from `main/config.tmpl`
        - start rabbitmq
            - `cd main && sudo docker-compose --compatibility -f docker-compose-master.yml up -d`
        - add jobs to the queue
            - `python detector.py install -i ../data/pypi.csv`
    - debugging
        - comment out the `QUEUING = Celery` line in `main/config`, and then the jobs should be running locally and sequentially.
        - the entry point for celery works is `main/celery_tasks.py` and the entry point for master it `main/detector.py`.
- TODO: how to debug static analyses


# HowTo #

## select_pm ##
- select the package managers to inspect based on num_pkg threshold
    - `python main.py select_pm`
    
## select_pkg ##
- select popular packages based on specified criteria, such as downloads or uses
    - `python main.py select_pkg ../data/pypi.with_stats.csv ../data/pypi.with_stats.popular.csv -n 10000`
    - `python main.py select_pkg ../data/maven.csv ../data/maven.popular.csv -n 10000 -f use_count`
    
## crawl ##
- crawl the specified package manager and save the package names
    - `python main.py crawl $package_manager $outfile`
- crawl the specified package manager for package names, lookup download stats, and save to file
    - `python main.py crawl $package_manager $outfile -s -p 24`
    
## edit_dist ##
- run edit distance for package names
    - `python main.py edit_dist $source -t $target $outfile`
    - `python main.py edit_dist ../data/pypi.with_stats.csv ../data/edit_dist/pypi_edist_dist.out -a c_edit_distance_batch -p 16`
    - `python main.py edit_dist ../data/pypi.with_stats.popular.csv ../data/edit_dist/pypi_pop_vs_all.out -t ../data/pypi.with_stats.csv -a c_edit_distance_batch -p 16 --pair_outfile ../data/edit_dist/pypi_pop_vs_all.csv`

## download ##
- download tarball file using pip, [link](https://stackoverflow.com/questions/7300321/how-to-use-pythons-pip-to-download-and-keep-the-zipped-files-for-a-package)
    - `pip download --no-binary :all: --no-deps package`
- download tgz file using npm, [link](https://stackoverflow.com/questions/15035786/download-source-from-npm-without-npm-install-xxx)
    - `npm pack package`
- download php packages using composer
    - `composer require -d ../testdata/php --prefer-source --no-scripts package`
- download ruby packages using gem
    - `gem fetch package`
- download java packages using maven
    - `mvn dependency:get -Dartifact=com.google.protobuf:protobuf-java:3.5.1 -Dtransitive=false && cp ~/.m2/repository/com/google/protobuf/protobuf-java/3.5.1/protobuf-java-3.5.1.jar ./`

## get_versions ##
- run get_versions job to get major versions for list of packages
    - `python main.py get_versions ../data/pypi.with_stats.popular.csv ../data/pypi.with_stats.popular.versions.csv -l python -c /data/maloss/info/python`
    - `python main.py get_versions ../data/maven.popular.csv ../data/maven.popular.versions.csv -c /data/maloss/info/java -l java`
- run get_versions job to get all versions for list of packages
    - `python main.py get_versions ../data/2019.07/pypi.csv ../data/2019.07/pypi.versions.csv -c /data/maloss/info-2019.07/python -l python --max_num -1`
- run get_versions job to get all versions for list of packages and include their time as well
    - `python main.py get_versions ../data/2019.07/pypi.csv ../data/2019.07/pypi.versions.csv -c /data/maloss/info-2019.07/python -l python --max_num -1 --with_time`
- run get_versions job to get recent versions for list of packages
    - `python main.py get_versions ../data/2019.07/pypi.csv ../data/2019.07/pypi.versions.csv -c /data/maloss/info-2019.07/python -l python --max_num 100 --min_gap_days 1`

## get_author ##
- run get_author job to the author for list of packages
    - `python main.py get_author ../data/pypi.with_stats.popular.csv ../data/pypi.with_stats.with_author.popular.csv -l python -c /data/maloss/info/python`

## get_dep ##
- run get_dep job to list dependencies for python packages
    - `python main.py get_dep -l python -n protobuf -c ../testdata`
    - `python main.py get_dep -l python -n scrapy -c ../testdata`
- run get_dep job to list dependencies for javascript packages
    - `python main.py get_dep -l javascript -n eslint -c ../testdata`
- run get_dep job to list dependencies for ruby packages
    - `python main.py get_dep -l ruby -n protobuf -c ../testdata`
- run get_dep job to list dependencies for php packages
    - `python main.py get_dep -l php -n designsecurity/progpilot -c ../testdata`
- run get_dep job to list dependencies for java packages
    - `python main.py get_dep -l java -n com.google.protobuf/protobuf-java -c ../testdata`

## get_stats ##
- get the stats for specified packages
    - `python main.py get_stats ../malware/npmjs-mal-pkgs.june2019.txt ../malware/npmjs-mal-pkgs.june2019.with_stats.txt.new -m npmjs`
- get the stats for specified packages
    - `python main.py get_stats ../malware/pypi-mal-pkgs.txt ../malware/pypi-mal-pkgs.with_stats.txt -m pypi

## build_dep ##
- build the dependency graph
    - `python main.py build_dep -c /data/maloss/info/python -l python ../data/pypi.with_stats.csv ../airflow/data/pypi.with_stats.dep_graph.pickle`
- build the dependency graph with versions (the *--record_version* option)
    - `python main.py build_dep -c /data/maloss/info/python -v -l python ../data/pypi.with_stats.popular.versions.csv ../airflow/data/pypi.with_stats.popular.versions.dep_graph.pickle`

## build_author ##
- build the author package graph for popular packages in pypi/npmjs/rubygems/packagist
    - `python main.py build_author ../data/author_pkg_graph.popular.pickle -i ../data/pypi.with_stats.with_author.popular.csv ../data/npmjs.with_stats.with_author.popular.csv ../data/rubygems.with_stats.with_author.popular.csv ../data/packagist.with_stats.with_author.popular.csv -l python javascript ruby php -t ../data/top_authors.popular.json`
- build the author package graph for all packages in  pypi/npmjs/rubygems/packagist/maven
    - `python main.py build_author ../data/author_pkg_graph.pickle -i ../data/pypi.with_stats.with_author.csv ../data/npmjs.with_stats.with_author.csv ../data/rubygems.with_stats.with_author.csv ../data/packagist.with_stats.with_author.csv ../data/maven.with_author.csv -l python javascript ruby php java -t ../data/top_authors.json`

## split_graph ##
- split the dependency graph
    - unzip the pickle files first
        - `tar -zxf ../airflow/data/pypi.with_stats.dep_graph.pickle.tgz`
    - split into N copies
        - `python main.py split_graph ../airflow/data/pypi.with_stats.dep_graph.pickle ../airflow/pypi_dags/ -d ../airflow/data/pypi_static.py -n 20`
        - `python main.py split_graph ../airflow/data/pypi.with_stats.popular.versions.dep_graph.pickle ../airflow/pypi_version_dags/ -d ../airflow/data/pypi_static_versions.py -n 10`
        - `python main.py split_graph ../airflow/data/maven.dep_graph.pickle ../airflow/maven_dags/ -d ../airflow/data/maven_static.py -n 20`
    - split into N copies and K folders
        - `python main.py split_graph ../airflow/data/maven.popular.versions.dep_graph.pickle.tgz ../airflow/maven_version_dags/ -d ../airflow/data/maven_static_versions.py -n 80 -k 4`
    - split out the subgraph that contains seed nodes
        - `python main.py split_graph ../airflow/data/pypi.with_stats.dep_graph.pickle ../airflow/pypi_dags/ -d ../airflow/data/pypi_static.py -s ../data/pypi.with_stats.popular.csv`

## install ##
- run install job to install python packages and capture traces
    - `python main.py install -n protobuf -l python -c ../testdata -o ../testdata`
- run install job to install javascript packages and capture traces
    - `python main.py install -n eslint -l javascript -c ../testdata -o ../testdata`
- run install job to install ruby packages and capture traces
    - `python main.py install -n protobuf -l ruby -c ../testdata -o ../testdata`
- run install job to install php packages and capture traces
    - `python main.py install -n designsecurity/progpilot -l php -c ../testdata -o ../testdata`
- run install job to install java packages and capture traces
    - `python main.py install -n com.google.protobuf/protobuf-java -l java -c ../testdata -o ../testdata`

## astgen ##
- run astgen job to compute ast for python and python3 packages
    - `python main.py astgen ../testdata/test-eval-exec.py ../testdata/test-eval-exec.py.out -c ../config/test_astgen_python.config`
    - `python main.py astgen ../testdata/html5lib-1.0.1.tar.gz ../testdata/html5lib-1.0.1.tar.gz.out -c ../config/test_astgen_python.config`
    - `python main.py astgen ../testdata/python-taint-0.40.tar.gz ../testdata/python-taint-0.40.tar.gz.out -c ../config/test_astgen_python.config`
- run astgen job to compute ast for javascript packages
    - `python main.py astgen ../testdata/test-eval.js ../testdata/test-eval.js.out -c ../config/test_astgen_javascript.config -l javascript`
    - `python main.py astgen ../testdata/urlgrey-0.4.4.tgz ../testdata/urlgrey-0.4.4.tgz.out -c ../config/test_astgen_javascript.config -l javascript`
- run astgen job to compute ast for php packages
    - `cd static_proxy && php astgen.php -c ../../config/test_astgen_php.config.bin -i ../../testdata/test-eval-exec.php -o ../../testdata/test-eval-exec.php.out.bin && cd ..`
    - `python main.py astgen ../testdata/test-eval-exec.php ../testdata/test-eval-exec.php.out -c ../config/test_astgen_php.config -l php`
    - `python main.py astgen ../testdata/test-backtick.php ../testdata/test-backtick.php.out -c ../config/test_astgen_php.config -l php`
    - `python main.py astgen ../testdata/php/vendor/guzzlehttp/guzzle/ ../testdata/guzzlehttp_guzzle.out -c ../config/test_astgen_php.config -l php`
- run astgen job to compute ast for ruby packages
    - `cd static_proxy && ruby astgen.rb -c ../../config/test_astgen_ruby.config.bin -i ../../testdata/test-eval.rb -o ../../testdata/test-eval.rb.out.bin && cd ..`
    - `python main.py astgen ../testdata/test-eval.rb ../testdata/test-eval.rb.out -c ../config/test_astgen_ruby.config -l ruby`
- run astgen job to compute ast for java packages
    - `cd static_proxy/astgen-java && java -jar target/astgen-java-1.0.0-jar-with-dependencies.jar -help && cd ../../`
    - `cd static_proxy/astgen-java && java -jar target/astgen-java-1.0.0-jar-with-dependencies.jar -inpath ../../../testdata/Test.jar -outfile ../../../testdata/Test.jar.out -intype JAR -config ../../../config/astgen_java_smt.config -process_dir ../../../testdata/Test.jar && cd ../../`
    - `python main.py astgen ../testdata/protobuf-java-3.5.1.jar ../testdata/protobuf-java-3.5.1.jar.out -c ../config/test_astgen_java.config -l java`
    - `python main.py astgen ../testdata/Test.jar ../testdata/Test.jar.out -c ../config/astgen_java_smt.config -l java`

## astfilter ##
- use the configs titled `../config/astgen_XXX_smt.config` for each language (e.g. `../config/astgen_javascript_smt.config`) in astfilter job
- run astfilter job to evaluate api usage for python/pypi package and its dependent packages
    - `python main.py astfilter -n protobuf -c $python_config -d ../testdata/ -o ../testdata/`
- run astfilter job to evaluate api usage for javascript/npmjs package and its dependent packages
    - `python main.py astfilter -n eslint-scope -c $javascript_config -d ../testdata/ -o ../testdata/ -l javascript`
- run astfilter job to evaluate api usage for php/packagist package and its dependent packages
    - `python main.py astfilter -n designsecurity/progpilot -c $php_config -d ../testdata/ -o ../testdata/ -l php`
- run astfilter job to evaluate api usage for ruby/rubygems package and its dependent packages
    - `python main.py astfilter -n protobuf -c $ruby_config -d ../testdata/ -o ../testdata -l ruby`
- run astfilter job to evaluate api usage for java/maven package and its dependent packages
    - `python main.py astfilter -n com.google.protobuf/protobuf-java -c $java_config -d ../testdata/ -o ../testdata -l java`

## taint ##
- run taint analysis for specific packages
    - `python main.py taint -n json -d /data/maloss/info/ruby -o /data/maloss/result/ruby -l ruby -c ../config/astgen_ruby_smt.config`
- run taint analysis for specific packages and ignore their dependencies
    - `python main.py taint -n urllib -i ../malware/pypi-samples/urllib-1.21.1.tgz -d /data/maloss/info/python -o ./ -l python -c ../config/astgen_python_smt.config`
    - `python main.py taint -n django-server -i ../malware/pypi-samples/django-server-0.1.2.tgz -d /data/maloss/info/python -o ./ -l python -c ../config/astgen_python_smt.config`
    - `pip download --no-binary :all: --no-deps trustme && python main.py taint -n trustme -i trustme-0.5.1.tar.gz -d /data/maloss/info/python -o ./ -l python -c ../config/astgen_python_smt.config`
    - `python main.py taint -n eslint-scope -i ../malware/npmjs-samples/eslint-scope-3.7.2.tgz -d /data/maloss/info/javascript -o ./ -l javascript -c ../config/astgen_javascript_smt.config`
    - `python main.py taint -n custom8 -i static_proxy/jsprime/jsprimetests/custom8.js -d /data/maloss/info/javascript -o ./ -l javascript -c ../config/astgen_javascript_smt.config`
    - `python main.py taint -n stream-combine -i ../malware/npmjs-samples/stream-combine-2.0.2.tgz -d /data/maloss/info/javascript -o ./ -l javascript -c ../config/astgen_javascript_smt.config`
    - `python main.py taint -n test-eval-exec -i ../testdata/test-eval-exec.php -d /data/maloss/info/php -o ./ -l php -c ../config/astgen_php_smt.config`
    - `python main.py taint -n test-multiple-flows -i static_proxy/progpilot/projects/tests/tests/flows/ -d /data/maloss/info/php -o ./ -l php -c ../config/astgen_php_smt.config`
    - `python main.py taint -n test-flow -i ../testdata/test-flow.php -d /data/maloss/info/php -o ./ -l php -c ../config/astgen_php_smt.config`
- run taint analysis for specific input file
    - `python main.py taint -n active-support -l ruby -c ../config/astgen_ruby_smt.config -i ../malware/rubygems-samples/active-support-5.2.0.gem -o ./`
    - `python main.py taint -n bootstrap-sass -l ruby -c ../config/astgen_ruby_smt.config -i ../malware/rubygems-samples/bootstrap-sass-3.2.0.3.gem -o ./`
    - `python main.py taint -n brakeman-rails4 -l ruby -c ../config/astgen_ruby_smt.config -i ../testdata/rails4/ -o ./`

## filter_pkg ##
- filter packages based on the api usage or flow presence
    - `python main.py filter_pkg ../data/pypi.with_stats.csv ../data/pypi.with_stats.with_taint_apis.csv -c ../config/astgen_python_taint_apis.config -o /data/maloss/result/python -d /data/maloss/info/python -l python`
    - `python main.py filter_pkg ../data/rubygems.with_stats.csv ../data/rubygems.with_stats.with_taint_apis.csv -c ../config/astgen_ruby_taint_apis.config -o /data/maloss/result/ruby -d /data/maloss/info/ruby -l ruby`
    - `python main.py filter_pkg ../data/npmjs.with_stats.csv ../data/npmjs.with_stats.with_taint_apis.csv -c ../config/astgen_javascript_taint_apis.config -o /data/maloss/result/javascript -d /data/maloss/info/javascript -l javascript`
    - `python main.py filter_pkg ../data/packagist.with_stats.csv ../data/packagist.with_stats.with_taint_apis.csv -c ../config/astgen_php_taint_apis.config -o /data/maloss/result/php -d /data/maloss/info/php -l php`
    - `python main.py filter_pkg ../data/maven.csv ../data/maven.with_taint_apis.csv -c ../config/astgen_java_taint_apis.config -o /data/maloss/result/java -d /data/maloss/info/java -l java`

## static ##
- run static job to perform astfilter, taint and danger analysis for python and python3 packages
    - `python main.py static -n protobuf -c $python_config -d ../testdata/ -o ../testdata/`

## dynamic ##
- run dynamic job to install, main and exercise python packages and capture traces
    - `python main.py dynamic -n protobuf -l python -c ../testdata -o ../testdata`

## interpret_trace ##
- run interpret trace job to parse dynamic traces and dump them into per pkg/version protobuf output files
    - NOTE: sudo is needed for starting falco to parse traces
    - `sudo python main.py interpret_trace -l python --trace_dir /data/maloss1/sysdig/pypi -c /data/maloss/info/python -o /data/maloss/result/python -p 8`

## compare_ast ##
- compare the ast of specified input files and packages for permissions, apis etc.
    - `python main.py compare_ast -i ../malware/npmjs-samples/flatmap-stream-0.1.1.tgz ../benignware/npmjs-samples/flatmap-stream-0.1.0.tgz -o ../testdata/ ../testdata/flatmap-stream.json -l javascript -c ../config/astgen_javascript_smt.config`
    - `python main.py compare_ast -i ../testdata/test-backtick.php ../testdata/test-eval-exec.php -o tempout/ tempout/test_eval_backtick.json -l php -c ../config/astgen_php_smt.config`
    - `python main.py compare_ast -i ../malware/rubygems-samples/bootstrap-sass-3.2.0.3.gem ../benignware/rubygems-samples/bootstrap-sass-3.2.0.2.gem -l ruby -c ../config/astgen_ruby_smt.config -o ../testdata/  --outfile ../testdata/bootstrap-sass-compare.txt`
    - `python main.py compare_ast -i ../malware/rubygems-samples/active-support-5.2.0.gem ../benignware/rubygems-samples/activesupport-5.2.3.gem -c ../config/astgen_ruby_smt.config -o ../testdata/ --outfile ../testdata/activesupport-compare.txt -l ruby`

## filter_versions ##
- filter package versions based on compare_ast results, to allow further analysis such as taint analysis
    - `python main.py filter_versions ../data/2019.07/packagist.versions.with_time.csv ../data/2019.07/packagist_ast_stats.apis.json ../data/2019.07/packagist.versions.with_time.filtered_loose_apis.csv`

## compare_hash ##
- compare the hash value of same package versions across different package managers
    - `python main.py compare_hash -i ../data/maven.csv ../data/jcenter.csv -d /data/maloss/info/java /data/maloss/info/jcenter -o ../data/maven_jcenter.json`
    - `python main.py compare_hash -i ../data/jitpack.csv ../data/jcenter.csv -d /data/maloss/info/jitpack /data/maloss/info/jcenter -o ../data/jitpack_jcenter.json`
- compare the hash value of same package versions and their content hashs or api permissions across different package managers
    - `python main.py compare_hash -i ../data/jitpack.csv ../data/jcenter.csv -d /data/maloss/info/jitpack /data/maloss/info/jcenter -o ../data/jitpack_jcenter_filtered.json --inspect_content`
    - `python main.py compare_hash -i ../data/jitpack.csv ../data/jcenter.csv -d /data/maloss/info/jitpack /data/maloss/info/jcenter -o ../data/jitpack_jcenter_filtered.json --inspect_api -c ../config/astgen_java_smt.config`
    - `python main.py compare_hash -i ../data/jitpack.csv ../data/jcenter.csv -d /data/maloss/info/jitpack /data/maloss/info/jcenter -o ../data/jitpack_jcenter_filtered_api.json --inspect_api -c ../config/astgen_java_smt.config --compare_hash_cache ../data/jitpack_jcenter_filtered.json` 

## interpret_result ##
- collect and plot api stats
    - `python main.py interpret_result --data_type api -c /data/maloss/info/python -o /data/maloss/result/python -l python ../data/2019.01/pypi.with_stats.csv ../data/pypi_api_stats.json`
    - `python main.py interpret_result --data_type api -c /data/maloss/info/python -o /data/maloss/result/python -l python ../data/2019.01/pypi.with_stats.popular.csv ../data/pypi_pop_api_stats.json`
    - `python main.py interpret_result --data_type api -c /data/maloss/info/python -o /data/maloss/result/python -l python ../data/2019.01/pypi.with_stats.csv ../data/pypi_api_mapping.json -d --detail_filename`
- collect and plot domain stats
    - `python main.py interpret_result --data_type domain -c /data/maloss/info/python -o /data/maloss/result/python -l python ../data/2019.06/pypi.csv ../data/2019.06/pypi_domain_stats.json`
    - `python main.py interpret_result --data_type domain -c /data/maloss/info/python -o /data/maloss/result/python -l python ../data/2019.06/pypi.csv ../data/2019.06/pypi_domain_mapping.json -d`
- collect the pre-generated dependency stats
    - `python main.py interpret_result --data_type dependency -l python ../data/pypi.with_stats.popular.csv ../data/pypi_pop_dep_stats.json`
- collect the cross version comparison results, can filter by permissions, apis etc.
    - `python main.py interpret_result --data_type compare_ast -c /data/maloss/info/python -o /data/maloss/result/python -l python ../data/2019.06/pypi.with_stats.popular.csv ../data/2019.06/pypi_compare_ast_stats.json`
    - `python main.py interpret_result --data_type compare_ast -c /data/maloss/info-2019.07/javascript -o /data/maloss/result-2019.07/javascript -l javascript ../data/2019.07/npmjs.csv ../data/2019.07/npmjs_ast_stats.json --compare_ast_options_file ../data/2019.07/compare_ast_options.json`
- collect metadata/static/dynamic results and dump suspicious packages
    - `python main.py interpret_result --data_type install_with_network -c /data/maloss/info/javascript -o /data/maloss/result/javascript -l javascript -m npmjs ../data/2019.06/npmjs.csv ../data/2019.06/npmjs.install_with_network.json`
- collect the reverse dependency results
    - `python main.py interpret_result --data_type reverse_dep -l javascript -m npmjs ../airflow/data/high_impact.csv ../airflow/data/high_impact_npmjs.json`
    - `python main.py interpret_result --data_type reverse_dep -l python -m pypi ../airflow/data/high_impact.csv ../airflow/data/high_impact_pypi.json`
    - `python main.py interpret_result --data_type reverse_dep -l ruby -m rubygems ../airflow/data/high_impact.csv ../airflow/data/high_impact_rubygems.json`
- collect metadata/static/compare_ast results and dump suspicious packages
    - `python main.py interpret_result --data_type correlate_info_api_compare_ast -c /data/maloss/info-2019.07/javascript -o /data/maloss/result-2019.07/javascript -l javascript -m npmjs -s ../data/2019.07/npmjs_skip_list.json ../data/2019.07/npmjs_ast_stats.json ../data/2019.07/npmjs_correlate_info_api_compare_ast.json`
    - `python main.py interpret_result --data_type correlate_info_api_compare_ast -c /data/maloss/info-2019.07/php -o /data/maloss/result-2019.07/php -l php -m packagist -s ../data/2019.07/packagist_skip_list.json ../data/2019.07/packagist_ast_stats.json ../data/2019.07/packagist_correlate_info_api_compare_ast.json`
    - `python main.py interpret_result --data_type taint -c /data/maloss/info-2019.07/php -o /data/maloss/result-2019.07/php -l php ../data/2019.07/packagist.csv ../data/2019.07/packagist_flow_stats.json`

## grep_pkg ##
- grep through packages
    - `python main.py grep_pkg ../data/2019.07/rubygems.csv ../data/2019.07/rubygems.csv.pastebin.com pastebin.com -l ruby -p 80`
    - `python main.py grep_pkg ../data/2019.07/npmjs.csv ../data/2019.07/npmjs.csv.pastebin.com pastebin.com -l javascript -p 20`

## speedup ##
- measure the speedup benefits from summaries
    - `python main.py speedup ../data/2019.01/pypi.with_stats.popular.csv speedup.log -l python`


# Tool #

## Internet-wide scanning ##
- [Shodan](https://www.shodan.io)
- [Censys](https://censys.io)
    
## Statistics for different package managers ##
- [PyPi stats](https://github.com/ofek/pypinfo)
- [PyPi stats of packages](https://pypistats.org/packages/colourama)
- [NpmJS stats](https://github.com/pvorb/npm-stat.com)
    - [npm-pack-dependents](https://github.com/IonicaBizau/npm-pack-dependents/blob/master/lib/index.js)
- [RubyGems stats](https://rubygems.org/stats)
    - [Unofficial portal for RubyGems downloads](http://bestgems.org/gems/active-support)
- [Nuget stats](https://www.nuget.org/stats)
- [Packagist stats](https://github.com/GrahamCampbell/Packagist-Stats)
    - [Packagist sumary](https://packagist.org/statistics)
- [Maven stats (used by other packages)](https://mvnrepository.com/)
    - [Maven quick stats](https://search.maven.org/stats)

## Static analysis tools for different languages ##
- List summary
    - [13 tools for checking the security risk of open-source dependencies](https://techbeacon.com/13-tools-checking-security-risk-open-source-dependencies-0)
    - [Awesome Malware Analysis: a curated list of awesome malware analysis tools and resources](https://github.com/rshipp/awesome-malware-analysis)
    - [A curated list of linters, code quality checkers, and other static analysis tools for various programming languages](https://github.com/mre/awesome-static-analysis)
    - [PMD: An extensible cross-language static code analyzer. https://pmd.github.io](https://github.com/pmd/pmd)
        - [PMD doesn't support inter-procedural analysis now](https://github.com/pmd/pmd/wiki/Project-Ideas-%5BInception%5D#data-flow-analysis-and-control-flow-graph)
        - [Custom security ruleset for the popular Java static analysis tool PMD.](https://github.com/GDSSecurity/GDS-PMD-Security-Rules)
- Python 
    - [A Static Analysis Tool for Detecting Security Vulnerabilities in Python Web Applications](https://github.com/python-security/pyt)
    - [Bandit is a tool designed to find common security issues in Python code](https://github.com/PyCQA/bandit)
- Php
    - [A reviewed list of useful PHP static analysis tools](https://github.com/exakat/php-static-analysis-tools)
    - [Detect potentially malicious PHP files](https://github.com/nbs-system/php-malware-finder)
    - [Taint Analysis for PHP](https://github.com/olivo/TaintPHP)
    - [Phpcs security audit](https://github.com/FloeDesignTechnologies/phpcs-security-audit)
        - [Php Code Sniffer](https://github.com/squizlabs/PHP_CodeSniffer)
    - [A static analysis tool for security](https://github.com/designsecurity/progpilot)
        - [API and documentation for progpilot](https://github.com/designsecurity/progpilot/blob/master/docs/API.md)
        - [PHP Global Variables - Superglobals](https://www.w3schools.com/php/php_superglobals.asp)
    - [Taint is a PHP extension, used for dynamically detecting XSS codes](https://github.com/laruence/taint)
- Ruby
    - [Check for Ruby security problems](https://github.com/rubysec/bundler-audit)
    - [Locking Ruby in the Safe](http://phrogz.net/programmingruby/taint.html)
    - [A static analysis security vulnerability scanner for Ruby on Rails applications](https://brakemanscanner.org/), [github](https://github.com/presidentbeef/brakeman)
        - [Brakeman Pro is the best way to investigate security posture of Ruby on Rails application code.](https://brakemanpro.com/features)
    - [Dawn is a static analysis security scanner for ruby written web applications. It supports Sinatra, Padrino and Ruby on Rails frameworks.](https://github.com/thesp0nge/dawnscanner)
    - [Quality is a tool that runs quality checks on your code using community tools](https://github.com/apiology/quality)
- NpmJS
    - [6 Tools to Scan Node.js Application for Security Vulnerability](https://geekflare.com/nodejs-security-scanner/)
    - [node security platform command-line tool https://nodesecurity.io](https://github.com/nodesecurity/nsp)
    - [a javascript static security analysis tool](http://dpnishant.github.io/jsprime/)
        - [Blackhat 2013 talk for jsprime](https://www.slideshare.net/nishantdp/jsprime-bhusa13new)
    - [JSHint is a tool that helps to detect errors and potential problems in your JavaScript code](https://github.com/jshint/jshint)
    - [A First Look at Firefox OS Security](https://arxiv.org/pdf/1410.7754.pdf)
        - WALA is slow
        - JSPrime is also capable of performing dataflow analysis, but the architecture is extremely difficult to extend.
        - ScanJS, written in-house by Mozilla, is closest in spirit to our own.
    - [NodeJsScan is a static security code scanner for Node.js applications.](https://github.com/ajinabraham/NodeJsScan)
    - [FLOW IS A STATIC TYPE CHECKER FOR JAVASCRIPT](https://flow.org/)
    - [JSFlow is a security-enhanced JavaScript interpreter for fine-grained tracking of information flow.](http://www.jsflow.net/)
    - [A tool for studying JavaScript malware.](https://github.com/CapacitorSet/box-js)
    - [A Javascript malware analysis tool](https://github.com/svent/jsdetox)
    - [Scalable Analysis Framework for ECMAScript](https://github.com/sukyoung/safe)
    - [DEPRECATED: Static analysis tool for javascript code.](https://github.com/mozilla/scanjs)
    - [Analyzing JavaScript and the Web with WALA](http://wala.sourceforge.net/files/WALAJavaScriptTutorial.pdf)
    - [Jsunpack: jsunpack-n emulates browser functionality when visiting a URL](https://github.com/urule99/jsunpack-n)
    - [Collection of almost 40.000 javascript malware samples](https://github.com/HynekPetrak/javascript-malware-collection)
    - [JSAI: a static analysis platform for JavaScript](https://dl.acm.org/citation.cfm?id=2635904)
        - [Clone of JSAI static analysis framework](https://github.com/nystrom/jsai)
    - [Static analysis of event-driven Node.js JavaScript applications](https://dl.acm.org/citation.cfm?id=2814272)
    - [Dynamic analysis framework for JavaScript](https://github.com/Samsung/jalangi2)
- Java
    - [Android Malware Detection Framework](https://github.com/soarlab/maline)
    - [Code for Deep Android Malware Detection paper](https://github.com/niallmcl/Deep-Android-Malware-Detection)
    - [FlowDroid Static Data Flow Tracker](https://github.com/secure-software-engineering/FlowDroid)
- CSharp
    - [Security Code Scan - static code analyzer for .NET](https://security-code-scan.github.io/)
- Dependency management tools 
    - [Bower: A package manager for the web](https://github.com/bower/bower)
    - [Yarn: Fast, reliable, and secure dependency management](https://github.com/yarnpkg/yarn)
- Dynamic analysis
    - [Dynamorio: Dynamic Instrumentation Tool Platform](https://github.com/DynamoRIO/dynamorio)
    - [Dynamic Application Security Test Orchestration (DASTO)](https://github.com/target/webbreaker)
    - [Valgrind is an instrumentation framework for building dynamic analysis tools](http://valgrind.org/)
    - [A taint-tracking plugin for the Valgrind memory checking tool](https://github.com/wmkhoo/taintgrind)
- Analysis framework
    - [Modular file scanning/analysis framework: support ClamAV etc.](https://github.com/mitre/multiscanner)
    - [A free malware analysis service for the community that detects and analyzes unknown threats using a unique Hybrid Analysis technology.](https://www.reverse.it/)
    - [More than 5200 open source projects and 25000 developers use Coverity Scan](https://scan.coverity.com/)

## AST parsers for different languages ##
- Python AST parser, use ast.parse
    - [ast.parse](https://www.programcreek.com/python/example/4282/ast.parse)
    - [ast.parse parameters](http://greentreesnakes.readthedocs.io/en/latest/tofrom.html)
    - [annotate the python ast: asttoken](https://github.com/gristlabs/asttokens)
    - [Writing the setup script](https://docs.python.org/2/distutils/setupscript.html)
- JavaScript AST parser, use Esprima
    - [Estree: JavaScript Parser api specifications](https://github.com/estree/estree)
    - [Answers refer to SpiderMonkey and Esprima](https://stackoverflow.com/questions/16127985/what-is-javascript-ast-how-to-play-with-it)
    - [SpiderMonkey](https://developer.mozilla.org/en-US/docs/Mozilla/Projects/SpiderMonkey/Parser_API)
    - [Esprima](http://esprima.org/), [Esprima comparison](http://esprima.org/test/compare.html)
    - [Acorn](https://github.com/acornjs/acorn), [Acorn vs Esprima](http://marijnhaverbeke.nl/blog/acorn.html)
    - [Babel compiler, based on acorn](https://github.com/babel/babel/tree/master/packages/babel-parser)
    - [Python port of Esprima](https://github.com/Kronuz/esprima-python)
    - [How npm handles the "scripts" field](https://docs.npmjs.com/misc/scripts)
    - [Node.js API specification](https://nodejs.org/api/index.html)
    - [Javascript Standard objects by category](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects)
        - [JavaScript methods index](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Methods_Index)
- Ruby AST parser
    - [Ruby in twenty minutes](https://www.ruby-lang.org/en/documentation/quickstart/)
    - [A Ruby parser](https://github.com/whitequark/parser), [download stats](https://rubygems.org/gems/parser/versions/2.3.1.2)
    - [ruby_parser](https://github.com/seattlerb/ruby_parser)
    - [Comparison between parser and ruby_parser](https://whitequark.org/blog/2012/10/02/parsing-ruby/)
    - [Using A Ruby parser to find deprecated syntax](https://blog.arkency.com/using-ruby-parser-and-ast-tree-to-find-deprecated-syntax/)
    - [Ruby eval function can be dangerous](https://blog.udemy.com/ruby-eval/)
    - [Ruby exec, system, %x() and Backticks](https://stackoverflow.com/questions/6338908/ruby-difference-between-exec-system-and-x-or-backticks)
    - [How to execute a script while gem installation?](https://stackoverflow.com/questions/14395992/how-to-execute-a-script-while-gem-installation)
- Java AST parser
    - [Soot](https://github.com/Sable/soot)
    - [Wala](https://github.com/wala/WALA)
    - [Run a script after maven install](https://stackoverflow.com/questions/39087922/run-a-script-after-maven-install)
    - [Exploitable Java functions](https://stackoverflow.com/questions/4339611/exploitable-java-functions)
- C# AST parser
    - [microsoft binskim](https://github.com/Microsoft/binskim)
    - [automated C#/.NET code analyzer](https://security.stackexchange.com/questions/25031/are-there-any-free-static-analysis-tools-for-c-net-code)
    - [Verocode supports static analysis of many languages](https://help.veracode.com/reader/4EKhlLSMHm5jC8P8j3XccQ/UXI5sR0ayWfLm6ifmd4zWw)
    - [security-code-scan](https://github.com/security-code-scan/security-code-scan)
    - [security-guard](https://github.com/dotnet-security-guard/roslyn-security-guard/)
    - [PUMA Scan](https://pumascan.com/)
    - [comparison of C# code analyzers](https://codehollow.com/2016/08/use-code-analyzers-csharp-improve-code-quality/)
- Php AST parser
    - [PHP-Parser](https://github.com/nikic/PHP-Parser)
    - [php-ast](https://github.com/nikic/php-ast)
    - [Generate AST of a PHP source file](https://stackoverflow.com/questions/6153634/generate-ast-of-a-php-source-file)
    - [phpjoern](https://github.com/malteskoruppa/phpjoern)
    - [Exploitable PHP functions](https://stackoverflow.com/questions/3115559/exploitable-php-functions)
    - [Dangerous PHP functions](https://www.eukhost.com/blog/webhosting/dangerous-php-functions-must-be-disabled/)
    - [Disable Dangerous PHP functions](https://gist.github.com/fuyuanli/f789580e1e9e39efd84f60f7bc3ad63f)
    - [Composer scripts for dynamic analysis](https://getcomposer.org/doc/articles/scripts.md)
- C/C++ AST parser
    - [Clang](https://clang.llvm.org/)


# Resource #

- [Taobao mirror of NPM](https://npm.taobao.org/), 
- [Stanford mirror of pypi](https://nero-mirror.stanford.edu/pypi/simple/my_project101011/)
- [Mirrors of registries in China](https://github.com/PaicFE/blog/issues/3)
- [Keeping The npm Registry Awesome: How npmjs works?](https://nodejs.org/en/blog/npm/2013-outage-postmortem/)
- [Query npmjs registry via api](https://stackoverflow.com/questions/34071621/query-npmjs-registry-via-api)
- [NPM search with history versions](http://npmsearch.com/)
- [numeric precision matters: how npm download counts work](https://blog.npmjs.org/post/92574016600/numeric-precision-matters-how-npm-download-counts)
- [npmjs api documents](https://github.com/npm/registry/tree/master/docs)
- [Synk's CLI help you find and fix known vulnerabilities in your dependencies, both ad hoc and as part of your CI system](https://snyk.io/docs/using-snyk)
- [Using the European npm mirror](https://shapeshed.com/using-the-european-npm-mirror/)
- [What I learned from analysing 1.65M versions of Node.js modules in NPM](https://blog.nodeswat.com/what-i-learned-from-analysing-1-65m-versions-of-node-js-modules-in-npm-a0299a614318)
- [Archive.org snapshots websites and can be used for measuring victim websites](https://web.archive.org/web/*/gatech.edu)
- [Event Tracing for Windows (ETW)](https://docs.microsoft.com/en-us/windows/desktop/etw/event-tracing-portal)
    - [intro to ETW](https://docs.microsoft.com/en-us/windows/desktop/etw/about-event-tracing)
- [Linux Audit](https://linux-audit.com/)
    - [Tuning auditd: high-performance Linux Auditing](https://linux-audit.com/tuning-auditd-high-performance-linux-auditing/)
    - [Linux Audit Framework 101 – Basic Rules for Configuration](https://linux-audit.com/linux-audit-framework-101-basic-rules-for-configuration/)
    - [Linux Audit: Auditing the Network Configuration](https://linux-audit.com/linux-audit-auditing-network-configuration/)
    - [ How To Use the Linux Auditing System on CentOS 7](https://www.digitalocean.com/community/tutorials/how-to-use-the-linux-auditing-system-on-centos-7)
    - [CHAPTER 7. SYSTEM AUDITING](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/6/html/security_guide/chap-system_auditing)
- [Strace](https://github.com/strace/strace)
    - [Strace Analyzer](https://clusterbuffer.wordpress.com/strace-analyzer/)
    - [python-ptrace is a Python binding of ptrace library](https://github.com/vstinner/python-ptrace)
    - [pystrace -- Python tools for parsing and analysing strace output files](https://github.com/dirtyharrycallahan/pystrace)
    - [analyzes strace output](https://github.com/wookietreiber/strace-analyzer)
    - [Profiling and visualizing with GNU strace](https://blog.cppse.nl/profiler-based-on-strace)
        - [I created a BNF grammer for the output and used bnfc to automatically generate a parser in C++.](https://bitbucket.org/rayburgemeestre/strace-output-parser/src/master/)
    - [Structured output for strace](https://lists.strace.io/pipermail/strace-devel/2014-February/002897.html)
    - [like strace, but for ruby code](https://github.com/tmm1/rbtrace)
    - [pytrace is a fast python tracer. it records function calls, arguments and return values.](https://github.com/alonho/pytrace)
    - [php-strace helps to track down segfaults in running php processes](https://github.com/markus-perl/php-strace)
    - [How to set strace output characters string width to be longer?](https://serverfault.com/questions/240788/how-to-set-strace-output-characters-string-width-to-be-longer)
        - `-s` option specifies the  maximum  string  size  to  print
        - `-v` option print unabbreviated argv, stat, termios, etc. args
    - Google Summer of Code for Strace output
        - [strace participation in the GSOC 2014](https://sourceforge.net/p/strace/wiki/GoogleSummerOfCode2014/)
        - [Truly structured output for strace in the GSOC 2016](https://summerofcode.withgoogle.com/archive/2016/projects/6296300991545344/)
        - [Doc for GSOC 2016](https://github.com/lineprinter/strace/wiki/GSoC-related-information)
- [DTrace for linux](https://github.com/dtrace4linux/linux)
    - [Code for the cross platform, single source, OpenDTrace implementation](https://github.com/opendtrace/opendtrace)
    - [Ftrace is an internal tracer designed to help out developers and designers of systems to find what is going on inside the kernel.](https://www.kernel.org/doc/Documentation/trace/ftrace.txt)
    - [What is the difference between DTrace and STrace](https://www.quora.com/What-is-the-difference-between-DTrace-and-STrace)
    - [Sysdig vs DTrace vs Strace: a Technical Discussion](https://sysdig.com/blog/sysdig-vs-dtrace-vs-strace-a-technical-discussion/)
- [osquery: Process and socket auditing with osquery](https://github.com/facebook/osquery/blob/master/docs/wiki/deployment/process-auditing.md)
    - [Information collected by osquery (tables)](https://osquery.io/schema/3.2.6)
    - [A curated list of tools and resources for security incident response, aimed to help security analysts and DFIR teams.](https://github.com/meirwah/awesome-incident-response)
    - [1st: How are teams currently using osquery?](https://blog.trailofbits.com/2017/11/09/how-are-teams-currently-using-osquery/)
    - [2nd: What are the current pain points of osquery?](https://blog.trailofbits.com/2017/12/21/osquery-pain-points/)
    - [3rd: What do you wish osquery could do?](https://blog.trailofbits.com/2018/04/10/what-do-you-wish-osquery-could-do/)
    - [Kolide Cloud is an endpoint monitoring solution which leverages and instruments Facebook’s open-source osquery project. Try it today; completely free for your first 10 devices.](https://blog.kolide.com/managing-osquery-with-kolide-launcher-and-fleet-b33b4536acb4)
    - [Kolide fleet for monitoring osquery machines](https://github.com/kolide/fleet)
    - [Docker support in OSQuery](https://github.com/facebook/osquery/pull/3241)
    - [Dockerfiles for containerized osquery](https://github.com/kolide/docker-osquery)
    - [Uptycs: Securing Containers: Using osquery to Solve New Challenges Posed by Hosted Orchestration Services](https://www.uptycs.com/blog/securing-containers-running-in-hosted-orchestration-services)
    - [Uptycs: Docker and osquery](https://seshupasam.wordpress.com/2017/09/19/docker-and-osquery/)
    - [osquery For Security: Introduction to osquery — Part 1](https://medium.com/@clong/osquery-for-security-b66fffdf2daf)
    - [osquery for Security — Part 2](https://medium.com/@clong/osquery-for-security-part-2-2e03de4d3721)
    - [osquery—Windows, macOS, Linux Monitoring and Intrusion Detection](https://www.usenix.org/conference/lisa17/conference-program/presentation/reed)
    - [Docker and osquery](https://seshupasam.wordpress.com/2017/09/19/docker-and-osquery/)
    - [Intro to Osquery: Frequently Asked Questions for Beginners](https://www.uptycs.com/blog/intro-to-osquery-frequently-asked-questions-for-beginners)
    - [osquery configuration from palantir](https://github.com/palantir/osquery-configuration)
- [sysdig: Linux system exploration and troubleshooting tool with first class support for containers](https://github.com/draios/sysdig)
    - [SELinux, Seccomp, Sysdig Falco, and you: A technical discussion](https://sysdig.com/blog/selinux-seccomp-falco-technical-discussion/)
    - [Prometheus Monitoring and Sysdig Monitor: A Technical Comparison](https://sysdig.com/blog/prometheus-monitoring-and-sysdig-monitor-a-technical-comparison/)
    - [Day 3 - So Server, tell me about yourself. An introduction to facter, osquery and sysdig](http://sysadvent.blogspot.com/2014/12/day-3-so-server-tell-me-about-yourself.html)
        - ```Whereas Facter and osquery are predominantly about querying infrequently changing information, Sysdig is much more suited to working with real-time data streams – for example, network or file I/O, or tracking errors in running processes.```
    - [Container Monitoring: Prometheus and Grafana Vs. Sysdig and Sysdig Monitor](https://dzone.com/articles/container-monitoring-prometheus-and-grafana-vs-sys)
    - [Container monitoring with Sysdig](https://www.slideshare.net/SreenivasMakam/container-monitoring-with-sysdig-58790785)
    - [Sysdig user guide](https://github.com/draios/sysdig/wiki/sysdig-user-guide)
    - [Sysdig falco](https://github.com/draios/falco/wiki/How-to-Install-Falco-for-Linux)
    - [Sysdig falco rules](https://github.com/draios/falco/wiki/Falco-Rules)
    - [Detecting Cryptojacking with Sysdig’s Falco](https://sysdig.com/blog/detecting-cryptojacking-with-sysdigs-falco/)
    - [Sysdig + logstash + elasticsearch](https://stackoverflow.com/questions/40359132/import-sysdig-data-into-elastic)
    - [Sysdig + ELK (potential)](https://logz.io/blog/sysdig-elk-stack/)
    - [Sending Kubernetes & Docker events to Elasticsearch and Splunk using Sysdig](https://sysdig.com/blog/kubernetes-docker-elasticsearch-splunk/)
    - [Runtime Container Security – How to Implement Open Source Container Security](https://sysdig.com/blog/oss-container-security-runtime/)
    - [WTF my container just spawned a shell](https://archive.fosdem.org/2017/schedule/event/container_spawned_shell/)
- [go-auditd](https://slack.engineering/syscall-auditing-at-scale-e6a3ca8ac1b8)
    - [go-audit is an alternative to the auditd daemon that ships with many distros](https://github.com/slackhq/go-audit)
- [The Prometheus monitoring system and time series database.](https://github.com/prometheus/prometheus)
    - [Prometheus official site](https://prometheus.io/)
    - [go-audit-container](https://github.com/auditNG/go-audit-container)
    - [FIM AND SYSTEM CALL AUDITING AT SCALE IN A LARGE CONTAINER DEPLOYMENT](https://www.rsaconference.com/writable/presentations/file_upload/csv-r14-fim-and-system-call-auditing-at-scale-in-a-large-container-deployment.pdf)
- [kubernetes: Kubernetes is an open-source system for automating deployment, scaling, and management of containerized applications.](https://kubernetes.io/)
    - [kubernetes github](https://github.com/kubernetes/kubernetes)
- [facter: Collect and display system facts](https://github.com/puppetlabs/facter)
    - [facter: core facts](https://puppet.com/docs/facter/3.9/core_facts.html)
- [Find exploitable PHP files by parameter fuzzing and function call tracing](https://github.com/XiphosResearch/phuzz)
- [An OS X analyzer for Cuckoo Sandbox project](https://github.com/rodionovd/cuckoo-osx-analyzer)
- [Cuckoo Sandbox is the leading open source automated malware analysis system](https://cuckoosandbox.org/)
- [Native libraries with Maven](http://blog.dub.podval.org/2011/01/native-libraries-with-maven.html)
- [Maven: Bundling and Unpacking Native Libraries](https://myshittycode.com/2015/11/09/maven-bundling-and-unpacking-native-libraries/)
- [Native ARchive plugin for Maven](https://github.com/maven-nar/nar-maven-plugin/wiki/Native-Library-Loader)
- [Elastic file system (EFS) mount outside of AWS](https://serverfault.com/questions/799016/elastic-file-system-efs-mount-outside-of-aws)
- [Amazon EFS Update – On-Premises Access via Direct Connect](https://aws.amazon.com/blogs/aws/amazon-efs-update-on-premises-access-via-direct-connect-vpc/)
- [The Go Programming Language](https://golang.org/pkg/)
    - [Due to the way Go does imports, a central clearing house like Maven or NPM is simply not needed.](https://go-search.org/about)
    - [Project for Go Search, a search engine for finding popular and relevant packages.](https://github.com/daviddengcn/gcse)
- [Ruby (finally) gains in popularity, but Go plateaus](https://www.infoworld.com/article/3261566/application-development/ruby-finally-gains-in-popularity-but-go-plateaus.html)
    - Top languages: Java, C, C++, Python, C#, PHP, JavaScript, Ruby
- Static analysis references
    - [Automated type inference for dynamically typed programs](https://medium.com/vimeo-engineering-blog/automated-type-inference-for-dynamically-typed-programs-6e79197e5420)
        - [A static analysis tool for finding errors in PHP applications](https://github.com/vimeo/psalm)
- [IBM appscan allows scanning source/compiled code for vulnerabilities](https://www-01.ibm.com/support/docview.wss?uid=swg21628056)
    - [Support languages of AppScan: supports C/C++, .NET, Java, JSP, JavaScript, Php, ASP, Python](https://www.ibm.com/support/knowledgecenter/en/SSS9LM_9.0.3/com.ibm.rational.appscansrc.install.doc/topics/system_requirements_language_support.html)
    - [IBM Security AppScan Source 9.0.3.10 available at Fix Central](https://www-01.ibm.com/support/docview.wss?uid=ibm10729207)
    - [AppScan Source versions available](https://www-01.ibm.com/support/docview.wss?uid=swg21971044)
- Restricted execution
    - [Sandboxed Python](https://wiki.python.org/moin/SandboxedPython)
    - [Ruby sandboxing vs. integrating a scripting language](https://stackoverflow.com/questions/8619422/ruby-sandboxing-vs-integrating-a-scripting-language)
    - [Jailed — flexible JS sandbox](https://github.com/asvd/jailed)
    - [Is It Possible to Sandbox JavaScript Running In the Browser?](https://stackoverflow.com/questions/195149/is-it-possible-to-sandbox-javascript-running-in-the-browser)
    - [Is there a way to execute php code in a sandbox from within php](https://stackoverflow.com/questions/324726/is-there-a-way-to-execute-php-code-in-a-sandbox-from-within-php)
    - [Runkit_Sandbox](http://php.net/manual/en/runkit.sandbox.php)
    - [Sandboxing Java Code](https://www.javacodegeeks.com/2012/11/sandboxing-java-code.html)
    - [Execute a method in Java with restricted permissions](https://stackoverflow.com/questions/15885300/execute-a-method-in-java-with-restricted-permissions)
- AWS Batch Jobs
    - [aws batch tutorial](https://www.youtube.com/watch?v=S1Vf4orJqcw)
    - [aws batch: simplifying batch computing in the cloud](https://www.youtube.com/watch?v=H8bmHU_z8Ac)
    - aws batch example
        - [ec2-spot-aws-batch](https://github.com/awslabs/ec2-spot-labs/tree/master/ec2-spot-aws-batch)
        - [sqs-ec2-spot-fleet-autoscaling](https://github.com/awslabs/ec2-spot-labs/tree/master/sqs-ec2-spot-fleet-autoscaling)
- Airflow Dag
    - [Parallel running DAG of tasks in Python’s Celery](https://medium.com/@pavloosadchyi/parallel-running-dag-of-tasks-in-pythons-celery-4ea73c88c915)
    - [Airflow - Scaling Out with Celery](https://airflow.apache.org/howto/executor/use-celery.html)
    - [Airflow Dag](https://airflow.apache.org/tutorial.html)
    - [Airflow introduction](https://cwiki.apache.org/confluence/display/AIRFLOW/Roadmap)
    - [Airflow on Kubernetes (Part 1): A Different Kind of Operator](https://kubernetes.io/blog/2018/06/28/airflow-on-kubernetes-part-1-a-different-kind-of-operator/)
    - [A docker image and kubernetes config files to run Airflow on Kubernetes](https://github.com/mumoshu/kube-airflow)
    - [A Guide On How To Build An Airflow Server/Cluster](https://stlong0521.github.io/20161023%20-%20Airflow.html)
- Security advisories
    - [Rubygems problems](http://help.rubygems.org/discussions/problems)
        - [Rubygems advisory](https://github.com/rubysec/ruby-advisory-db)
    - [Npmpjs security advisories](https://www.npmjs.com/advisories)
    - [Python packages](https://github.com/pyupio/safety-db)
    - [Packagist packages](https://github.com/FriendsOfPHP/security-advisories)
    - Maven packages
    - [JCenter packages](https://status.bintray.com/history)
    - [VulnDB Data Mirror](https://github.com/stevespringett/vulndb-data-mirror)
    - [Dependency track](https://github.com/DependencyTrack/dependency-track)
    - [Dependency check](https://github.com/jeremylong/DependencyCheck)
    - [Microsoft Security Advisory](https://docs.microsoft.com/en-us/security-updates/securityadvisories/2018/4338110)


# Reference #

- [module counts](http://www.modulecounts.com)
    - [a quick website to track the number of modules in various repositories](https://github.com/edebill/modulecounts)
- [typo-squatting website](http://incolumitas.com/2016/06/08/typosquatting-package-managers/)
- [typo-squatting thesis](http://incolumitas.com/data/thesis.pdf)
- [debian popcorn](https://popcon.debian.org)
- [pypi packages found to be malicious](http://www.nbu.gov.sk/skcsirt-sa-20170909-pypi/index.html)
- [Python Typo Squatting](https://www.pytosquatting.org)
- [PHP Typo Squatting](https://phpsec.xyz/composer-typosquatting-vulnerability-877d263509ec)
- [JCenter Typo Squatting](https://status.bintray.com/incidents/w4dfr0rpznkt)
- [Rubygems typosquatting](http://help.rubygems.org/discussions/problems/33195-malware-in-a-gem)
- [HUNTING MALICIOUS NPM PACKAGES](https://duo.com/decipher/hunting-malicious-npm-packages)
- [Malicious npm packages](https://hackernoon.com/im-harvesting-credit-card-numbers-and-passwords-from-your-site-here-s-how-9a8cb347c5b5)
- [list of all pypi packages](https://pypi.python.org/simple/)
- [Crossenv malware on the npm registry](https://blog.npmjs.org/post/163723642530/crossenv-malware-on-the-npm-registry)
- [Open source packages with malicious intent](https://medium.com/sourceclear/open-source-packages-with-malicious-intent-142fec637f19)
- [HOW TO TAKE OVER THE COMPUTER OF ANY JAVA (OR CLOJURE OR SCALA) DEVELOPER](https://max.computer/blog/how-to-take-over-the-computer-of-any-java-or-clojure-or-scala-developer/)
- [Security Corner with Snyk: Top Six Vulnerabilities in Maven and npm](https://www.cloudfoundry.org/blog/security-corner-snyk-top-six-vulnerabilities-maven-npm/)
- [Another Linux distro poisoned with malware](https://nakedsecurity.sophos.com/2018/07/11/another-linux-distro-poisoned-with-malware/)
- [NodeJS: Remote Code Execution as a Service](https://drive.google.com/file/d/0ByL_eDzFMdXzWHh3eFJuM0xTWjg/view)
- [17 Backdoored Docker Images Removed From Docker Hub](https://www.bleepingcomputer.com/news/security/17-backdoored-docker-images-removed-from-docker-hub/)
- [Backdoored Python Library Caught Stealing SSH Credentials](https://www.bleepingcomputer.com/news/security/backdoored-python-library-caught-stealing-ssh-credentials/)
- [eslint-scope is the ECMAScript scope analyzer used in ESLint. Version 3.7.2 was identified as malicious after a possible npm account takeover. Installing the malicious package would lead to leaking the user's npm token.](https://snyk.io/vuln/npm:eslint-scope:20180712)
- [npm Acquires ^Lift Security and the Node Security Platform](https://medium.com/npm-inc/npm-acquires-lift-security-258e257ef639)
- [analyze pip ssh-decorate supply-chain attack](https://zhuanlan.zhihu.com/p/36677867)
- [Malicious .jar Files Hosted On Google Code](https://www.zscaler.com/blogs/research/malicious-jar-files-hosted-google-code)
- [Dissection of a Java Malware (JRAT)](http://www.alliacom.com/nous-suivre/blog/item/dissection-of-a-java-malware-jrat)
- [The packages potentially affected by eslint-scope](https://gist.github.com/thenewwazoo/0306aa06aafe7807497ed1db430ee2b8)
- [Malicious Modules — what you need to know when installing npm packages](https://medium.com/@liran.tal/malicious-modules-what-you-need-to-know-when-installing-npm-packages-12b2f56d3685)
- [Twelve malicious Python libraries found and removed from PyPI](https://www.zdnet.com/article/twelve-malicious-python-libraries-found-and-removed-from-pypi/)
- [Malware packages on PyPI](https://github.com/pypa/warehouse/issues/3948)
- [Plot to steal cryptocurrency foiled by the npm security team](https://blog.npmjs.org/post/185397814280/plot-to-steal-cryptocurrency-foiled-by-the-npm)
- [Vulnerability Discovered In Komodo’s Agama Wallet – This Is What You Need To Do](https://komodoplatform.com/vulnerability-discovered-in-komodos-agama-wallet-this-is-what-you-need-to-do/)
- [PyPI malware packages](https://github.com/rsc-dev/pypi_malware.git)
- [Report projects that damage other packages, don't adhere to guidelines, or are malicious](https://github.com/pypa/warehouse/issues/3896)
- [Collection of Php backdoors](https://github.com/bartblaze/PHP-backdoors)
- [Collection of windows malware](https://github.com/malwares)
- [Snakes in the grass! Malicious code slithers into Python PyPI repository](https://nakedsecurity.sophos.com/2018/10/30/snakes-in-the-grass-malicious-code-slithers-into-python-pypi-repository/)
- [Cryptojacking invades cloud. How modern containerization trend is exploited by attackers](https://kromtech.com/blog/security-center/cryptojacking-invades-cloud-how-modern-containerization-trend-is-exploited-by-attackers)
- [This is the list of all packages found by @malicious-packages/core and removed from repository by npm team](https://github.com/malicious-packages/cemetry)
- [First Top 10 Risks for Applications Built on Serverless Architectures Research by PureSec Released](https://www.puresec.io/press_releases/sas_top_10_2018_released)
- [Exploiting Developer Infrastructure Is Ridiculously Easy](https://medium.com/s/story/exploiting-developer-infrastructure-is-insanely-easy-9849937e81d4)
- [Javascript static + dynamic analysis](http://www.franktip.org/pubs.html)
- [Php backdoor obfuscation techniques](https://vexatioustendencies.com/php-backdoor-obfuscation-techniques/)
- [Php obfuscation techniques](https://blog.dutchcoders.io/php-obfuscation-techniques/)
- [Understanding Obfuscated Code & How to Deobfuscate PHP and JavaScript](https://www.upwork.com/hiring/development/understanding-obfuscated-code-deobfuscate-php-javascript/)
- [Joomla Plugin Constructor Backdoor](https://blog.sucuri.net/2014/04/joomla-plugin-constructor-backdoor.html)
- [A confusing dependency](https://blog.autsoft.hu/a-confusing-dependency/)
- [Exposed Docker Control API and Community Image Abused to Deliver Cryptocurrency-Mining Malware](https://blog.trendmicro.com/trendlabs-security-intelligence/exposed-docker-control-api-and-community-image-abused-to-deliver-cryptocurrency-mining-malware/)
- [Malicious remote code execution backdoor discovered in the popular bootstrap-sass Ruby gem](https://snyk.io/blog/malicious-remote-code-execution-backdoor-discovered-in-the-popular-bootstrap-sass-ruby-gem/)
- [Backdoor in Captcha Plugin Affects 300K WordPress Sites](https://www.wordfence.com/blog/2017/12/backdoor-captcha-plugin/)
- [Backdoor found in Webmin, a popular web-based utility for managing Unix servers](https://www.zdnet.com/article/backdoor-found-in-webmin-a-popular-web-based-utility-for-managing-unix-servers/)
    - [DEFCON-Webmin-1920-Unauthenticated-Remote-Command-Execution](https://pentest.com.tr/exploits/DEFCON-Webmin-1920-Unauthenticated-Remote-Command-Execution.html)
- [POLA Would Have Prevented the Event-Stream Incident](https://medium.com/agoric/pola-would-have-prevented-the-event-stream-incident-45653ecbda99)
- [Cryptojacking Criminals Are Using Multiple Techniques to Install Coinminers](https://medium.com/threat-intel/cryptojacking-coin-mining-cybercrime-234895bec6e1)
- [Google Analytics and Angular in Magento Credit Card Stealing Scripts](https://blog.sucuri.net/2019/02/google-analytics-and-angular-in-magento-credit-card-stealing-scripts.html)
- [PSA: There is a fake version of this package on PyPI with malicious code](https://github.com/dateutil/dateutil/issues/984)
- [Typosquatting barrage on RubyGems software repository users](https://blog.reversinglabs.com/blog/mining-for-malicious-ruby-gems)
- [PyPI 官方仓库遭遇request恶意包投毒](https://mp.weixin.qq.com/s/dkPdXfGfSK097GI6Ln92lA)
- [SourMint: malicious code, ad fraud, and data leak in iOS](https://snyk.io/blog/sourmint-malicious-code-ad-fraud-and-data-leak-in-ios/)
    - [SourMint Malicious SDK](https://snyk.io/blog/sourmint-malicious-code-ad-fraud-and-data-leak-in-ios/)
- [Dependency Hijacking Software Supply Chain Attack Hits More Than 35 Organizations](https://blog.sonatype.com/dependency-hijacking-software-supply-chain-attack-hits-more-than-35-organizations)
    - [Sonatype Spots 275+ Malicious npm Packages Copying Recent Software Supply Chain Attacks that Hit 35 Organizations](https://blog.sonatype.com/sonatype-spots-150-malicious-npm-packages-copying-recent-software-supply-chain-attacks)
    - [Newly Identified Dependency Confusion Packages Target Amazon, Zillow, and Slack; Go Beyond Just Bug Bounties](https://blog.sonatype.com/malicious-dependency-confusion-copycats-exfiltrate-bash-history-and-etc-shadow-files)
- [Dependency Confusion: How I Hacked Into Apple, Microsoft and Dozens of Other Companies](https://medium.com/@alex.birsan/dependency-confusion-4a5d60fec610)
    - for pip, `--extra-index-url` for internal/external packages will choose the version with higher version number
    - for gem, `gem install --source`
    - [index-url extra-index-url install priority order](https://github.com/pypa/pip/issues/5045)
    - [index-url extra-index-url install priority order - contd](https://github.com/pypa/pip/issues/8606)
    - [pywheels for Raspberry Pi](https://www.piwheels.org/)
- [Package name squatting: cupy-cuda112](https://github.com/cupy/cupy/issues/4787)

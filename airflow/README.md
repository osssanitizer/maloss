# Intro #

Use airflow to run jobs.

Airflow docker image relies on python3. So dags should be executed/tested using python3.

# HowTo #

- run airflow with local executor
    - `docker-compose -f docker-compose-local.yml up -d`
    - terminate
    - `docker-compose -f docker-compose-local.yml down`
- run airflow with celery executor + docker swarm
    - deploy
        - `docker stack deploy --with-registry-auth -c <(docker-compose -f docker-swarm-celery.yml config) rubygems_astfilter`
    - [run the above command with `sudo bash -c "$CMD"` to allow anonymous fifo](https://superuser.com/questions/184307/bash-create-anonymous-fifo)
        - `sudo bash -c "docker stack deploy --with-registry-auth -c <(docker-compose -f docker-swarm-celery.yml config) rubygems_astfilter"`
        - [docker don't want to add env file support on CLI](https://github.com/moby/moby/issues/29133)
    - terminate
        - `docker stack rm rubygems_astfilter`
    - check status
        - `docker stack ps rubygems_astfilter`
    - check service status
        - `docker service ls`
        - `docker service ps rubygems_astfilter_worker`
    - redeploy the updated services
        - `docker stack deploy --with-registry-auth -c <(docker-compose -f docker-swarm-celery.yml config) rubygems_astfilter`
- run airflow with celery executor
    - master machine
        - `sudo docker-compose --compatibility -f docker-compose-master.yml up -d`
    - worker machine
        - `sudo docker-compose --compatibility up -d`
- turn on the dag to run in the UI and trigger the dag from UI
    - visit the UI at `http://localhost:8080`
    - toggle the DAG `pypi_static` on and click `Trigger Dag` to start the `pypi_static` dag
    - [external triggering](https://stackoverflow.com/questions/37040975/triggering-an-airflow-dag-from-terminal-not-working)
- generate a dummy *test_graph.pickle* graph to play with
    - `python data/test.py`
- [deprecated] deploy docker swarm cluster
    - docker swarm cluster deployment, requires the following port to be open
        - TCP port 2377 for cluster management communications
        - TCP and UDP port 7946 for communication among nodes
        - UDP port 4789 for overlay network traffic
    - command to join swarm cluster and deploy docker services
        - `docker swarm join --token $token $ip:$port`
        - `docker stack deploy --with-registry-auth -c docker-compose.yml getstartedlab`


# References #

- [airflow docker image](https://github.com/puckel/docker-airflow)
- [airflow tutorial](https://airflow.apache.org/howto/operator.html#pythonoperator)
- [parallelism/dag_concurrency/max_active_runs](https://airflow.apache.org/faq.html)

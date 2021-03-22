# Use an official Python runtime as a parent image
FROM ubuntu:16.04

# Add user
RUN useradd -m maloss && adduser maloss sudo
RUN mkdir -p /etc/sudoers.d && echo "maloss ALL=(ALL:ALL) NOPASSWD: ALL" > /etc/sudoers.d/maloss


# Install toolchain 
RUN apt-get update -yqq
RUN apt-get install -yqq sudo curl wget php git ruby-full rubygems-integration nuget python python-pip npm jq vim strace nano
RUN DEBIAN_FRONTEND=noninteractive apt-get install -yqq tzdata

# Copy contents to inside contianer
ARG MALOSS_HOME=/home/maloss
ADD config ${MALOSS_HOME}/config
ADD data ${MALOSS_HOME}/data
ADD src ${MALOSS_HOME}/src
ADD main ${MALOSS_HOME}/main

# Install dependencies
WORKDIR ${MALOSS_HOME}
RUN ${MALOSS_HOME}/src/install_dep.sh
RUN ${MALOSS_HOME}/src/install_protoc.sh
RUN ${MALOSS_HOME}/src/install_nuget.sh
RUN ${MALOSS_HOME}/main/install_dep.sh

# Change current user and create folders
RUN chown -R maloss:maloss ${MALOSS_HOME}
USER maloss 

# Prepare honeypot
RUN ${MALOSS_HOME}/data/honeypot.sh

# Prepare output directories
RUN mkdir ${MALOSS_HOME}/metadata
RUN mkdir ${MALOSS_HOME}/result
WORKDIR ${MALOSS_HOME}/src



##################################################################################
# Basic Airflow container
##################################################################################
# Ref: https://github.com/puckel/docker-airflow/blob/master/Dockerfile
# Never prompts the user for choices on installation/configuration of packages
USER root
ENV DEBIAN_FRONTEND noninteractive
ENV TERM linux

# Airflow
ARG AIRFLOW_VERSION=1.10.2
ARG AIRFLOW_HOME=/home/maloss/airflow
# Enable password based authentication
# https://github.com/puckel/docker-airflow/issues/209
ARG AIRFLOW_DEPS="password"
ARG PYTHON_DEPS="flask_bcrypt sqlalchemy"
ENV AIRFLOW_GPL_UNIDECODE yes

# Define en_US.
ENV LANGUAGE en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8
ENV LC_CTYPE en_US.UTF-8
ENV LC_MESSAGES en_US.UTF-8

RUN set -ex \
    && buildDeps=' \
        freetds-dev \
        libkrb5-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        git \
    ' \
    && apt-get update -yqq \
    && apt-get upgrade -yqq \
    && apt-get install -yqq --no-install-recommends \
        $buildDeps \
        freetds-bin \
        build-essential \
        libmysqlclient-dev \
        apt-utils \
        curl \
        rsync \
        libpq5 \
        netcat \
        locales \
    && sed -i 's/^# en_US.UTF-8 UTF-8$/en_US.UTF-8 UTF-8/g' /etc/locale.gen \
    && locale-gen \
    && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8

# these dependencies are ignored
#    && pip3 install -U pip setuptools wheel \
RUN set -ex \
    && buildDeps=' \
        freetds-dev \
        libkrb5-dev \
        libsasl2-dev \
        libssl-dev \
        libffi-dev \
        libpq-dev \
        git \
    ' \
    && pip3 install pytz \
    && pip3 install pyOpenSSL \
    && pip3 install ndg-httpsclient \
    && pip3 install pyasn1 \
    && pip3 install apache-airflow[crypto,celery,postgres,hive,jdbc,mysql,ssh${AIRFLOW_DEPS:+,}${AIRFLOW_DEPS}]==${AIRFLOW_VERSION} \
    && pip3 install redis==3.2 tornado==5.1.1 networkx==2.2 \
    && if [ -n "${PYTHON_DEPS}" ]; then pip3 install ${PYTHON_DEPS}; fi

ADD airflow/script/entrypoint.sh /entrypoint.sh
ADD airflow/script/create_user.py ${AIRFLOW_HOME}/create_user.py
ADD airflow/config/airflow.cfg ${AIRFLOW_HOME}/airflow.cfg
# customizations
ADD airflow/pypi_dags ${AIRFLOW_HOME}/pypi_dags
ADD airflow/npmjs_dags0 ${AIRFLOW_HOME}/npmjs_dags0
ADD airflow/npmjs_dags1 ${AIRFLOW_HOME}/npmjs_dags1
ADD airflow/npmjs_dags2 ${AIRFLOW_HOME}/npmjs_dags2
ADD airflow/npmjs_dags3 ${AIRFLOW_HOME}/npmjs_dags3
ADD airflow/packagist_dags ${AIRFLOW_HOME}/packagist_dags
ADD airflow/rubygems_dags ${AIRFLOW_HOME}/rubygems_dags
ADD airflow/maven_dags ${AIRFLOW_HOME}/maven_dags
ADD airflow/pypi_version_dags ${AIRFLOW_HOME}/pypi_version_dags
ADD airflow/npmjs_version_dags ${AIRFLOW_HOME}/npmjs_version_dags
ADD airflow/packagist_version_dags ${AIRFLOW_HOME}/packagist_version_dags
ADD airflow/rubygems_version_dags ${AIRFLOW_HOME}/rubygems_version_dags

RUN chown -R maloss:maloss ${AIRFLOW_HOME}

EXPOSE 8080 5555 8793

USER maloss
WORKDIR ${MALOSS_HOME}/src
ENTRYPOINT ["/entrypoint.sh"]
# set default arg for entrypoint
CMD ["webserver"]

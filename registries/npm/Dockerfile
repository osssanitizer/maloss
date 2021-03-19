FROM python:3.8

RUN apt-get update -yqq && apt-get install -yqq wget
ADD ./requirements.txt /tmp
ADD ./download_npm.py /tmp
RUN pip install -r /tmp/requirements.txt
WORKDIR /tmp

ADD ./runner.py /tmp/

CMD ["python", "/tmp/runner.py", "86400"]

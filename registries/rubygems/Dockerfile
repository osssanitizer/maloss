FROM alpine:3.5

RUN apk update && apk upgrade && apk --update add \
    ruby ruby-irb ruby-rake ruby-io-console ruby-bigdecimal ruby-json ruby-bundler \
    libstdc++ tzdata bash ca-certificates git python3 \
    &&  echo 'gem: --no-document' > /etc/gemrc

ENV BUSYBOX=1
ENV MIRROR_DIR=/data/rubygems
# NOTE: the rubygems verison has bug
# RUN gem install rubygems-mirror
WORKDIR /tmp
RUN git clone https://github.com/rubygems/rubygems-mirror.git
WORKDIR /tmp/rubygems-mirror
RUN gem build rubygems-mirror.gemspec 
RUN gem install rubygems-mirror-1.3.0.gem 
WORKDIR /tmp

ADD ./run.sh /tmp/
ADD ./runner.py /tmp/

CMD ["python3", "/tmp/runner.py", "7200"]

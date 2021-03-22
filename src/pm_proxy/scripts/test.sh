#!/bin/bash

# for python
# install dependencies
pip install protobuf scrapy --user
pip3 install protobuf scrapy --user

# run the test commands
python exercise.py protobuf
python exercise.py rsa
python3 exercise_py3.py protobuf
python3 exercise_py3.py rsa
python main.py scrapy
python3 main.py scrapy

# for ruby
# install dependencies
gem install parser google-protobuf --user

# run the test commands
ruby exercise.rb parser
ruby exercise.rb google-protobuf
python main.py parser -m rubygems

# for javascript
npm install webpack

# run the test commands
node exercise.js webpack
node exercise.js watchpack

#!/bin/bash
cd ../src/

# python
python main.py astgen ../testdata/Adafruit_GPIO-1.0.3.tar.gz ../testdata/Adafruit_GPIO-1.0.3.tar.gz.out -c ../config/test_astgen_python.config
python main.py astgen ../testdata/Jinja2-2.10.tar.gz ../testdata/Jinja2-2.10.tar.gz.out -c ../config/test_astgen_python.config
python main.py astgen ../testdata/WebHelpers-1.3.tar.gz ../testdata/WebHelpers-1.3.tar.gz.out -c ../config/test_astgen_python.config
python main.py astgen ../testdata/html5lib-1.0.1.tar.gz ../testdata/html5lib-1.0.1.tar.gz.out -c ../config/test_astgen_python.config
python main.py astgen ../testdata/test-eval-exec.py ../testdata/test-eval-exec.py.out -c ../config/test_astgen_python.config

cd ../testdata

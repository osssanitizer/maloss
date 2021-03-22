#!/bin/bash
cd ../src/

# javascript
python main.py astgen ../testdata/urlgrey-0.4.4.tgz ../testdata/urlgrey-0.4.4.tgz.out -c ../config/test_astgen_javascript.config -l javascript
python main.py astgen ../testdata/bluebird-3.5.1.tgz ../testdata/bluebird-3.5.1.tgz.out  -c ../config/test_astgen_javascript.config -l javascript
python main.py astgen ../testdata/gulp-less-3.5.0.tgz ../testdata/gulp-less-3.5.0.tgz.out -c ../config/test_astgen_javascript.config -l javascript
python main.py astgen ../testdata/requirejs-2.3.5.tgz ../testdata/requirejs-2.3.5.tgz.out -c ../config/test_astgen_javascript.config -l javascript
python main.py astgen ../testdata/test-eval.js ../testdata/test-eval.js.out -c ../config/test_astgen_javascript.config -l javascript

cd ../testdata

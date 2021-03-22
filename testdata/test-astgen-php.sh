#!/bin/bash
# download the packages
cd php && composer update --prefer-source --no-scripts && cd ../

cd ../src/

# php
python main.py astgen ../testdata/test-eval-exec.php ../testdata/test-eval-exec.php.out -c ../config/test_astgen_php.config -l php
python main.py astgen ../testdata/php/vendor/symfony/polyfill-mbstring/ ../testdata/symfony_polyfill-mbstring.out -c ../config/test_astgen_php.config -l php
python main.py astgen ../testdata/php/vendor/guzzlehttp/guzzle/ ../testdata/guzzlehttp_guzzle.out -c ../config/test_astgen_php.config -l php

cd ../testdata

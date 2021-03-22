#!/bin/bash
cd ../src/

# ruby
python main.py astgen ../testdata/test-eval.rb ../testdata/test-eval.rb.out -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/activesupport-5.2.0.gem ../testdata/activesupport-5.2.0.gem.out -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/evaluator-0.1.6.gem ../testdata/evaluator-0.1.6.gem.out  -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/gen_eval-0.4.0.gem ../testdata/gen_eval-0.4.0.gem.out  -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/rake-12.3.1.gem ../testdata/rake-12.3.1.gem.out  -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/safe_eval-0.1.0.gem ../testdata/safe_eval-0.1.0.gem.out  -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/i18n-1.0.1.gem ../testdata/i18n-1.0.1.gem.out  -c ../config/test_astgen_ruby.config -l ruby
python main.py astgen ../testdata/rack-2.0.5.gem ../testdata/rack-2.0.5.gem.out  -c ../config/test_astgen_ruby.config -l ruby

cd ../testdata


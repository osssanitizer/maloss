# Intro #

This folder contains examples that shows how to use protobuf in each language, 
including serialize and deserialize into/from file in text/binary format, and set/add corresponding fields.


# Dependencies #

- check `maloss/src/install_dep.sh`


# HowTo #

## Run example for each language ##

- run python2 example
    - ```python module_example.py```
    - refer to `maloss/src/static_proxy/astgen.py`
- run python3 example
    - ```python3 module_example3.py```
    - refer to `maloss/src/static_proxy/astgen_py3.py`
- run ruby example
    - ```ruby module_example.rb```
    - refer to `maloss/src/static_proxy/astgen.rb`
- run javascript example
    - ```nodejs module_example.js```
- run php example
    - ```php module_example.php```
    - refer to `maloss/src/static_proxy/astgen.php`    
- run java example
    - refer to `maloss/src/static_proxy/astgen-java`

## Text to binary format conversion and vice versa ##

Since protobuf doesn't support (AFAIK) for serialize/deserialize in text format for language ruby/php/javascript now. 
You need to use the provided *convert.py* to convert text format into binary format and vice versa.

- convert ruby config into binary format
    - ```python convert.py -i ../../../config/astgen_ruby_smt.config -o ../../../config/astgen_ruby_smt.config.pb -t AstLookupConfig```
- convert php config into binary format
    - ```python convert.py -i ../../../config/astgen_php_smt.config -o ../../../config/astgen_php_smt.config.pb -t AstLookupConfig```
- convert javascript config into binary format
    - ```python convert.py -i ../../../config/astgen_javascript_smt.config -o ../../../config/astgen_javascript_smt.config.pb -t AstLookupConfig```
- convert ruby result into text format
    - ```python convert.py -i module_result_rb.pb -o module_result_rb.txt -t ModuleResult -r```
    - ```python convert.py -i module_summary_rb.pb -o module_summary_rb.txt -t ModuleSummary -r```
- convert php result into text format
    - ```python convert.py -i module_result_php.pb -o module_result_php.txt -t ModuleResult -r```
    - ```python convert.py -i module_summary_php.pb -o module_summary_php.txt -t ModuleSummary -r```
- convert javascript result into text format
    - ```python convert.py -i module_result_js.pb -o module_result_js.txt -t ModuleResult -r```
    - ```python convert.py -i module_summary_js.pb -o module_summary_js.txt -t ModuleSummary -r```



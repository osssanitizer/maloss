# Identify the number of maintainers analyzed # 

- For PyPI, NpmJS, Packagist, use email
    - `grep -E -o "\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}\b" pypi.with_stats.with_author.csv | sort -u | wc`
- For RubyGems, use id
    - `grep -E -o "u'id': [0-9]+" rubygems.with_stats.with_author.csv | sort -u | wc`

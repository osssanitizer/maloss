# For first time run, keep INIT=1 in .env for first-time sync. after that, delete it.
```
cd rubygems 
sudo docker-compose --compatibility build
sudo docker-compose --compatibility up
```

# This reuses the official image.
```
cd pypi
sudo docker-compose --compatibility up
```

# For first time run, keep INIT=1 in .env for first-time sync. after that, delete it.
# The data is very large, with over 10+TB. No need to host on a single machine.
# Specifically, copy the mirror/npm/all_npm_pkgs_tarball.{sync_all,latest}.json from the one machine to another, to allow incremental sync
```
cd npm
sudo docker-compose --compatibility build
sudo docker-compose --compatibility up
```


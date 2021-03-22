# Intro #

Use sysdig to trace application behaviors.


# HowTo #

- run docker sysdig
    - `sudo docker-compose up -d`
- run docker falco
    - `sudo docker-compose -f docker-compose-falco.yml up -d`


# Notice #

- sysdig 0.22.1 is compatible with falco 0.11.1.
- sysdig 0.23.1 is compatible with falco 0.12.1.
- sysdig 0.24.1 is compatible with falco 0.13.0.
- sysdig 0.24.2 is compatible with falco 0.14.0.
- sysdig 0.27.1 is compatible with falco 0.27.0


# References #

- [Start containers automatically](https://docs.docker.com/v17.09/engine/admin/start-containers-automatically/#use-a-restart-policy)
    - `docker run -dit --restart unless-stopped redis`
- Restart process automatically using a process manager
    - upstart, systemd, supervisor
- Using a process manager inside containers
    - Process managers can also run within the container to check whether a process is running and starts/restart it if not.


# Example falco rules #

- falco configuration
    - `falco.yaml`
- default falco rules
    - `falco_rules.yaml`
    - [latest copy](https://raw.githubusercontent.com/falcosecurity/falco/dev/rules/falco_rules.yaml)
- customized falco rules
    - `falco_rules.local.yaml`

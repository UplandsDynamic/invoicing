Before starting for the first time:

    mkdir -p /apps/docker_persistent_volumes/aninstance-invoicing/media/protected;
    mkdir -p /apps/docker_persistent_volumes/aninstance-invoicing/media/logo;
    mkdir -p /apps/docker_persistent_volumes/aninstance-invoicing/sqlite;

    And if using a db other than sqlite:
      mkdir -p /apps/docker_persistent_db/aninstance-invoicing;
      chown -R aninstance /apps/docker_persistent_db/aninstance-invoicing;
      chmod -R 700 /apps/docker_persistent_db/aninstance-invoicing;

    # users and groups
    # uid 1000 will be local unprivileged user running docker
    # uid 1010 matches user in container 'aninstance', running django app inside container

    groupadd -g 1010 aninstance;
    useradd -u 1010 -g 1010 -r aninstance; # -r flag creates a system user, with no passwd, no shell account, no home dir.
    groupadd -g 1000 dan;
    useradd -u 1000 -g 1000 -r dan;
    usermod -a -G docker dan; # docker will be run as unprivileged user dan, so add dan to the docker group
    chmod 700 /apps/docker_persistent_db;
    chmod 700 /apps/docker_persistent_volumes/aninstance-invoicing/media/protected;
    chmod 700 /apps/docker_persistent_volumes/aninstance-invoicing/sqlite;
    chown 1010 /apps/docker_persistent_volumes/aninstance-invoicing/sqlite;
    chown 1010 /apps/docker_persistent_volumes/aninstance-invoicing/media/protected;
    chown 1010 /apps/docker_persistent_volumes/aninstance-invoicing/media/logo;
    chown -R 1000 /apps/aninstance-invoicing;
    chown -R 1010 /apps/docker_persistent_volumes/aninstance-invoicing;
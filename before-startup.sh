#!/bin/bash
## TO BE RUN WITHIN CONTAINER WHEN CONTAINER RUNNING!
python3.5 /home/docker/code/manage.py makemigrations;
python3.5 /home/docker/code/manage.py makemigrations invoicing;
python3.5 /home/docker/code/manage.py migrate;
python3.5 /home/docker/code/manage.py collectstatic --noinput;
python3.5 /home/docker/code/manage.py makemessages -l en_GB && \
python3.5 /home/docker/code/manage.py compilemessages;
python3.5 /home/docker/code/manage.py rebuild_index --noinput;
chown -R aninstance /home/docker/docker_persistent_volumes;
chown -R aninstance /home/docker/code/aninstance
chown 1000:aninstance /home/docker/code
redis-cli -h redis flushall;
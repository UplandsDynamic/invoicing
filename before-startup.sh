#!/bin/bash
## TO BE RUN WITHIN CONTAINER WHEN CONTAINER RUNNING!
# change git to lower version whilst template creation bug persists
/usr/bin/git -C /usr/local/lib/python3.5/dist-packages/django-git checkout stable/1.10.x && \
# update very latest django from from git to patch bugs etc
/usr/bin/git -C /usr/local/lib/python3.5/dist-packages/django-git pull -a; && \
rm -rf /usr/local/lib/python3.5/dist-packages/django && \
cp -R /usr/local/lib/python3.5/dist-packages/django-git/django /usr/local/lib/python3.5/dist-packages/django;
python3.5 /home/docker/code/manage.py makemigrations;
python3.5 /home/docker/code/manage.py makemigrations invoicing;
python3.5 /home/docker/code/manage.py migrate;
python3.5 /home/docker/code/manage.py collectstatic --noinput;
python3.5 /home/docker/code/manage.py makemessages -l en_GB && \
python3.5 /home/docker/code/manage.py compilemessages;
python3.5 /home/docker/code/manage.py rebuild_index --noinput;
chown -R aninstance /home/docker/code/aninstance/whoosh_index;
chown -R aninstance /home/docker/docker_persistent_volumes;
redis-cli -h redis flushall;
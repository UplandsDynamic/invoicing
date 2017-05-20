FROM ubuntu:16.04
MAINTAINER Dan Bright email: productions@aninstance.com
# change to bash
RUN rm /bin/sh && ln -s /bin/bash /bin/sh
# Install required packages and remove the apt packages cache when done.
RUN apt update && apt install -y \
python3-dev \
libpq-dev \
libffi-dev \
libcairo2 \
libcairo2-dev \
pango-1.0 \
gettext \
python3-pip \
python3-setuptools \
nginx \
supervisor \
iputils-ping
RUN pip3 install --upgrade pip
# install uwsgi now because it takes a little while
RUN pip3.5 install uwsgi
# install uwsgi plugin
RUN apt install -y uwsgi-plugin-python3
# setup all the config files
COPY aninstance/requirements.txt /home/docker/code/aninstance/
RUN pip3.5 install -r /home/docker/code/aninstance/requirements.txt
VOLUME ["/home/docker/code"]
VOLUME ["/home/docker/docker_persistent_volumes"]
RUN rm -rf /etc/nginx/nginx.conf
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx-app.conf /etc/nginx/sites-available/default
COPY supervisor-app.conf /etc/supervisor/conf.d/
RUN mkdir -p /home/docker/volatile/static
RUN groupadd -g 1010 aninstance
RUN useradd -r -u 1010 -g 1010 -s /bin/false aninstance
RUN mkdir -p /var/log/django_main && chown aninstance /var/log/django_main
RUN touch /var/log/django_main/debug.log
RUN mkdir -p /var/log/django_q && chown aninstance /var/log/django_q
RUN mkdir -p /var/log/uwsgi
RUN chown aninstance /var/log/django_q
RUN chown www-data /var/log/django_main
RUN chown www-data:www-data /var/log/django_main/debug.log
RUN chmod 666 /var/log/django_main/debug.log
RUN chown aninstance /var/log/uwsgi
RUN mkdir -p /sockets && chown aninstance:www-data /sockets \
&& chmod 755 /sockets && chmod g+s /sockets
RUN apt install redis-tools -y;
EXPOSE 80
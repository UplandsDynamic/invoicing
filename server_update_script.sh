## script to update aninstance.com from git repo
git fetch --all;
git reset --hard origin/master;
# set permissions
chown -R aninstance /apps/aninstance-invoicing;
chmod 750 /apps/aninstance-invoicing;
chown -R aninstance:www-data /apps/docker_persistent_volumes/aninstance-invoicing/media/logo;
chmod 700 /apps/docker_persistent_volumes/aninstance-invoicing/media/protected;
chown aninstance:root /apps/docker_persistent_volumes/aninstance-invoicing/media/protected;
chmod +x /apps/aninstance-invoicing/before-startup.sh;
sudo -u dan docker-compose up --force-recreate --build -d;
sudo -u dan docker exec -it aninstanceinvoicing_aninstance_1 /bin/bash /home/docker/code/before-startup.sh;
sudo -u dan docker-compose restart;
echo "Aninstance invoicing invoicing is now updated!";
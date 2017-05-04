#!/bin/bash
## script to flush redis inside the running redis container ...

/usr/bin/docker exec aninstance_redis_1 redis-cli flushall
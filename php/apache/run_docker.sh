#!/bin/bash

# these need to be absolute paths:
PHP_CONFIG=$1

docker run -p 8001:80 --rm -it \
	-v ${PHP_CONFIG}:/var/www/openml/openml_OS/config/BASE_CONFIG.php \
	--network sqlnetwork \
        apache-php

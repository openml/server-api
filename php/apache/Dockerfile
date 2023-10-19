FROM php:7.4.33-apache

RUN docker-php-source extract \
	&& docker-php-ext-install mysqli \
	&& docker-php-source delete

RUN apt-get update \
    && apt-get install -y git \
    && git clone https://github.com/openml/openml /var/www/openml

RUN mv /var/www/openml/openml_OS/config/BASE_CONFIG-BLANK.php /var/www/openml/openml_OS/config/BASE_CONFIG.php

RUN mkdir /var/www/openml/logs
RUN mkdir /data


COPY config/*.load /etc/apache2/mods-enabled/
COPY config/api.conf /etc/apache2/sites-enabled/000-default.conf
COPY config/php.ini /user/local/etc/php/
COPY config/.htaccess /var/www/openml/.htaccess

RUN mkdir /scripts
COPY set_configuration.sh /scripts/

ENTRYPOINT ["bash", "/scripts/set_configuration.sh"]
#ENTRYPOINT ["apache2-foreground"]

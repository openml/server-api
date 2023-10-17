# Running apache php backend locally

1. checkout the php code to a directory (/yourpath/to/php_root)
2. update /yourpath/to/php_root/.htaccess: remove the `RedirectMatch 301`
3. create /yourpath/to/php_root/openml_OS/config/BASE_CONFIG.php (copy the BASE_CONFIG_BLANK.php) and configure the database etc.
4. Set `define('ENVIRONMENT', 'development');` in /yourpath/to/php_root/index.php so that you'll get errors

```bash
./build_docker.sh
./run_docker.sh /yourpath/to/php_root /path/to/a/data/directory
```

Go to http://localhost:8001/home

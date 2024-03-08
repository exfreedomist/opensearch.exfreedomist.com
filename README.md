# opensearch.exfreedomist.com

Here is source of open version of torrents search engine (which use **[api.exfreedomist.com](https://api.exfreedomist.com)**).

# Structure

```
opensearch.exfreedomist.com
├── core (Python FastAPI routers)
├── static
    ├── css
    ├── images
    └── js
├── templates (HTML Jinja templates)
├── .env
├── docker-compose.yml (build)
└── main.py (entry point)
```

# Dependencies

`Linux/Ubuntu`. In your system must be installed:
* **Redis** database _(do not forget to change the settings in `.env`)_. Need for correct cache subsystem working.
* **Docker-compose** ver. 3.3

# Deploy

```
docker-compose up --build -d
```

In this case you get local instance of search engine. Try in your browser:
```commandline
http://localhost:31337
```
_(by default port is `31337`)_


# .env

Setup your instance.

For API endpoints and base redis settings clearly.

* `redis_ex_sec` is time in seconds for decay redis board labels cache _(by default 1 week)_
* `redis_ex_cache_sec` is time in seconds for decay redis magnets cache _(by default 15 minutes)_
* `token` is for API endpoints requests. You can setup your personal token for debug cases.
* `token` is for API endpoints requests. You can setup your personal token for debug cases.
* `static_prefix` is path to static files. By default if `/static` and shared from container, but you can use this server behind Nginx and put static files to other dir.

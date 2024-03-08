FROM python:3.11-slim-buster
LABEL tag="opensearch.exfreedomist.com:latest" author="Captain Freedomist"

RUN apt update

RUN python3 -m pip install --upgrade pip
RUN python3 -m pip install python-decouple uvicorn httpx ua-parser user-agents
RUN python3 -m pip install python-multipart fastapi-utils jinja2 pathlib redis

ADD ./ /usr/src/app/
WORKDIR /usr/src/app

CMD [ "/bin/bash" ]

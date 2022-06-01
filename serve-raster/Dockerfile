FROM ubuntu

# Switch to root user for package installs
USER 0

RUN apt-get -y update --fix-missing && apt-get -y upgrade && TZ="Etc/UTC" DEBIAN_FRONTEND="noninteractive" apt-get -y install python3 python3-venv python3-pip curl

# Install poetry https://python-poetry.org/docs/#installation
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -

# Poetry needs somewhere to store it's virtual environment
ENV HOME=/usr/local/poetry
RUN mkdir -p $HOME
RUN chown 1001:1001 $HOME

# Switch back to default user
USER 1001

# Copy files for poetry
COPY ./poetry.lock /usr/local/src
COPY ./pyproject.toml /usr/local/src

# Install dependencies using poetry virtual environment 
WORKDIR /usr/local/src
RUN /opt/poetry/bin/poetry run python -m pip install --upgrade pip
RUN /opt/poetry/bin/poetry install --no-root --no-dev

EXPOSE 8000

# Copy source files
COPY ./serve_raster/*.py /usr/local/src/serve_raster/
CMD ["/opt/poetry/bin/poetry", "run", "uvicorn", "--host", "0.0.0.0", "serve_raster.main:app"]
FROM ubuntu

# Install pre-requisites
RUN apt-get -y update --fix-missing && apt-get -y upgrade && TZ="Etc/UTC" DEBIAN_FRONTEND="noninteractive" apt-get -y install libgdal-dev curl build-essential libbz2-dev libreadline-dev libffi-dev git python3 python3-venv python3-pip

# Install poetry https://python-poetry.org/docs/#installation
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -

# Install pyenv (easiest way to get python 3.8.13???)
RUN curl https://pyenv.run | bash
# Install python 3.8.13
RUN /root/.pyenv/bin/pyenv install 3.8.13
RUN /root/.pyenv/bin/pyenv global 3.8.13
RUN /root/.pyenv/bin/pyenv which python

# Copy files for poetry
COPY ./poetry.lock /usr/local/src
COPY ./pyproject.toml /usr/local/src

# Install dependencies using poetry virtual environment 
RUN cd /usr/local/src && /opt/poetry/bin/poetry env use /root/.pyenv/versions/3.8.13/bin/python && /opt/poetry/bin/poetry run python -m pip install --upgrade pip
RUN cd /usr/local/src && /opt/poetry/bin/poetry env use /root/.pyenv/versions/3.8.13/bin/python && /opt/poetry/bin/poetry install --no-root --no-dev
RUN cd /usr/local/src && /opt/poetry/bin/poetry run python -m pip install gdal==$(gdal-config --version)

# Copy source files
COPY ./fire_perimeter/*.py /usr/local/src/fire_perimeter/
WORKDIR /usr/local/src
CMD ["/opt/poetry/bin/poetry", "run", "python", "-m", "fire_perimeter.client"]
FROM pypy:3.10-bookworm

# Install packages required for psycopg2
RUN apt-get update && apt-get install -y gcc musl-dev

WORKDIR /src

COPY ./requirements.txt /src/requirements.txt

RUN pip3 install --upgrade pip

RUN pip3 install --no-cache-dir -r ./requirements.txt

# Create /uploads directory in /tmp and grant permissions
RUN mkdir -p /tmp/uploads && chmod 777 /tmp/uploads

ENV PYTHONIOENCODING=UTF-8

COPY . /src/

# Expose the Flask app port
EXPOSE 5000

CMD [ "honcho", "start" ]
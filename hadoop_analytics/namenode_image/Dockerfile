# Dockerfile for namenode
FROM bde2020/hadoop-namenode:2.0.0-hadoop3.2.1-java8

RUN echo "deb http://archive.debian.org/debian stretch main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security stretch/updates main contrib non-free" >> /etc/apt/sources.list && \
    apt-get update -o 'Acquire::Check-Valid-Until=false' --allow-unauthenticated && \
    apt-get install -y python3 && \
    rm -rf /var/lib/apt/lists/*

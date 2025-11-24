# Start from the base bde2020 nodemanager image
FROM bde2020/hadoop-nodemanager:2.0.0-hadoop3.2.1-java8

# 1. Rewrite the sources.list to point to the official Debian archive for "Stretch"
# This is necessary because Debian 9 "Stretch" is End-of-Life.
RUN echo "deb http://archive.debian.org/debian stretch main contrib non-free" > /etc/apt/sources.list && \
    echo "deb http://archive.debian.org/debian-security stretch/updates main contrib non-free" >> /etc/apt/sources.list

# 2. Update the package lists.
# We must ignore expired "Valid-Until" headers and allow unauthenticated packages
# because the archive repositories are not actively maintained. This replaces the
# --allow-releaseinfo-change flag, which is not supported on this old apt version.
RUN apt-get update -o 'Acquire::Check-Valid-Until=false' --allow-unauthenticated

# 3. Install Python 3
RUN apt-get install -y python3
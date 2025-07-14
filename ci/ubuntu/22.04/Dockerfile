FROM ubuntu:22.04

RUN mkdir -p /opt/built

# prevent failures due to interactive apt transactions
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -y update
RUN apt-get -y upgrade --no-install-recommends

# Copy and install packages from the latest opentestpoint build
WORKDIR /opt
RUN mkdir -p dependencies
COPY --from=gcr.io/automated-builds-303920/ubuntu22.04.emane /opt/built/* dependencies/
COPY --from=gcr.io/automated-builds-303920/ubuntu22.04.waveform-resource /opt/built/* dependencies/
RUN dpkg -i dependencies/*; apt-get -y -f install

# Build tools and dependencies
RUN apt-get -y install git gcc g++ autoconf automake libtool dh-python debhelper python3-setuptools \
                       build-essential protobuf-compiler

RUN git clone https://github.com/adjacentlink/emane-jammer-simple -b develop

WORKDIR emane-jammer-simple
RUN ./autogen.sh && ./configure && make deb
RUN cp $(find .debbuild -name "*\.deb") /opt/built
RUN dpkg -i /opt/built/*; apt-get -y install -f

RUN echo 'complete'

FROM fedora:41

RUN mkdir -p /opt/built

RUN dnf -y update

# Copy and install packages from the latest upsteam dependencies
WORKDIR /opt
RUN mkdir -p dependencies
COPY --from=gcr.io/automated-builds-303920/fedora41.emane /opt/built/* dependencies/
COPY --from=gcr.io/automated-builds-303920/fedora41.waveform-resource /opt/built/* dependencies/
RUN dnf -y install dependencies/*\.rpm

# Build tools and depends
RUN dnf -y install git gcc-c++ make autoconf automake libtool rpm-build python3-setuptools \
                   libxml2-devel python3-devel python3-protobuf protobuf-devel zeromq-devel

RUN git clone https://github.com/adjacentlink/emane-jammer-simple -b develop

WORKDIR emane-jammer-simple
RUN ./autogen.sh && ./configure && make rpm
RUN cp $(find .rpmbuild/RPMS -name "*\.rpm") /opt/built
RUN dnf -y install /opt/built/*

RUN dnf clean all

RUN echo 'complete'

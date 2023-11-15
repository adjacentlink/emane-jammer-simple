emane-jammer-simple
==

# Overview

The emane-jammer-simple project provides information and examples for
using the `emanesh.ota.otapublisher` Python module to generate
over-the-air (OTA) messages in order to jam radio model instances.

# Common PHY Header

EMANE physical layer instances are interconnected using an OTA
multicast channel. All OTA messages are processed by every physical
layer instance listening on the same channel. OTA messages contain a
physical layer header, known as the Common PHY Header, which is used
to account for signal propagation, antenna effects and interference
sources across heterogeneous radio models.

Jamming in EMANE is a function of manipulating the Common PHY Header
of packets generated using NEM ids representing jamming sources and
setting the appropriate propagation model inputs (pre-computed
pathloss or location) for those sources in relationship to other NEMs
participating in the emulation.

The [Common PHY Header][commonphyheader] is defined using Google
Protocol Buffers and contains the following information:

1. The NEM id and power level in dBm of every transmitter
   simultaneously transmitting the message (collaborative
   transmission).

2. The frequency (Hz), offset from start-of-transmission time
   (microseconds), duration (microseconds) and optional power (dBm) of
   each of the segments composing the single OTA message.

3. The registration id and sub id of the transmitting waveform.

4. The OTA sequence number of the message.

5. The bandwidth of the transmitter (Hz).

6. The start-of-transmission time (microseconds) since the Epoch,
   1970-01-01 00:00:00 +0000 (UTC).


# Simple Jamming Technique

The EMANE distribution contains a Python module that can be used to
implement a simple jammer: `emanesh.ota.otapublisher`. This module
defines the `OTAPublisher` class that is instantiated with an OTA
multicast channel endpoint and provides a `publish` method used to
generate OTA messages containing only a Common PHY Header.

These messages can be used to inject energy at specific frequencies in
order to jam radio model instances by increasing the amount of
interference (noise) they see.

## Jamming Scenario Support

The `emaneota-publisher` utility available as part of the standard
EMANE distribution, uses the `OTAPublisher` to generate messages
defined via a time based [XML][otapublihserschema] scenario:

```xml
<otapublisherscenario>
  <flow registrationid='65535' 
        subid='65535' 
        rate='20' 
        start='0' 
        end='6000'
        source='11' 
        destination='65535' 
        bandwidth='20000000' 
        fixedgain='0'>
    <segments>
      <segment frequency='2347000000'
               offset='0'
               duration='100000'/>
    </segments>
    <transmitters>
      <transmitter nem='11'
                   power='0'/>
    </transmitters>
  </flow>
</otapublisherscenario>
```

The above OTA Publisher scenario illustrates a single publisher flow
with the following attributes:

1. `registrationid` and `subid`: Both are inconsequential as long as
   they are not set to the same value used by any other radio model
   participating in the emulation on the same OTA multicast channel.

2. `rate`: The number of OTA messages per second.

3. `start`: The timestamp in seconds to start the flow. Relative to
   application start time.

4. `end`: The timestamp in seconds to stop the flow. Relative to
   application start time.

5. `source`: The NEM id of the publisher. This should be a unique NEM
   id not used by any other node in the emulation.

6. `destination:` The NEM id of the destination. This value should
   most likely be set to the NEM broadcast address 65535.

7. `bandwidth`: Bandwidth of the transmitter in Hz.

8. `fixedgain`: Optional fixed gain value in dBi. The absence of
   `fixedgain` indicates the use of antenna profiles.

9. `segments`: One or mode `segment` entries containing the following:

    1. `frequency`: Center frequency of the segment in Hz.

    2. `offset`: Offset of the segment from the start-of-transmission
       in microseconds.

    3. `duration`: Duration of the segment in microseconds.

10. `transmitters`: One or more `transmitter` entries containing the
    following:

    1. `nem`: NEM id of the transmitter. This usually matches the
    `source` NEM id of the publisher.

    2. `power`: The transmit power in dBm.

Information on using `emaneota-publisher` can be found via
`emaneota-publisher --help`.

## Spectrum Energy Overlap

Taking a closer look at the above OTA Publisher scenario XML, the flow
as defined will generate an OTA Message with a duration of 100
milliseconds every 50 milliseconds. This flow is overlapping the
spectrum energy to ensure a continuous tone.

This technique is possible because the emulator physical layer will
not add energy into the same spectrum window bin more than once per
transmitting NEM, so overlapping will not increase the energy level
but will reduce the possibility of gaps due to operating system
scheduler fluctuation.

## Building A Jammer

The `emane-jammer-simple` utility contained in this project
illustrates how to use `emanesh.ota.otapublisher` to build a jammer.

The `OTAPublisher` class is instantiated with the OTA multicast
channel group, port and optional device.

```python
publisher = OTAPublisher((args['group'],
                          args['port'],
                          args['device']),)
```

OTA Messages are instantiated with the following parameters:

1. `source`: The NEM id of the publisher. This should be a unique NEM
   id not used by any other node in the emulation.

2. `destination`: The NEM id of the destination. This value should
   most likely be set to the NEM broadcast address 65535.

3. `registrationId`: Registration id of the transmitter.
   Inconsequential as long as not set to the same value used by any
   other radio model participating in the emulation on the same OTA
   multicast channel.

4. `subId`: Sub id of the transmitter. Inconsequential.

5. `bandwidth`: Bandwidth of the transmitter in Hz.

6. `transmitters`: List of tuples containing the following:

    1. NEM id of transmitter.

    2. Transmission power in dBm.

7. `segments`: List of tuples containing the following:

    1. Center frequency in Hz.

    2. Offset from the start-of-transmission in microseconds.

    3. Duration of segment in microseconds.

8. `fixedAntennaGain`: Fixed antenna gain in dBi or `None` for antenna
   profiles.

```python
msg = OTAMessage(args['nem'], # src
                 65535, # destination
                 65535, # registration id
                 65535, # sub id
                 args['bandwidth'], # bandwidth
                 [(args['nem'],args['power'])],
                 [(freq,0,1000000) for freq in args['frequency']],
                 0) # fixed antenna gain
```

Messages are sent using the `publish` method which takes the following
parameters:

1. `msg`: `OTAMessage` instance.

2. `time`: Start-of-transmission time in microseconds since the Epoch.

```python
publisher.publish(msg,int(time.time() * 1000000))
```

Information on using `emane-jammer-simple` can be found via
`emane-jammer-simple --help`.

# Propagation Model Inputs

Each jamming publisher needs a unique NEM Id. Other radio models
participating in the emulation process jammer generated OTA messages
as noise like all other out-of-band messages.

Radio models will need pre-computed pathloss information or location
information for any jamming publisher (NEM ids used for transmitters)
participating in the emulation, based on physical layer propagation
model selection.

# Simple Jammer Service

The `emane-jammer-simple-service` is a simple
[waveform-resource][waveformresource] service which uses a
[ZeroMQ][zeromq] request-reply pattern to control a jamming source.

`emane-jammer-simple-service` uses an XML configuration file to
specify service listen endpoint and emane OTA channel and message
parameters:

```xml
    <emane-jammer-simple-service endpoint='0.0.0.0:45715'>
      <ota-channel group='224.1.2.8'
                   port='45702'
                   device='backchan0'/>
      <ota-message destination='65535'
                   registration-id='65535'
                   sub-id='65535'/>
    </emane-jammer-simple-service>
```

Where,

1. `endpoint`: service listen endpoint

2. `ota-channel`: Configuration for the EMANE OTA channel

    1. `group`: OTA multicast group. See
       [otamanagergroup](https://github.com/adjacentlink/emane/wiki/Configuring-the-Emulator#otamanagergroup).
  
    2. `port`: OTA multicast port. See
       [otamanagergroup](https://github.com/adjacentlink/emane/wiki/Configuring-the-Emulator#otamanagergroup).
  
    3. `device`: See
       [otamanagerdevice](https://github.com/adjacentlink/emane/wiki/Configuring-the-Emulator#otamanagerdevice)
  
3. `ota-message`: Configuration for static message fields when
   publishing OTA messages

    1. `destination`: Destination of the OTA message. For most cases
       use broadcast 65535.
  
    2. `registration-id`: Registration id of the OTA physical
       layer. For most cases used 65535.
  
    3. `sub-id`: See
       [subid](https://github.com/adjacentlink/emane/wiki/Physical-Layer-Model#subid).


Sample `emane-jammer-simple-service` usage:

```
$ emane-jammer-simple-service \
   --config-file emane-jammer-simple-service.xml \
   --log-file /path/to/emane-jammer-simple-service.log \
   --pid-file /path/to/emane-jammer-simple-service.pid \
   --daemonize
```

`emane-jammer-simple-service` [request and response messages][api] are
defined using [Google Protocol Buffers][protobuf] and the
`emane-jammer-simple-control` script servers as an example for using
the API.

Sample `emane-jammer-simple-control` client usage:

```
$ emane-jammer-simple-control \
   jammer-node:45715 \
   on \
   4 \
   2360000000,5 \
   2460000000,5 \
   2410000000,5 \
   -a omni

$ emane-jammer-simple-control jammer-node:45715 off
```

# Need more information?

Visit the EMANE Wiki:

 https://github.com/adjacentlink/emane/wiki

[commonphyheader]: https://github.com/adjacentlink/emane/blob/master/src/libemane/commonphyheader.proto

[otapublihserschema]: https://github.com/adjacentlink/emane/blob/master/src/emanesh/emanesh/schema/otapublisherscenario.xsd

[zeromq]: https://zeromq.org 

[waveformresource]: https://github.com/adjacentlink/waveform-resource

[protobuf]: https://protobuf.dev/

[api]: https://github.com/adjacentlink/emane-jammer-simple/blob/develop/emane_jammer_simple/service/emane-jammer-simple.proto

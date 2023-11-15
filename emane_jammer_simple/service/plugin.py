# Copyright (c) 2023 - Adjacent Link LLC, Bridgewater, New Jersey
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in
#    the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of Adjacent Link LLC nor the names of its
#    contributors may be used to endorse or promote products derived
#    from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# See toplevel COPYING for more information.

import time
import zmq
import emane
import functools
from lxml import etree
from pkg_resources import resource_filename
from waveform_resource.interface.plugin import Plugin as BasePlugin
import emane_jammer_simple.service.emane_jammer_simple_pb2 as emane_jammer_simple_pb2
import logging

from emane.ota import OTAMessage
import uuid

class Plugin(BasePlugin):
    def initialize(self,ctx,configuration_file):
        """Initializes the scheduler service.

        Args:
          ctx (obj) Context instance.

          configuration_file (str): Plugin configuration files.

        Raises:
          RuntimeError: If a schema error is encountered.

        """
        tree = etree.parse(configuration_file)

        root = tree.getroot()

        schemaDoc = etree.parse(resource_filename('emane_jammer_simple.service',
                                                  'schema/service.xsd'))

        schema = etree.XMLSchema(etree=schemaDoc,attribute_defaults=True)

        if not schema(root):
            message = []
            for entry in schema.error_log:
                message.append('{}: {}'.format(entry.line,entry.message))
            raise RuntimeError('\n'.join(message))

        endpoint = root.get('endpoint');
        logging.info('endpoint = {}'.format(endpoint))

        e_ota_channel = root.xpath('/emane-jammer-simple-service/ota-channel')[0]
        self._ota_group = e_ota_channel.get('group')
        logging.info('ota-channel group = {}'.format(self._ota_group))

        self._ota_port = int(e_ota_channel.get('port'))
        logging.info('ota-channel port = {}'.format(self._ota_port))

        ota_device = e_ota_channel.get('device')
        logging.info('ota-channel device = {}'.format(ota_device))

        e_ota_message = root.xpath('/emane-jammer-simple-service/ota-message')[0]

        self._ota_message_destination = int(e_ota_message.get('destination'))
        logging.info('ota-message destination = {}'.format(self._ota_message_destination))

        self._ota_message_registration_id = int(e_ota_message.get('registration-id'))
        logging.info('ota-message registration = {}'.format( self._ota_message_registration_id))

        self._ota_message_sub_id = int(e_ota_message.get('sub-id'))
        logging.info('ota-message sub-id = {}'.format(self._ota_message_sub_id))

        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REP)
        self._socket.bind('tcp://{}'.format(endpoint))
        self._ota_channel_id = ctx.create_channel_multicast(group=self._ota_group,
                                                            group_port=self._ota_port,
                                                            device=ota_device)

        self._uuid = uuid.uuid4()
        self._ota_sequence = 0
        self._request_sequence = 0
        self._ota_msg = None

    def start(self,ctx):
        """Starts the service.

        Args:
          ctx (obj): Context instance.

        """
        ctx.add_fd(self._socket.fileno(),
                   functools.partial(self._handle_request,ctx))


    def stop(self,ctx):
        """Stops the service.

        Args:
          ctx (obj): Context instance.
        """
        ctx.remove_fd(self._socket.fileno())

    def destroy(self,ctx):
        """Destroys the service.

        Args:
          ctx (obj): Context instance.

        """
        self._socket.close()
        self._context.destroy()
        ctx.delete_channel(self._ota_channel_id)

    def _handle_request(self,ctx):
        # ZMQ_EVENTS == 15
        zevents = self._socket.getsockopt(15)

        if zevents & zmq.POLLIN:
            data = self._socket.recv()

            success = True
            description='ok'

            m = emane_jammer_simple_pb2.Request()

            m.ParseFromString(data)

            logging.info(m)

            if m.type == emane_jammer_simple_pb2.Request.COMMAND_ON:
                if m.HasField('on'):
                    if m.on.duty_cycle_percent == 100:
                        # 100% duty cycle is a CW tone -- special case
                        # optimization to reduce the number of OTA
                        # messages AND to try and prevent gaps by
                        # overlapping messages (note: physical layer
                        # at receiver has logic to correctly handle
                        # overlap, ignores energry from the same
                        # transmitter in the same time bin)
                        self._ota_on_duration_microseconds = 1000000
                        self._ota_period_seconds = .8
                    else:
                        self._ota_on_duration_microseconds = int(m.on.period_microseconds *  (m.on.duty_cycle_percent / 100.0))
                        self._ota_period_seconds = m.on.period_microseconds / 1000000

                    logging.info('on duration: {}'.format(self._ota_on_duration_microseconds))
                    logging.info('period: {}'.format(self._ota_period_seconds))

                    self._ota_msg = OTAMessage(m.on.nem_id, # src
                                               self._ota_message_destination,
                                               self._ota_message_registration_id,
                                               self._ota_message_sub_id,
                                               m.on.bandwidth_hz,
                                               [(m.on.nem_id,0)],
                                               [(freq.frequency_hz,0,self._ota_on_duration_microseconds,freq.power_dBm) for freq in m.on.frequencies],
                                               m.on.antenna.fixed_gain_dBi if m.on.antenna.type == m.on.antenna.ANTENNA_IDEAL_OMNI else None,
                                               m.on.spectral_mask_index)

                    self._request_sequence += 1
                    self._send_next(ctx,0,self._request_sequence)

                else:
                    description='malformed on request missing Request.on'
                    success = False

            elif m.type == emane_jammer_simple_pb2.Request.COMMAND_OFF:
                if m.HasField('on'):
                    description='malformed off request has Request.on'
                    success = False
                else:
                    if self._ota_msg:
                        self._request_sequence += 1
                        self._ota_msg = None

            response = emane_jammer_simple_pb2.Response()

            response.success = success

            if not success:
                response.description = description

            self._socket.send(response.SerializeToString())


    def _send_next(self,ctx,timer_id,current_request_sequence):
        now = time.time()

        if current_request_sequence == self._request_sequence:
            timestamp = int(now * 1000000)
            ctx.channel_send(self._ota_channel_id,
                             self._ota_msg.generate(int(now * 1000000),
                                                    self._ota_sequence,
                                                    self._uuid))

            self._ota_sequence += 1

            # create an enclosed capture of the current request
            # sequence we are handling so we can handle update (new
            # request) and off
            def f():
                current_request_sequence = self._request_sequence
                def ff(ctx,timer_id):
                    nonlocal current_request_sequence
                    self._send_next(ctx,timer_id,current_request_sequence)

                ctx.create_timer(now + self._ota_period_seconds,ff)

            f()

            logging.debug('ota publish at {} next publish at {} for {}'.format(now,
                                                                               now + self._ota_period_seconds,
                                                                               current_request_sequence))
        else:
            logging.info('ota publish was scheduled for request {} but now request {}, skipping'.format(current_request_sequence,
                                                                                                        self._request_sequence))

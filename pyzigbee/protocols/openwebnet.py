#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Legrand France
# All rights reserved

import re
import logging
from pyzigbee.core.log import NullHandler
from pyzigbee.core.exceptions import PyZigBeeBadFormat
from pyzigbee.protocols.baseprotocol import BaseProtocol


OWN_ACK = "*#*1##"
OWN_NACK = "*#*0##"


class OWNProtocol(BaseProtocol):
    """
    OWN protocol is in charge of decoding/encoding OpenWebNet frames
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(NullHandler())

    def _build_where_field(self, zigbee_id=None):
        if zigbee_id is None:
            return ""
        else:
            return zigbee_id

    def handle_error(self, expected, received):
        """
        Handler called on error when expected data differs from received one
        """
        self.logger.warn("frame error (expected:%s , received: %s)", expected, received)
        raise PyZigBeeBadFormat("Frame error: received '%s' when "
                                      "expected was '%s'" % (received, expected))

    def check_answer(self, answer):
        """
        Handler called on received answer
        """
        if answer == OWN_NACK:
            self._raise_format_error("NACK received", answer)
        return answer

    def _raise_format_error(self, msg, data):
        if data == OWN_NACK:
            self.logger.debug("OWN: received NACK (%s)", OWN_NACK)
        self.logger.warn("OWN format error: %s (data: %s)", msg, data)
        raise PyZigBeeBadFormat("OWN: %s (data: %s)" % (msg, data))

    def get_info(self):
        return {"description": "OpenWebNet protocol"}

    def get_end_of_frame_sep(self):
        return "##"

    def encode_get_dev_number(self, delay=5):
        """
        Build the frames sequence to get the number of devices
        delay: number of seconds to wait for an answer
        """
        return [{"tx": "*13*65*##"},
                {"rx": OWN_ACK},
                {"delay": delay},
                {"answer": ""}]

    def decode_dev_number(self, data):
        """
        Decode the given data to find the number of devices
        """
        m = re.match("\*\#13\*\*67\*(\S+)\#\#", data)
        if m is not None:
            dev_nb = int(m.group(1))
            self.logger.debug("number of devices: %d", dev_nb)
            return dev_nb
        else:
            self._raise_format_error("could not extract device number from frame", data)

    def encode_get_dev_id(self, dev_index):
        """
        Build the frames sequence to get the device ID from
        a given device index
        """
        return [{"tx": "*#13**73#%d##" % dev_index},
                {"answer": ""},
                {"rx": OWN_ACK}, ]

    def decode_dev_id(self, data):
        """
        Decode the given data to find the device ID
        """
        m = re.match("\*\#13\*(.*)\#.*\#.*\#\#", data)
        if m is not None:
            dev_id = m.group(1)
            self.logger.debug("device ID: %s", dev_id)
            return dev_id
        else:
            self._raise_format_error("could not extract device ID from frame", data)

    def encode_get_firmware_version(self, zigbee_id=None):
        """
        Build the frames sequence to get the firmware version of the gateway
        """
        return [{"tx": "*#13*%s*16##" % self._build_where_field(zigbee_id)},
                {"answer": ""},
                {"rx": OWN_ACK}]

    def encode_get_hardware_version(self, zigbee_id=None):
        """
        Build the frames sequence to get the firmware version of the gateway
        """
        return [{"tx": "*#13*%s*17##" % self._build_where_field(zigbee_id)},
                {"answer": ""},
                {"rx": OWN_ACK}]

    def decode_firmware_version(self, data, zigbee_id=None):
        return self._decode_version(data, "16", zigbee_id)

    def decode_hardware_version(self, data, zigbee_id=None):
        return self._decode_version(data, "17", zigbee_id)

    def _decode_version(self, data, code="16", zigbee_id=None):
        """
        Decode the given data to find the version
        """
        escaped_id = re.escape(self._build_where_field(zigbee_id))
        m = re.match("\*\#13\*%s\*%s\*(\S+)\*(\S+)\*(\S+)\#\#" % (escaped_id, code), data)
        if m is not None:
            version = m.group(1) + "." + m.group(2) + "." + m.group(3)
            self.logger.debug("version: %s", version)
            return version
        else:
            self._raise_format_error("could not extract version from frame", data)

    def decode_binding_id(self, data):
        """
        Decode binding ID from the given data
        """
        m = re.match("\*25\*35\*(\S+)\#9\#\#", data)
        if m is not None:
            binding_id = m.group(1)
            self.logger.debug("binding ID: %s", binding_id)
            return binding_id
        else:
            self._raise_format_error("could not extract binding ID from frame", data)

    def encode_binding_request(self, zigbee_id):
        """
        Encode binding request for a given zigbee ID
        """
        zigbee_id = self._build_where_field(zigbee_id)
        return [{"tx": "*25*33*%s#9##" % zigbee_id},
                {"rx": OWN_ACK},
                {"rx": "*25*36*%s#9##" % zigbee_id}]

    def encode_unbinding_request(self, zigbee_id):
        """
        Encode unbinding request for a given zigbee ID
        """
        zigbee_id = self._build_where_field(zigbee_id)
        return [{"tx": "*25*34*%s#9##" % zigbee_id},
                {"rx": OWN_ACK},
                {"rx": "*25*36*%s#9##" % zigbee_id}]

#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Legrand France
# All rights reserved

import time
import logging
from pyzigbee.core.log import NullHandler
from pyzigbee.core.exceptions import PyZigBeeBadArgument
from pyzigbee.core.exceptions import PyZigBeeFailed
from pyzigbee.core.exceptions import PyZigBeeException
from pyzigbee.drivers.basedriver import BaseDriver
from pyzigbee.protocols.baseprotocol import BaseProtocol


class Gateway(object):
    """
    Gateways abstracts access to real devices
    """

    def __init__(self, driver, protocol, description=""):
        self.set_driver(driver)
        self.set_protocol(protocol)
        self.description = description
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(NullHandler())

    def set_driver(self, driver):
        if isinstance(driver, BaseDriver):
            self.driver = driver
        else:
            raise PyZigBeeBadArgument("%s is not a subclass of BaseDriver"
                                      % driver)

    def set_protocol(self, protocol):
        if isinstance(protocol, BaseProtocol):
            self.protocol = protocol
        else:
            raise PyZigBeeBadArgument("%s is not a subclass of BaseProtocol"
                                      % protocol)

    def get_info(self):
        return {'description': self.description,
                'driver': self.driver.get_info(),
                'protocol': self.protocol.get_info()}

    def get_firmware_version(self, zigbee_id=None):
        sequence = self.protocol.encode_get_firmware_version(zigbee_id)
        answer = self._get_answer(sequence)
        return self.protocol.decode_firmware_version(answer, zigbee_id)

    def get_hardware_version(self, zigbee_id=None):
        sequence = self.protocol.encode_get_hardware_version(zigbee_id)
        answer = self._get_answer(sequence)
        return self.protocol.decode_hardware_version(answer, zigbee_id)

    def open(self):
        self.driver.open()
        return self

    def close(self):
        self.driver.close()
        return self

    def _run_sequence(self, sequence):
        answer = None
        for seq in sequence:
            if "tx" in seq.keys():
                self.driver.write(seq["tx"])
            if "rx" in seq.keys():
                data = self.driver.read(to_read=len(seq["rx"]))
                if data != seq["rx"]:
                    self.protocol.handle_error(expected=seq["rx"], received=data)
            if "delay" in seq.keys():
                delay = int(seq["delay"])
                self.logger.debug("sleeping for %d seconds...", delay)
                time.sleep(delay)
            if "answer" in seq.keys():
                answer = self.driver.read(stop_on=self.protocol.get_end_of_frame_sep())
                self.protocol.check_answer(answer=answer)
        return answer

    def _get_answer(self, sequence):
        answer = self._run_sequence(sequence)
        if answer is not None:
            return answer
        else:
            raise PyZigBeeFailed("Device did not reply")

    def scan(self, delay=5):
        """
        Scan the network and return a list of dict (database Index, ZigBee ID)
        """
        self.driver.set_unblocking_mode()

        self.logger.debug("getting number of devices...")
        sequence = self.protocol.encode_get_dev_number(delay=delay)
        answer = self._get_answer(sequence)
        dev_nb = self.protocol.decode_dev_number(answer)
        self.logger.debug("%d device(s) on the network", dev_nb)

        # we can now loop over the devices
        devices = []
        for i in range(0, dev_nb):
            try:
                self.logger.debug("getting device ID at index %d...", i)
                sequence = self.protocol.encode_get_dev_id(dev_index=i)
                answer = self._get_answer(sequence)
                dev_id = self.protocol.decode_dev_id(answer)
                self.logger.info("device ID at index %d: %s", i, dev_id)
                devices.append({"index": i, "zigbee_id": dev_id})
            except PyZigBeeException as error:
                self.logger.warn("failed to get device ID at index %d (%s)",
                                 i, error)
        return devices

    def receive(self, timeout=None):
        """
        Receive frame from the network

        Optional arg: read timeout in seconds for non blocking mode
        """
        if timeout is None or timeout == "":
            self.driver.set_blocking_mode()
        else:
            self.driver.set_unblocking_mode(timeout=timeout)
        return self.driver.read(stop_on=self.protocol.get_end_of_frame_sep())

    def _decode_binding(self, zigbee_id):
        """
        Decode binding request from device
        """
        answer = self.driver.read(stop_on=self.protocol.get_end_of_frame_sep())
        dev_id = self.protocol.decode_binding_id(answer)

        if dev_id != zigbee_id:
            raise PyZigBeeBadArgument("Received un/binding request from ID: %s"
                                      " (expected was: %s)" % (dev_id, zigbee_id))
        return dev_id

    def bind(self, zigbee_id):
        """
        Bind procedure

        arg: the zigbee device to bind with
        """
        self.driver.set_blocking_mode()
        dev_id = self._decode_binding(zigbee_id)
        sequence = self.protocol.encode_binding_request(dev_id)
        self._run_sequence(sequence)

    def unbind(self, zigbee_id):
        """
        Unbind procedure

        arg: the zigbee device to unbind from
        """
        self.driver.set_blocking_mode()
        dev_id = self._decode_binding(zigbee_id)
        sequence = self.protocol.encode_unbinding_request(dev_id)
        self._run_sequence(sequence)

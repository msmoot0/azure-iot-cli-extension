# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

from azext_iot.central.models.enum import DeviceStatus


class Device:
    def __init__(self, device: dict):
        self.approved = device.get("enabled") or device.get("approved")
        self.display_name = device.get("displayName")
        self.etag = device.get("etag")
        self.id = device.get("id")
        self.instance_of = device.get("template") or device.get("instanceOf")
        self.provisioned = device.get("provisioned")
        self.simulated = device.get("simulated")
        self._device_status = self._parse_device_status()

    def _parse_device_status(self) -> DeviceStatus:
        if not self.approved:
            return DeviceStatus.blocked

        if not self.instance_of:
            return DeviceStatus.unassociated

        if not self.provisioned:
            return DeviceStatus.registered

        return DeviceStatus.provisioned

    def get_registration_info(self) -> dict:
        registration_info = {
            "device_status": self._device_status.value,
            "display_name": self.display_name,
            "id": self.id,
            "simulated": self.simulated,
            "instance_of": self.instance_of,
        }

        return registration_info

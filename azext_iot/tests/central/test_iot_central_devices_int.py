# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------


from sys import api_version
import time
import pytest
import json
from azext_iot.central.models.enum import DeviceStatus, ApiVersion
from azext_iot.tests import helpers
from azext_iot.tests.central import (
    CentralLiveScenarioTest,
)
from knack.log import get_logger


logger = get_logger(__name__)


class TestIotCentralDevices(CentralLiveScenarioTest):
    @pytest.fixture(autouse=True)
    def fixture_api_version(self, request):
        self._api_version = request.config.getoption("--api-version")
        IS_1_1_PREVIEW = (
            self._api_version == ApiVersion.v1_1_preview.value
            or self._api_version is None
        )  # either explicitely selected or omitted
        if IS_1_1_PREVIEW:
            logger.info("Testing 1.1-preview")
        yield

    def __init__(self, test_scenario):
        super(TestIotCentralDevices, self).__init__(test_scenario=test_scenario)

    def test_central_device_twin_show_fail(self):
        (device_id, _) = self._create_device(api_version=self._api_version)

        # Verify incorrect app-id throws error
        command = (
            "iot central device twin show --app-id incorrect-app --device-id {}".format(
                device_id
            )
        )

        self.cmd(command, expect_failure=True)

        # Verify incorrect device-id throws error
        command = "iot central device twin show --app-id {} --device-id incorrect-device".format(
            self.app_id
        )

        self.cmd(command, expect_failure=True)

        self._delete_device(device_id=device_id, api_version=self._api_version)

    def test_central_device_c2d_purge_success(self):
        (template_id, _) = self._create_device_template(api_version=self._api_version)
        (device_id, _) = self._create_device(
            template=template_id, api_version=self._api_version, simulated=True
        )

        # wait about a few seconds for simulator to kick in so that provisioning completes
        time.sleep(60)

        command = (
            "iot central device c2d-message purge --app-id {} --device-id {}".format(
                self.app_id, device_id
            )
        )

        cmd_output = self.cmd(command).get_output_in_json()

        self._delete_device(device_id=device_id, api_version=self._api_version)
        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

        assert device_id in cmd_output["message"]
        assert "Total messages purged:" in cmd_output["message"]

    def test_central_device_twin_show_success(self):
        (template_id, _) = self._create_device_template(api_version=self._api_version)
        (device_id, _) = self._create_device(
            template=template_id, api_version=self._api_version, simulated=True
        )

        # wait about a few seconds for simulator to kick in so that provisioning completes
        time.sleep(60)

        command = "iot central device twin show --app-id {} --device-id {}".format(
            self.app_id, device_id
        )

        self.cmd(
            command,
            checks=[
                self.check("deviceId", device_id),
                self.check("tags", {}),
                self.check("_links", None),
            ],
        )

        self._delete_device(device_id=device_id, api_version=self._api_version)
        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

    def test_device_connect(self):
        if self.app_primary_key is None:
            pytest.skip(
                "Cannot test without primary key. Currently there is no way of retrieving the app "
                "primary key from the IoT Central App."
            )
        app_scope_id = self.get_app_scope_id(api_version=self._api_version)
        device_id = "testDevice"

        command = "iot central device compute-device-key --pk {} -d {}".format(
            self.app_primary_key, device_id
        )
        device_primary_key = self.cmd(
            command, include_opt_args=False
        ).get_output_in_json()

        credentials = {
            "idScope": app_scope_id,
            "symmetricKey": {"primaryKey": device_primary_key},
        }
        device_client = helpers.dps_connect_device(device_id, credentials)

        command = "iot central device show --app-id {} -d {}".format(
            self.app_id, device_id
        )

        self.cmd(
            command,
            api_version=self._api_version,
            checks=[self.check("id", device_id)],
        )

        self._delete_device(device_id=device_id, api_version=self._api_version)

        assert device_client.connected

    def test_central_device_methods_CRUD(self):
        # list devices and get count
        start_device_list = self.cmd(
            "iot central device list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

        start_dev_count = len(start_device_list)
        (device_id, device_name) = self._create_device(api_version=self._api_version)

        command = "iot central device show --app-id {} -d {}".format(
            self.app_id, device_id
        )
        checks = [
            self.check("displayName", device_name),
            self.check("id", device_id),
            self.check("simulated", False),
        ]
        if self._api_version == ApiVersion.preview.value:
            checks.append(self.check("approved", True))
        else:
            checks.append(self.check("enabled", True))

        self.cmd(command, api_version=self._api_version, checks=checks)

        created_device_list = self.cmd(
            "iot central device list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

        created_dev_count = len(created_device_list)
        assert created_dev_count == (start_dev_count + 1)
        # assert device with id "device_id" is in created list
        assert (
            next(
                (device for device in created_device_list if device["id"] == device_id),
                None,
            )
            is not None
        )

        # UPDATES

        new_device_name = f"{device_name}_new"
        command = "iot central device update --app-id {} -d {} --device-name {}".format(
            self.app_id,
            device_id,
            new_device_name,
        )
        checks = [
            self.check("displayName", new_device_name),
            self.check("id", device_id),
        ]
        self.cmd(command, api_version=self._api_version, checks=checks)

        # DELETE
        self._delete_device(device_id=device_id, api_version=self._api_version)

        deleted_device_list = self.cmd(
            "iot central device list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

        deleted_dev_count = len(deleted_device_list)
        assert deleted_dev_count == start_dev_count
        # assert device with id "device_id" has been removed from list
        assert (
            next(
                (device for device in deleted_device_list if device["id"] == device_id),
                None,
            )
            is None
        )

    def test_central_edge_device_methods(self):
        # force API Version 1.1-preview as we want deployment manifest to be included

        # create edge template
        (template_id, _) = self._create_device_template(
            api_version=ApiVersion.v1_1_preview.value, edge=True
        )

        (device_id, _) = self._create_device(
            template=template_id,
            api_version=ApiVersion.v1_1_preview.value,
            simulated=True,
        )

        # wait about a few seconds for simulator to kick in so that provisioning completes
        time.sleep(60)

        command = "iot central device list --app-id {}".format(self.app_id)
        total_devs_list = self.cmd(command).get_output_in_json()

        # check if device appears as edge
        command = "iot central device list --app-id {} --edge-only".format(self.app_id)
        edge_list = self.cmd(command).get_output_in_json()
        assert device_id in [dev["id"] for dev in edge_list]
        # check edge device appears in general list
        assert all(x in total_devs_list for x in edge_list)

        # MODULES
        command = "iot central device edge module list --app-id {} -d {}".format(
            self.app_id, device_id
        )
        modules = self.cmd(command).get_output_in_json()

        assert len(modules) == 4  # edge runtime + custom modules
        assert all(
            (
                cond is True
                for cond in [
                    a in [module["moduleId"] for module in modules]
                    for a in [
                        "$edgeHub",
                        "$edgeAgent",
                        "testModule",
                        "SimulatedTemperatureSensor",
                    ]
                ]
            )
        )
        self._delete_device(device_id=device_id, api_version=self._api_version)
        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

    def test_central_edge_children_methods(self):
        # force API Version 1.1-preview as we want deployment manifest to be included

        # create child template
        (child_template_id, _) = self._create_device_template(
            api_version=ApiVersion.v1_1_preview.value
        )

        # create edge template
        (template_id, _) = self._create_device_template(
            api_version=ApiVersion.v1_1_preview.value, edge=True
        )

        (device_id, _) = self._create_device(
            template=template_id,
            api_version=ApiVersion.v1_1_preview.value,
            simulated=True,
        )

        (child_id, _) = self._create_device(
            template=child_template_id,
            api_version=ApiVersion.v1_1_preview.value,
            simulated=True,
        )

        # wait about a few seconds for simulator to kick in so that provisioning completes
        time.sleep(60)

        if api_version == ApiVersion.v1_1_preview.value:
            # check if device appears as edge
            command = "iot central device list --app-id {} --edge-only"
            devs_list = self.cmd(command).get_output_in_json()
            assert device_id in [dev.id for dev in devs_list]
        else:
            # check twin to evaluate the iotedge flag
            command = "iot central device twin show --app-id {} -d {}".format(
                self.app_id, device_id
            )
            twin = self.cmd(command).get_output_in_json()

            assert twin["capabilities"]["iotEdge"] is True

        # CHILDREN
        command = "iot central device edge children add --app-id {} -d {} --children-ids {}".format(
            self.app_id, device_id, child_id
        )
        self.cmd(command, api_version=ApiVersion.v1_1_preview.value)
        # wait for relationship to be established
        time.sleep(10)

        command = "iot central device edge children list --app-id {} -d {}".format(
            self.app_id, device_id
        )

        children = self.cmd(
            command, api_version=ApiVersion.v1_1_preview.value
        ).get_output_in_json()
        assert len(children) == 1
        assert children[0]["id"] == child_id

        # cleanup
        self._delete_device(device_id=child_id, api_version=self._api_version)
        # give some time to backend as device must still be on db
        time.sleep(10)
        self._delete_device(device_id=device_id, api_version=self._api_version)
        self._delete_device_template(
            template_id=child_template_id, api_version=self._api_version
        )
        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

    def test_central_device_template_methods_CRUD(self):
        # currently: create, show, list, delete

        # list device templates and get count
        start_device_template_list = self.cmd(
            "iot central device-template list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

        start_dev_temp_count = len(start_device_template_list)

        (template_id, template_name) = self._create_device_template(
            api_version=self._api_version
        )

        command = "iot central device-template show --app-id {} --device-template-id {}".format(
            self.app_id, template_id
        )

        result = self.cmd(
            command,
            api_version=self._api_version,
            checks=[self.check("displayName", template_name)],
        )

        json_result = result.get_output_in_json()

        assert (
            self._get_template_id(api_version=self._api_version, template=json_result)
            == template_id
        )

        created_device_template_list = self.cmd(
            "iot central device-template list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

        created_dev_temp_count = len(created_device_template_list)
        # assert number of device templates changed by 1 or none in case template was already present in the application
        assert (created_dev_temp_count == (start_dev_temp_count + 1)) or (
            created_dev_temp_count == start_dev_temp_count
        )
        # assert template with id "template_id" is in created list
        assert (
            next(
                (
                    template
                    for template in created_device_template_list
                    if self._get_template_id(
                        template=template, api_version=self._api_version
                    )
                    == template_id
                ),
                None,
            )
            is not None
        )

        # UPDATE
        new_template_name = f"{template_name}_new"
        del json_result[
            self._get_template_id_key(api_version=self._api_version)
        ]  # remove id
        del json_result["@context"]
        del json_result["etag"]

        json_result["displayName"] = new_template_name
        json_result["capabilityModel"]["contents"].append(
            {
                "@id": "dtmi:newcap;1",
                "@type": "Telemetry",
                "displayName": "testNewCapability",
                "name": "testNewCapability",
                "schema": "double",
            }
        )
        updated_contents = json_result["capabilityModel"]["contents"]
        command = (
            "iot central device-template update --app-id {} --dtid {} -k '{}'".format(
                self.app_id,
                template_id,
                json.dumps(json_result)
                .replace("{", "{{")
                .replace(
                    "}", "}}"
                ),  # replace is mandatory here as processing involve string formatting
            )
        )

        checks = [self.check("displayName", new_template_name)]
        updated = self.cmd(
            command, api_version=self._api_version, checks=checks
        ).get_output_in_json()
        assert updated["capabilityModel"]["contents"] == updated_contents

        # DELETE
        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

        deleted_device_template_list = self.cmd(
            "iot central device-template list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

        deleted_dev_temp_count = len(deleted_device_template_list)

        # if template existed before this run then a successfull deletion reduces the number of templates
        assert (
            deleted_dev_temp_count == start_dev_temp_count
            or deleted_dev_temp_count == (start_dev_temp_count - 1)
        )

        if (
            next(
                (
                    template
                    for template in start_device_template_list
                    if self._get_template_id(
                        template=template, api_version=self._api_version
                    )
                    == template_id
                ),
                None,
            )
            is None
        ):
            # template has been created during test so deletion succeeds
            # otherwise it might fail because existing devices can exist
            assert (
                next(
                    (
                        template
                        for template in deleted_device_template_list
                        if self._get_template_id(
                            template=template, api_version=self._api_version
                        )
                        == template_id
                    ),
                    None,
                )
                is None
            )

    def test_central_device_groups_list(self):
        result = self._list_device_groups()
        # assert object is empty or populated but not null
        assert result is not None and (result == [] or bool(result) is True)

    def test_central_device_registration_info_registered(self):
        (template_id, _) = self._create_device_template(api_version=self._api_version)
        (device_id, device_name) = self._create_device(
            template=template_id, api_version=self._api_version, simulated=False
        )

        command = "iot central device registration-info --app-id {} -d {}".format(
            self.app_id, device_id
        )

        result = self.cmd(command, api_version=self._api_version)

        self._delete_device(device_id=device_id, api_version=self._api_version)

        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

        json_result = result.get_output_in_json()

        assert json_result["@device_id"] == device_id

        # since time taken for provisioning to complete is not known
        # we can only assert that the payload is populated, not anything specific beyond that
        assert json_result["device_registration_info"] is not None
        assert json_result["dps_state"] is not None

        # Validation - device registration.
        device_registration_info = json_result["device_registration_info"]
        assert len(device_registration_info) == 5
        assert device_registration_info.get("device_status") == "registered"
        assert device_registration_info.get("id") == device_id
        assert device_registration_info.get("display_name") == device_name
        assert (
            device_registration_info.get(
                "instance_of"
                if self._api_version == ApiVersion.preview.value
                else "template"
            )
            == template_id
        )
        assert not device_registration_info.get("simulated")

        # Validation - dps state
        dps_state = json_result["dps_state"]
        assert len(dps_state) == 2
        assert device_registration_info.get("status") is None
        assert dps_state.get("error") == "Device is not yet provisioned."

    def test_central_device_registration_info_unassociated(self):
        (device_id, device_name) = self._create_device(api_version=self._api_version)

        command = "iot central device registration-info --app-id {} -d {}".format(
            self.app_id, device_id
        )

        result = self.cmd(command, api_version=self._api_version)

        self._delete_device(device_id=device_id, api_version=self._api_version)

        json_result = result.get_output_in_json()

        assert json_result["@device_id"] == device_id

        # since time taken for provisioning to complete is not known
        # we can only assert that the payload is populated, not anything specific beyond that
        assert json_result["device_registration_info"] is not None
        assert json_result["dps_state"] is not None

        # Validation - device registration.
        device_registration_info = json_result["device_registration_info"]
        assert len(device_registration_info) == 5
        assert device_registration_info.get("device_status") == "unassociated"
        assert device_registration_info.get("id") == device_id
        assert device_registration_info.get("display_name") == device_name
        assert (
            device_registration_info.get(
                "instance_of"
                if self._api_version == ApiVersion.preview.value
                else "template"
            )
            is None
        )
        assert not device_registration_info.get("simulated")

        # Validation - dps state
        dps_state = json_result["dps_state"]
        assert len(dps_state) == 2
        assert device_registration_info.get("status") is None
        assert (
            dps_state.get("error")
            == "Device does not have a valid template associated with it."
        )

    def test_central_device_registration_summary(self):
        command = "iot central diagnostics registration-summary --app-id {}".format(
            self.app_id
        )

        result = self.cmd(command, api_version=self._api_version)

        json_result = result.get_output_in_json()
        assert json_result[DeviceStatus.provisioned.value] is not None
        assert json_result[DeviceStatus.registered.value] is not None
        assert json_result[DeviceStatus.unassociated.value] is not None
        assert json_result[DeviceStatus.blocked.value] is not None
        assert len(json_result) == 4

    def test_central_device_should_start_failover_and_failback(self):
        # created device template & device
        (template_id, _) = self._create_device_template(api_version=self._api_version)
        (device_id, _) = self._create_device(
            instance_of=template_id, api_version=self._api_version, simulated=False
        )

        command = (
            "iot central device show-credentials --device-id {} --app-id {}".format(
                device_id, self.app_id
            )
        )

        credentials = self.cmd(
            command, api_version=self._api_version
        ).get_output_in_json()

        # connect & disconnect device & wait to be provisioned
        self._connect_gettwin_disconnect_wait_tobeprovisioned(device_id, credentials)
        command = "iot central device manual-failover --app-id {} --device-id {} --ttl {}".format(
            self.app_id, device_id, 5
        )

        # initiating failover
        result = self.cmd(command, api_version=self._api_version)
        json_result = result.get_output_in_json()

        # check if failover started and getting original hub identifier
        hubIdentifierOriginal = json_result["hubIdentifier"]

        # connect & disconnect device & wait to be provisioned
        self._connect_gettwin_disconnect_wait_tobeprovisioned(device_id, credentials)

        command = (
            "iot central device manual-failback --app-id {} --device-id {}".format(
                self.app_id, device_id
            )
        )

        # Initiating failback
        fb_result = self.cmd(command, api_version=self._api_version)

        # checking if failover has been done by comparing original hub identifier with hub identifier after failover is done
        fb_json_result = fb_result.get_output_in_json()
        hubIdentifierFailOver = fb_json_result["hubIdentifier"]
        # connect & disconnect device & wait to be provisioned
        self._connect_gettwin_disconnect_wait_tobeprovisioned(device_id, credentials)

        # initiating failover again to see if hub identifier after failbackreturned to original state
        command = "iot central device manual-failover --app-id {} --device-id {} --ttl {}".format(
            self.app_id, device_id, 5
        )

        result = self.cmd(command, api_version=self._api_version)

        json_result = result.get_output_in_json()
        hubIdentifierFinal = json_result["hubIdentifier"]

        # Cleanup
        self._delete_device(device_id=device_id, api_version=self._api_version)

        self._delete_device_template(
            template_id=template_id, api_version=self._api_version
        )

        assert len(hubIdentifierOriginal) > 0
        assert len(hubIdentifierFailOver) > 0
        assert hubIdentifierOriginal != hubIdentifierFailOver
        assert len(hubIdentifierFinal) > 0
        assert hubIdentifierOriginal == hubIdentifierFinal

    def _list_device_groups(self):
        return self.cmd(
            "iot central device-group list --app-id {}".format(self.app_id),
            api_version=self._api_version,
        ).get_output_in_json()

    def _connect_gettwin_disconnect_wait_tobeprovisioned(self, device_id, credentials):
        device_client = helpers.dps_connect_device(device_id, credentials)
        device_client.get_twin()
        device_client.disconnect()
        device_client.shutdown()
        self._wait_for_provisioned(device_id=device_id, api_version=self._api_version)

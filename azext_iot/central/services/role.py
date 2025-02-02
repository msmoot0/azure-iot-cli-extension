# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------
# This is largely derived from https://docs.microsoft.com/en-us/rest/api/iotcentral/roles

from typing import List, Union
import requests

from knack.log import get_logger

from azure.cli.core.azclierror import AzureResponseError
from azext_iot.constants import CENTRAL_ENDPOINT
from azext_iot.central.services import _utility
from azext_iot.central.models.v1 import RoleV1
from azext_iot.central.models.v1_1_preview import RoleV1_1_preview
from azext_iot.central.models.preview import RolePreview
from azure.cli.core.util import should_disable_connection_verify


logger = get_logger(__name__)

BASE_PATH = "api/roles"


def get_role(
    cmd,
    app_id: str,
    role_id: str,
    token: str,
    api_version: str,
    central_dns_suffix=CENTRAL_ENDPOINT,
) -> Union[RoleV1, RoleV1_1_preview, RolePreview]:
    """
    Get role info given a role id

    Args:
        cmd: command passed into az
        role_id: unique case-sensitive role id,
        app_id: name of app (used for forming request URL)
        token: (OPTIONAL) authorization token to fetch role details from IoTC.
            MUST INCLUDE type (e.g. 'SharedAccessToken ...', 'Bearer ...')
        central_dns_suffix: {centralDnsSuffixInPath} as found in docs

    Returns:
        role: dict
    """

    url = "https://{}.{}/{}/{}".format(app_id, central_dns_suffix, BASE_PATH, role_id)
    headers = _utility.get_headers(token, cmd)

    # Construct parameters
    query_parameters = {}
    query_parameters["api-version"] = api_version

    response = requests.get(
        url,
        headers=headers,
        params=query_parameters,
        verify=not should_disable_connection_verify(),
    )
    result = _utility.try_extract_result(response)

    return _utility.get_object(result, "Role", api_version)


def list_roles(
    cmd,
    app_id: str,
    token: str,
    api_version: str,
    max_pages=0,
    central_dns_suffix=CENTRAL_ENDPOINT,
) -> List[Union[RoleV1, RoleV1_1_preview, RolePreview]]:
    """
    Get a list of all roles in IoTC app

    Args:
        cmd: command passed into az
        app_id: name of app (used for forming request URL)
        token: (OPTIONAL) authorization token to fetch role details from IoTC.
            MUST INCLUDE type (e.g. 'SharedAccessToken ...', 'Bearer ...')
        central_dns_suffix: {centralDnsSuffixInPath} as found in docs

    Returns:
        list of roles
    """

    roles = []

    url = "https://{}.{}/{}".format(app_id, central_dns_suffix, BASE_PATH)
    headers = _utility.get_headers(token, cmd)

    # Construct parameters
    query_parameters = {}
    query_parameters["api-version"] = api_version

    pages_processed = 0
    while (max_pages == 0 or pages_processed < max_pages) and url:
        response = requests.get(
            url,
            headers=headers,
            params=query_parameters,
            verify=not should_disable_connection_verify(),
        )
        result = _utility.try_extract_result(response)

        if "value" not in result:
            raise AzureResponseError("Value is not present in body: {}".format(result))

        roles.extend(
            [_utility.get_object(role, "Role", api_version) for role in result["value"]]
        )

        url = result.get("nextLink", None)
        pages_processed = pages_processed + 1

    return roles

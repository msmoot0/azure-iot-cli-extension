# coding=utf-8
# --------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
#
# Code generated by Microsoft (R) AutoRest Code Generator.
# Changes may cause incorrect behavior and will be lost if the code is
# regenerated.
# --------------------------------------------------------------------------

from .digital_twins_resource import DigitalTwinsResource


class DigitalTwinsDescription(DigitalTwinsResource):
    """The description of the DigitalTwins service.

    Variables are only populated by the server, and will be ignored when
    sending a request.

    All required parameters must be populated in order to send to Azure.

    :ivar id: The resource identifier.
    :vartype id: str
    :ivar name: The resource name.
    :vartype name: str
    :ivar type: The resource type.
    :vartype type: str
    :param location: Required. The resource location.
    :type location: str
    :param tags: The resource tags.
    :type tags: dict[str, str]
    :param identity: The managed identity for the DigitalTwinsInstance.
    :type identity: ~controlplane.models.DigitalTwinsIdentity
    :ivar system_data: Metadata pertaining to creation and last modification
     of the DigitalTwinsInstance.
    :vartype system_data: ~controlplane.models.SystemData
    :ivar created_time: Time when DigitalTwinsInstance was created.
    :vartype created_time: datetime
    :ivar last_updated_time: Time when DigitalTwinsInstance was updated.
    :vartype last_updated_time: datetime
    :ivar provisioning_state: The provisioning state. Possible values include:
     'Provisioning', 'Deleting', 'Updating', 'Succeeded', 'Failed', 'Canceled',
     'Deleted', 'Warning', 'Suspending', 'Restoring', 'Moving'
    :vartype provisioning_state: str or
     ~controlplane.models.ProvisioningState
    :ivar host_name: Api endpoint to work with DigitalTwinsInstance.
    :vartype host_name: str
    :param private_endpoint_connections: The private endpoint connections.
    :type private_endpoint_connections:
     list[~controlplane.models.PrivateEndpointConnection]
    :param public_network_access: Public network access for the
     DigitalTwinsInstance. Possible values include: 'Enabled', 'Disabled'
    :type public_network_access: str or
     ~controlplane.models.PublicNetworkAccess
    """

    _validation = {
        'id': {'readonly': True},
        'name': {'readonly': True, 'pattern': r'^(?!-)[A-Za-z0-9-]{3,63}(?<!-)$'},
        'type': {'readonly': True},
        'location': {'required': True},
        'system_data': {'readonly': True},
        'created_time': {'readonly': True},
        'last_updated_time': {'readonly': True},
        'provisioning_state': {'readonly': True},
        'host_name': {'readonly': True},
    }

    _attribute_map = {
        'id': {'key': 'id', 'type': 'str'},
        'name': {'key': 'name', 'type': 'str'},
        'type': {'key': 'type', 'type': 'str'},
        'location': {'key': 'location', 'type': 'str'},
        'tags': {'key': 'tags', 'type': '{str}'},
        'identity': {'key': 'identity', 'type': 'DigitalTwinsIdentity'},
        'system_data': {'key': 'systemData', 'type': 'SystemData'},
        'created_time': {'key': 'properties.createdTime', 'type': 'iso-8601'},
        'last_updated_time': {'key': 'properties.lastUpdatedTime', 'type': 'iso-8601'},
        'provisioning_state': {'key': 'properties.provisioningState', 'type': 'str'},
        'host_name': {'key': 'properties.hostName', 'type': 'str'},
        'private_endpoint_connections': {'key': 'properties.privateEndpointConnections', 'type': '[PrivateEndpointConnection]'},
        'public_network_access': {'key': 'properties.publicNetworkAccess', 'type': 'str'},
    }

    def __init__(self, **kwargs):
        super(DigitalTwinsDescription, self).__init__(**kwargs)
        self.created_time = None
        self.last_updated_time = None
        self.provisioning_state = None
        self.host_name = None
        self.private_endpoint_connections = kwargs.get('private_endpoint_connections', None)
        self.public_network_access = kwargs.get('public_network_access', None)

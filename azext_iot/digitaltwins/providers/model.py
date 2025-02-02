# coding=utf-8
# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import json
from knack.log import get_logger
from azure.cli.core.azclierror import ForbiddenError, RequiredArgumentMissingError
from azext_iot.common.utility import process_json_arg, handle_service_exception, scantree
from azext_iot.digitaltwins.providers.base import DigitalTwinsProvider
from azext_iot.sdk.digitaltwins.dataplane.models import ErrorResponseException

logger = get_logger(__name__)


def get_model_dependencies(model):
    """Return a list of dependency DTMIs for a given model"""
    dependencies = []

    # Add everything that would have dependency DTMIs, worry about flattening later
    if "contents" in model:
        components = [item["schema"] for item in model["contents"] if item["@type"] == "Component"]
        dependencies.extend(components)

    if "extends" in model:
        dependencies.append(model['extends'])

    # Go through gathered items, get the DTMI references, and flatten if needed
    no_dup = set()
    for item in dependencies:
        # Models defined in a DTDL can implement extensions of up to two interfaces.
        # These interfaces can be in the form of a DTMI reference, or a nested model.
        if isinstance(item, str):
            # If its just a string, thats a single DTMI reference, so just add that to our set
            no_dup.add(item)
        elif isinstance(item, dict):
            # If its a single nested model, get its dtmi reference, dependencies and add them
            no_dup.update(set(get_model_dependencies(item)))
        elif isinstance(item, list):
            # If its a list, could have DTMIs or nested models
            for sub_item in item:
                if isinstance(sub_item, str):
                    # If there are strings in the list, that's a DTMI reference, so add it
                    no_dup.add(sub_item)
                elif isinstance(sub_item, dict):
                    # This is a nested model. Now go get its dependencies and add them
                    no_dup.update(set(get_model_dependencies(sub_item)))

    return list(no_dup)


class ModelProvider(DigitalTwinsProvider):
    def __init__(self, cmd, name, rg=None):
        super(ModelProvider, self).__init__(
            cmd=cmd, name=name, rg=rg,
        )
        self.model_sdk = self.get_sdk().digital_twin_models

    def add(self, models=None, from_directory=None):
        if not any([models, from_directory]):
            raise RequiredArgumentMissingError("Provide either --models or --from-directory.")

        # If both arguments are provided. --models wins.
        payload = []
        if models:
            models_result = process_json_arg(content=models, argument_name="models")

            if isinstance(models_result, list):
                payload.extend(models_result)
            elif isinstance(models_result, dict):
                payload.append(models_result)

        elif from_directory:
            payload = self._process_directory(from_directory=from_directory)

        logger.info("Models payload %s", json.dumps(payload))

        # @vilit - hack to customize 403's to have more specific error messages
        try:
            return self.model_sdk.add(payload, raw=True).response.json()
        except ErrorResponseException as e:
            if e.response.status_code == 403:
                error_text = "Current principal access is forbidden. Please validate rbac role assignments."
                raise ForbiddenError(error_text)
            handle_service_exception(e)

    def _process_directory(self, from_directory):
        logger.debug(
            "Documents contained in directory: {}, processing...".format(from_directory)
        )
        payload = []
        for entry in scantree(from_directory):
            if all(
                [not entry.name.endswith(".json"), not entry.name.endswith(".dtdl")]
            ):
                logger.debug(
                    "Skipping {} - model file must end with .json or .dtdl".format(
                        entry.path
                    )
                )
                continue
            entry_json = process_json_arg(content=entry.path, argument_name=entry.name)
            payload.append(entry_json)

        return payload

    def get(self, id, get_definition=False):
        try:
            return self.model_sdk.get_by_id(
                id=id, include_model_definition=get_definition, raw=True
            ).response.json()
        except ErrorResponseException as e:
            handle_service_exception(e)

    def list(
        self, get_definition=False, dependencies_for=None, top=None
    ):  # top is guarded for int() in arg def
        from azext_iot.sdk.digitaltwins.dataplane.models import DigitalTwinModelsListOptions

        list_options = DigitalTwinModelsListOptions(max_items_per_page=top)

        return self.model_sdk.list(
            dependencies_for=dependencies_for,
            include_model_definition=get_definition,
            digital_twin_models_list_options=list_options,
        )

    def update(self, id, decommission: bool):
        patched_model = [
            {"op": "replace", "path": "/decommissioned", "value": decommission}
        ]

        # Does not return model object upon updating
        try:
            self.model_sdk.update(id=id, update_model=patched_model)
        except ErrorResponseException as e:
            handle_service_exception(e)

        return self.get(id=id)

    def delete(self, id: str):
        try:
            self.model_sdk.delete(id=id)
        except ErrorResponseException as e:
            handle_service_exception(e)

    def delete_all(self):
        # Get all models
        incoming_pager = self.list(get_definition=True)
        incoming_result = []
        try:
            while True:
                incoming_result.extend(incoming_pager.advance_page())
        except StopIteration:
            pass
        except ErrorResponseException as e:
            handle_service_exception(e)

        # Build dict of model_id : set of parent_ids
        parsed_models = {model.id: set() for model in incoming_result}
        for model in incoming_result:
            # Parse dependents, add current model as parent of dependents
            dependencies = get_model_dependencies(model.model)
            for d_id in dependencies:
                parsed_models[d_id].add(model.id)

        def delete_parents(model_id, model_dict):
            # Check if current model has been deleted already
            if model_id not in model_dict:
                return

            # Delete parents first
            for parent_id in model_dict[model_id]:
                if parent_id in model_dict:
                    delete_parents(parent_id, model_dict)

            # Delete current model and remove references
            del model_dict[model_id]
            try:
                self.delete(model_id)
            except Exception as e:
                logger.warning(f"Could not delete model {model_id}; error is {e}")

        while len(parsed_models) > 0:
            model_id = next(iter(parsed_models))
            delete_parents(model_id, parsed_models)

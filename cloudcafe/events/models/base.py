"""
Copyright 2015 Rackspace

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import json

from cafe.engine.models.base import (
    AutoMarshallingModel, AutoMarshallingListModel)


class EventBaseModel(AutoMarshallingModel):
    """Base class for Event models

    This class provides default implementations for common
    model functionality. Child classes will need to
    override the kwarg_map and possibly the obj_model_key
    attributes. Additionally, models with submodels will
    need to override the _dict_to_obj method.

    Example:

        {
            "foo": {
                "key1": "value1",
                "key2": "value2",
                "id": "id_value"
            }
        }

        obj_model_key = 'foo'
        kwarg_map = {'key1': 'key1', 'key2': 'key2', 'id_': 'id'}

        (This mapping will generate: self.key1, self.key2, self.id_)
    """
    obj_model_key = None  # (Optional) Name of model's JSON schema
    kwarg_map = {}  # Mapping of JSON keys to model attribute names

    def __init__(self, kwargs):
        super(EventBaseModel, self).__init__()

        # Set class attributes from input kwargs
        # Ignore "private" kwargs (e.g. _foo) and kwargs
        # matching existing attributes (allows overriding)
        for var in kwargs and self.kwarg_map.values():
            if (var != 'self' and not var.startswith('_') and
                    not hasattr(self, var)):
                setattr(self, var, kwargs.get(var))

    @classmethod
    def _map_values_to_kwargs(cls, deserialized_obj):
        """Map input dict to class attributes"""
        kwargs = {}
        for local_kw, deserialized_obj_kw in cls.kwarg_map.iteritems():
            kwargs[local_kw] = deserialized_obj.get(deserialized_obj_kw)

        return cls(**kwargs)

    @classmethod
    def _json_to_obj(cls, serialized_str):
        """Deserialize a JSON string"""
        json_dict = json.loads(serialized_str)
        model_dict = json_dict.get(cls.obj_model_key) or json_dict
        return cls._dict_to_obj(model_dict)

    @classmethod
    def _dict_to_obj(cls, json_dict):
        """Default dict_to_obj implementation

        Default implementation works for simple cases. Override
        for instances with sub-models.
        """
        return cls._map_values_to_kwargs(json_dict)

    def is_empty(self):
        """Check if all object values are False

        Example:
            obj_json = {
                "foo": []
                "bar": 0
            }

            obj.foo = []
            obj.bar = 0
            # obj.is_empty() returns True
        """
        for key in self.kwarg_map.keys():
            value = getattr(self, key)

            # Short-circuit return for empty primitive type
            if not value:
                return True

            # Recursively check sub-models
            return value.is_empty() if hasattr(value, 'is_empty') else False


class EventBaseListModel(AutoMarshallingListModel):
    """Base class for Event list models

    This class provides default implementations for common
    list model functionality. Child classes will need to
    override the list_model_key and ObjectModel attributes.

    Example:

        {
            "foo": [
                {
                    "key1": "value1",
                    "key2": "value2"
                }
            ]
        }

        list_model_key = 'foo'
        ObjectModel = Foo
    """
    list_model_key = None  # Name of model's JSON array
    ObjectModel = None  # Name of model class for list elements

    @classmethod
    def _json_to_obj(cls, serialized_str):
        """Deserialize a JSON string"""
        json_dict = json.loads(serialized_str)
        list_of_dicts = json_dict.get(cls.list_model_key)
        return cls._list_to_obj(list_of_dicts)

    @classmethod
    def _list_to_obj(cls, list_of_dicts):
        """Create list of objects from list of dicts"""
        obj_list = cls()
        for obj_dict in list_of_dicts:
            obj_list.append(cls.ObjectModel._dict_to_obj(obj_dict))
        return obj_list

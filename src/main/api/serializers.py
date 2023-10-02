import copy
import traceback

from django.conf import settings
from django.db import transaction
from django.utils.functional import cached_property

from modeltranslation.translator import translator
from rest_framework import serializers
from rest_framework.fields import empty
from rest_framework.utils import model_meta
from main.utils import get_user_traceability_id


class IrisSerializer(serializers.ModelSerializer):
    """
    This serializer adds Meta options for customizing concrete behaviours.
      - expand_translatable (default: all): for each translatable field, it adds an equal field for each translation
      value and sets the original (the selected language value) as read only. Given a field description and two
      languages (ES, CA), the serializer will generate the following serializer fields: description_es,
      description_ca and description (read only).
    """

    can_delete = serializers.BooleanField(source="can_be_deleted", required=False, read_only=True)

    def get_fields(self):
        fields = super().get_fields()
        self._expand_translated_fields(fields)
        return fields

    @cached_property
    def translation_options(self):
        return getattr(self.Meta, "translation_options", translator.get_options_for_model(self.Meta.model))

    @cached_property
    def languages(self):
        return dict(settings.LANGUAGES)

    def _expand_translated_fields(self, fields):
        for trans_field in self.get_expand_translatable_fields(fields):
            assert trans_field in self.translation_options.fields, f"""
            Field {trans_field} is not a registered translatable field for {self.Meta.model}.
            """
            assert trans_field in fields, f"""
            Field {trans_field} is not declared on {self.__class__} serializer class.
            """
            self._expand_translated_field(fields, trans_field)

    def get_expand_translatable_fields(self, fields):
        """
        :return: List of field names for being expanded according to its translations.
        """
        expand_translatable = getattr(self.Meta, "expand_translatable", serializers.ALL_FIELDS)
        if expand_translatable == serializers.ALL_FIELDS:
            return [field for field in self.translation_options.fields.keys() if field in fields]
        else:
            return expand_translatable

    def _expand_translated_field(self, fields, field_name):
        """
        Creates the translation fields and pops the original one.
        :param fields: Dictionary with serializer fields
        :param field_name: Name of the field beign expanded.
        """
        trans_fields = {field.language: field for field in self.translation_options.fields.get(field_name)}
        field = fields[field_name]
        for lang, name in settings.LANGUAGES:
            trans_field = trans_fields[lang]
            if trans_field.name not in fields:
                fields[trans_field.name] = self._copy_for_translation(field, trans_field)
        field.read_only = True

    def _copy_for_translation(self, field, trans_field):
        """
        Makes the copy of the Field instance for field for using them with trans_field.
        :param field:
        :param trans_field:
        :return: Copied field.
        """
        new_field = copy.deepcopy(field)
        new_field.label = self.get_translated_label(field.label, self.languages.get(trans_field.language))
        return new_field

    def get_translated_label(self, original_label, language_name):
        return f"{original_label} ({language_name})"

    def get_translation_fields(self, field_name):
        """
        :param field_name:
        :return: Returns the list of translated serializer fields expanded
        """
        return [field.name for field in self.translation_options.fields.get(field_name)]


class ManyToManyExtendedSerializer(serializers.ListSerializer):

    def __init__(self, instance=None, data=empty, **kwargs):
        self.model = kwargs.pop("model")
        self.related_field = kwargs.pop("related_field")
        self.to = kwargs.pop("to")
        self.child = kwargs.pop("many_to_many_serializer")()
        self.related_instance = kwargs.pop("related_instance", None)
        self.extra_query_fields = kwargs.pop("extra_query_fields", {})
        self.set_user_id = kwargs.pop("set_user_id", True)
        self.extra_values_params = kwargs.pop("extra_values_params", [])
        self.extra_data_params = kwargs.pop("extra_data_params", [])
        if kwargs.get("many", False):
            raise Exception("ManyToManyExtendedBaseSerializer only allows many=False")
        kwargs["allow_empty"] = True
        super().__init__(instance, data, **kwargs)

    def to_representation(self, data):
        filter_fields = {"enabled": True}
        filter_fields.update(self.extra_query_fields)
        return super().to_representation(data.filter(**filter_fields))

    def save(self, **kwargs):
        validated_data = [dict(list(attrs.items()) + list(kwargs.items())) for attrs in self.validated_data]

        with transaction.atomic():
            related_instance = self.related_instance if self.related_instance else self.parent.instance
            filter_fields = {self.related_field: related_instance, "enabled": True}
            filter_fields.update(self.extra_query_fields)

            values_params = [self.to, "id"] + self.extra_values_params + self.extra_data_params
            active_registers = self.model.objects.filter(**filter_fields).values(*values_params)

            self.disable_registers(active_registers, validated_data)
            self.create_new_enabled_registers(active_registers, validated_data, related_instance)

        return self.instance

    def disable_registers(self, active_registers, validated_data):
        """
        Disable registers that are not send to the api
        :param active_registers: Current active to_registers
        :param validated_data: Validated data send to the api
        :return:
        """
        disable_ids = []
        for active_register in active_registers:
            found = False
            for data in validated_data:
                if active_register[self.to] == data[self.to].pk and not self.change_extra_values(active_register, data):
                    found = True
                    break
            if not found:
                disable_ids.append(active_register["id"])

        if disable_ids:
            self.model.objects.filter(id__in=disable_ids).update(enabled=False)

    def change_extra_values(self, active_register, data):
        """
        Check if extra values of register has changed
        :param active_register: Current register on the db
        :param data: New data from register
        :return: False if extra values params is not set or extra values have not change
        :return: True if extra values have changed
        """
        if not self.extra_values_params:
            return False
        for param in self.extra_values_params:
            if param is self.extra_data_params:
                continue
            if active_register[param] != data[param]:
                return True
        return False

    def create_new_enabled_registers(self, active_registers, validated_data, related_instance):
        """
        Create new enabled registers that are not previously on database
        :param active_registers: Current active to_registers
        :param validated_data: Validated data send to the api
        :param related_instance: Related instance of the register updated
        :return:
        """
        for data in validated_data:
            found = False
            for active_register in active_registers:
                if data[self.to].pk == active_register[self.to] and not self.change_extra_values(active_register, data):
                    found = True
                    break

            if not found:
                query_fields = {
                    self.to: data[self.to],
                    # the existence of the record is checked on the is_valid method
                    self.related_field: related_instance,
                }
                if self.set_user_id and self.context.get("request"):
                    query_fields.update({"user_id": get_user_traceability_id(self.context["request"].user)})

                query_fields.update(data)
                query_fields.update(self.extra_query_fields)
                self.model.objects.create(**query_fields)


class SerializerCreateExtraMixin:
    """
    Class to set the usre id to a model from the user that has done the request

    IMPORTANT: user_id must be set on fields and read_only_fiels of the serializer
    """

    extra_actions = False
    post_create_extra_actions = False
    save_user_id = True
    post_data_keys = []

    def do_extra_actions_on_create(self, validated_data):
        """
        Perform extra actions on create
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        raise NotImplementedError("Method must be implement with the extra actions that has to be done on the "
                                  "create of the serializer")

    def do_post_create_extra_actions(self, instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param instance: Instance of the created object
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        raise NotImplementedError("Method must be implement with the post create extra actions that has to be done "
                                  "on the create of the serializer")

    def create(self, validated_data):
        """
        We have a bit of extra checking around this in order to provide
        descriptive messages when something goes wrong, but this method is
        essentially just:

            return ExampleModel.objects.create(**validated_data)

        If there are many to many fields present on the instance then they
        cannot be set until the model is instantiated, in which case the
        implementation is like so:

            example_relationship = validated_data.pop("example_relationship")
            instance = ExampleModel.objects.create(**validated_data)
            instance.example_relationship = example_relationship
            return instance

        The default implementation also does not handle nested relationships.
        If you want to support writable nested relationships you'll need
        to write an explicit `.create()` method.
        """
        ModelClass = self.Meta.model

        # Remove many-to-many relationships from validated_data.
        # They are not valid arguments to the default `.create()` method,
        # as they require that the instance has already been saved.
        info = model_meta.get_field_info(ModelClass)
        many_to_many = {}
        for field_name, relation_info in info.relations.items():
            if relation_info.to_many and (field_name in validated_data):
                many_to_many[field_name] = validated_data.pop(field_name)

        with transaction.atomic():
            if self.extra_actions:
                self.do_extra_actions_on_create(validated_data)

            if self.save_user_id:
                self.register_user_id(validated_data)

            for post_data_key in self.post_data_keys:
                validated_data.pop(post_data_key, None)

            try:
                instance = ModelClass._default_manager.create(**validated_data)
            except TypeError:
                tb = traceback.format_exc()
                msg = (
                        "Got a `TypeError` when calling `%s.%s.create()`. "
                        "This may be because you have a writable field on the "
                        "serializer class that is not a valid argument to "
                        "`%s.%s.create()`. You may need to make the field "
                        "read-only, or override the %s.create() method to handle "
                        "this correctly.\nOriginal exception was:\n %s" %
                        (ModelClass.__name__, ModelClass._default_manager.name, ModelClass.__name__,
                         ModelClass._default_manager.name, self.__class__.__name__, tb)
                )
                raise TypeError(msg)

            if self.post_create_extra_actions:
                self.do_post_create_extra_actions(instance, validated_data)

            return instance

    def register_user_id(self, validated_data):
        # On the context of the serializer, we can find view that use the serializer
        # We can acces to the request from the view to get the username
        view = self.context.get("view")
        if view:
            validated_data["user_id"] = get_user_traceability_id(view.request.user)


class SerializerUpdateExtraMixin:
    post_update_extra_actions = False

    def do_extra_actions_on_update(self, validated_data):
        """
        Perform extra actions on update

        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        raise NotImplementedError("Method must be implement with the extra actions that has to be done on the "
                                  "update of the serializer")

    def do_post_update_extra_actions(self, previous_instance, validated_data):
        """
        Perform extra actions on create after the instance creation
        :param previous_instance: Copy of the instance before the update operation
        :param validated_data: Dict with validated data of the serializer
        :return:
        """
        raise NotImplementedError("Method must be implement with the post update extra actions that has to be done "
                                  "on the update of the serializer")

    def update(self, instance, validated_data):

        previous_instance = copy.deepcopy(instance)
        with transaction.atomic():
            self.do_extra_actions_on_update(validated_data)

            info = model_meta.get_field_info(instance)

            # Simply set each attribute on the instance, and then save it.
            # Note that unlike `.create()` we don't need to treat many-to-many
            # relationships as being a special case. During updates we already
            # have an instance pk for the relationships to be associated with.
            for attr, value in validated_data.items():
                if attr in info.relations and info.relations[attr].to_many:
                    field = getattr(instance, attr)
                    field.set(value)
                else:
                    setattr(instance, attr, value)
            instance.save()

            if self.post_update_extra_actions:
                self.do_post_update_extra_actions(previous_instance, validated_data)

            return instance


class GetGroupFromRequestMixin:

    @staticmethod
    def get_group_from_request(request):
        """
        Get group profile from request
        :param request:
        :return:
        """
        return request.user.usergroup.group if hasattr(request.user, "usergroup") else None


class UpperKeysMixin:

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        return self.upper_keys(representation)

    @staticmethod
    def upper_keys(representation):
        return {key.upper(): data for key, data in representation.items()}

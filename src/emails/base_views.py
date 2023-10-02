from abc import abstractmethod

from django.utils.functional import cached_property
from django_yubin.messages import TemplatedMultipleAttachmentsEmailMessageView

from iris_masters.models import Parameter
from iris_templates.renderer import Iris1TemplateRenderer
from iris_templates.template_params import get_required_param_names, get_template_param
from iris_templates.templates_context.context import IrisVariableFinder
import logging

logger = logging.getLogger(__name__)


class BaseRecordCardEmail(TemplatedMultipleAttachmentsEmailMessageView):
    FROM_EMAIL_PARAM = "MAILFROM"
    REQUIRED_PARAMS = {}

    def __init__(self, record_card, group=None) -> None:
        super().__init__()
        self.record_card = record_card
        self.group = group

    def send(self, extra_context=None, **kwargs):
        """
        Override send method for setting the recipent from the record and the default from-email.
        :param extra_context:
        :param kwargs:
        :return:
        """
        if "from_email" not in kwargs:
            kwargs["from_email"] = self.get_from_email()
        if "to" not in kwargs:
            kwargs["to"] = [self.get_to_email()]
        return super().send(extra_context, **kwargs)

    @cached_property
    def required_translated_params(self):
        """
        :return: Required params with the final translated Parameter name.
        """
        return get_required_param_names(self.lang, self.REQUIRED_PARAMS)

    @cached_property
    def configs(self) -> dict:
        """
        :return: Dynamic config params needed for rendering the email.
        """
        return Parameter.get_config_dict(self.required_translated_params.values())

    def get_from_email(self) -> str:
        """
        :return: Email for the reply-to param of the email.
        """
        return Parameter.get_parameter_by_key(self.FROM_EMAIL_PARAM)

    @abstractmethod
    def get_to_email(self) -> str:
        """
        :return: Destination email
        """
        pass

    @cached_property
    def applicant_email(self) -> str:
        """
        :return: Email of the applicant for sending the email
        """
        return self.record_card.recordcardresponse.address_mobile_email

    @cached_property
    def lang(self) -> str:
        """
        :return: Language for the answer, according to the record configuration and applicant preferences
        """
        return self.record_card.language


class ParameterTemplateEmail(BaseRecordCardEmail):
    subject_template_name = "record_cards/simple/subject.html"
    html_body_template_name = "record_cards/simple/body.html"
    body_template_name = "record_cards/simple/body.txt"
    template_renderer_cls = Iris1TemplateRenderer
    TEMPLATE_PARAM = ""

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["subject_text"] = self.get_subject()
        ctx["body_text"] = self.get_body()
        ctx["record_card"] = self.record_card
        return ctx

    def get_body(self) -> str:
        """
        :return: Body of the record card answer with all the vars replaced.
        """
        return self.renderer.render(self.template_text)

    @abstractmethod
    def get_subject(self) -> str:
        pass

    @cached_property
    def renderer(self):
        return self.template_renderer_cls(self.record_card, var_finder_cls=IrisVariableFinder)

    @cached_property
    def template_text(self):
        return get_template_param(self.lang, self.get_template_param())

    def get_template_param(self):
        return self.TEMPLATE_PARAM

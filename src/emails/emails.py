from abc import abstractmethod
from email.mime.image import MIMEImage
import logging

from bs4 import BeautifulSoup
from django.utils.timezone import localtime
from django.utils.functional import cached_property
from django_yubin.messages import TemplatedHTMLEmailMessageView, TemplatedMultipleAttachmentsEmailMessageView

from emails.base_views import ParameterTemplateEmail, BaseRecordCardEmail
from emails.break_lines import break_text_lines
from iris_masters.models import Parameter, RecordState
from iris_templates.renderer import DelimitedVarsTemplateRenderer, Iris1TemplateRenderer
from iris_templates.templates_context.record_card_vars_finder import ResponsibleGroupVariableFinder
from iris_templates.templates_context.var_filters import date, time
from main.utils import get_default_lang
from record_cards.templates import render_record_response
from django.utils.translation import gettext_lazy as _


logger = logging.getLogger(__name__)


class ResponseHashMessageEmail(TemplatedMultipleAttachmentsEmailMessageView):
    subject_template_name = "communications/emails/subject.html"
    html_body_template_name = "communications/emails/body.html"
    body_template_name = "communications/emails/body.txt"


class NotificationBaseEmail(TemplatedHTMLEmailMessageView):
    def __init__(self, group, record_cards, *args, **kwargs):
        self.group = group
        self.record_cards = record_cards
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(NotificationBaseEmail, self).get_context_data(**kwargs)
        ctx["group"] = self.group
        ctx["record_cards"] = self.record_cards
        ctx["front_url"] = Parameter.get_parameter_by_key("IRIS_RECORDS_FRONT_URL", "/backoffice/records/")
        return ctx


class NextExpireRecordsEmail(NotificationBaseEmail):
    subject_template_name = "profiles/emails/next_expire_records/subject.html"
    html_body_template_name = "profiles/emails/next_expire_records/body.html"
    body_template_name = "profiles/emails/next_expire_records/body.txt"


class PendingValidateRecordsEmail(NotificationBaseEmail):
    subject_template_name = "profiles/emails/pend_records/subject.html"
    html_body_template_name = "profiles/emails/pend_records/body.html"
    body_template_name = "profiles/emails/pend_records/body.txt"


class RecordsPendCommunications(NotificationBaseEmail):
    subject_template_name = "profiles/emails/pend_communications/subject.html"
    html_body_template_name = "profiles/emails/pend_communications/body.html"
    body_template_name = "profiles/emails/pend_communications/body.txt"


class RecordAllocationEmail(TemplatedHTMLEmailMessageView):
    subject_template_name = "profiles/emails/allocated_records/subject.html"
    html_body_template_name = "profiles/emails/allocated_records/body.html"
    body_template_name = "profiles/emails/allocated_records/body.txt"

    def __init__(self, group, record, *args, **kwargs):
        self.group = group
        self.record = record
        super().__init__(*args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(RecordAllocationEmail, self).get_context_data(**kwargs)
        ctx["group"] = self.group
        ctx["record_normalized_id"] = self.record.normalized_record_id
        ctx["records"] = [self.record]
        ctx["front_url"] = Parameter.get_parameter_by_key("IRIS_RECORDS_FRONT_URL", "/backoffice/records/")
        return ctx


class InternalClaimEmail(TemplatedHTMLEmailMessageView):
    subject_template_name = "record_cards/emails/internal_claim/subject.html"
    html_body_template_name = "record_cards/emails/internal_claim/body.html"
    body_template_name = "record_cards/emails/internal_claim/body.txt"


class CreateRecordCardEmail(ParameterTemplateEmail):
    html_body_template_name = "record_cards/emails/create_record/body.html"
    body_template_name = "record_cards/emails/create_record/body.txt"

    TEMPLATE_PARAM = "ACUSAMENT_REBUT"
    TEMPLATE_MULTI_PARAM = "ACUSAMENT_MULTI"

    def get_to_email(self) -> str:
        """
        :return: Destination email must be the applicant email
        """
        return self.applicant_email

    def get_subject(self) -> str:
        return _(u"EMAIL_REQUEST")

    def get_body(self) -> str:
        """
        :return: Body of the record card answer with all the vars replaced.
        """
        text = self.renderer.render(self.template_text)
        soup = BeautifulSoup(text, 'html.parser')
        body = soup.prettify()
        body = break_text_lines(300, body)
        return body.replace("\n", "\n<br>")

    def get_template_param(self):
        if self.record_card.multirecord_from:
            return self.TEMPLATE_MULTI_PARAM
        return super().get_template_param()


class ExternalTramitationEmail(ParameterTemplateEmail):
    """
    Email sent to external organization for informing a new job (record card).

    Since this is an email to an external organization, it will be sent only in one language. In other words, the email
    is generated with only one variable, and its language will be the language of the content written on it.
    """
    template_renderer_cls = DelimitedVarsTemplateRenderer
    SUBJECT_TEMPLATE_VAR = "CAPSALERA"
    TEMPLATE_PARAM = "PLANTILLA_DERIVACIO_EXTERNA"

    @property
    def lang(self) -> str:
        """
        :return: The fixed lang, since this email respects the content of its var.
        """
        return get_default_lang()

    def get_to_email(self) -> str:
        """
        :return: Destination email
        """
        return self.record_card.element_detail.external_email

    @abstractmethod
    def get_subject(self) -> str:
        """
        :return: Subject, defined within the parameter as CAPSALERA"
        """
        return self.renderer.get_header_context(self.template_text).get(
            self.SUBJECT_TEMPLATE_VAR, _("Requests from town council websites")
        )


class RecordCardAnswer(BaseRecordCardEmail):
    """
    Email view for sending the final answer email for the citizen/social entity.
    """
    subject_template_name = "record_cards/emails/answer/subject.html"
    html_body_template_name = "record_cards/emails/answer/body.html"
    body_template_name = "record_cards/emails/answer/body.txt"

    REQUIRED_PARAMS = {
        "subject_text": "MAILSUBJECT",
        "greeting": "TEXTCARTACAP",
        "ans_exceeded_text": "DISCULPES_RETARD",
        "appointment": "DATA_HORA_CITA_PREVIA",
        "goodbye": "TEXTCARTAFI",
        "signed": "TEXTCARTASIGNATURA",
        "footer": "PEU_CONSULTES",
        "lopd": "TEXT_LOPD",
    }

    def render_to_message(self, extra_context=None, attachments=None, *args, **kwargs):
        message = super().render_to_message(extra_context, attachments, *args, **kwargs)
        if self.group and self.group.icon:
            mime = MIMEImage(self.group.icon.read())
            mime.add_header('Content-Disposition', 'inline')
            mime.add_header('X-Attachment-Id', 'icon')
            mime.add_header('Content-ID', '<icon>')
            message.attach(mime)
        return message

    def preview(self, answer_text):
        return self.render_html_body(self.get_context_data(**{
            "body": self.get_body(answer_text),
            "title": self.record_card.normalized_record_id,
        }))

    def get_to_email(self) -> str:
        """
        :return: Destination email must be the applicant email
        """
        return self.applicant_email

    def get_context_data(self, **kwargs) -> dict:
        """
        :param kwargs:
        :return: All the vars for the answer template.
        """
        ctx = super().get_context_data(**kwargs)
        if not kwargs.get('body'):
            ctx["body"] = self.get_body()
        self.set_group_context()
        ctx.update(self.get_config_context())
        if self.renderer.context.get('firma_grup'):
            ctx['signed'] = '{}\n{}'.format(self.renderer.context.get('firma_grup'), ctx.get('signed'))
        ctx["ans_exceeded"] = self.record_card.show_late_answer_text()
        ctx["is_appointment"] = self.is_appointment
        if self.is_appointment:
            ctx["appointment"] = self.get_appointment_text(ctx["appointment"])
        ctx["lopd"] = self.get_lopd()
        ctx["record_card"] = self.record_card
        ctx.update(kwargs)
        return ctx

    @cached_property
    def renderer(self):
        return Iris1TemplateRenderer(self.record_card)

    @cached_property
    def resolution(self):
        """
        :return: True if the record card has an appointment set, in which case must be included in the email
        """
        if hasattr(self.record_card, "workflow"):
            return getattr(self.record_card.workflow, "workflowresolution", None)

    @cached_property
    def is_appointment(self) -> bool:
        """
        :return: True if the record card has an appointment set, in which case must be included in the email
        """
        return self.resolution.is_appointment if self.resolution else False

    def get_body(self, preview_text=None) -> str:
        """
        :return: Body of the record card answer with all the vars replaced.
        """
        body = render_record_response(self.record_card, preview_text, renderer=self.renderer)
        soup = BeautifulSoup(body, 'html.parser')
        body = soup.prettify()
        return body

    def set_group_context(self):
        if not self.group:
            history = self.record_card.recordcardstatehistory_set.order_by('created_at').filter(
                previous_state_id=RecordState.PENDING_ANSWER
            ).first()
            self.group = history.group if history else None
        if self.group:
            # Override with group var performing the action
            group_finder = ResponsibleGroupVariableFinder(self.group)
            group_finder.get_values(self.renderer.context, group_finder.get_vars_for_templates())

    def get_config_context(self) -> dict:
        """
        :return: Email template vars extracted from dynamic Parameters
        """
        return {t_var: render_record_response(self.record_card, self.configs[config_key], self.renderer)
                for t_var, config_key in self.required_translated_params.items()}

    def get_appointment_text(self, appointment_template) -> str:
        """
        The appointment template text must be completed with the values of the different vars.
        An example of template could be:
            "Día: data_resolucio a las hora_resol:minuts_resol con el técnico Sr/a. persona_encarregada"

        :param appointment_template: Appointment template.
        :return: Template replace with the values.
        """
        if hasattr(self.record_card.workflow, "workflowresolution"):
            resolution = self.record_card.workflow.workflowresolution
            resolution_date = localtime(resolution.resolution_date)
            constructed_date = str(resolution_date)[8:10] + '/' + str(resolution_date)[5:7] + '/' + str(resolution_date)[:4]

            # If/Else puesto para cubrir el caso de incidencia "No se envian los correos de respuesta"
            if resolution_date is not None and len(str(resolution_date)) > 15:
                replacements = {
                    "data_resolucio": constructed_date,
                    "hora_resol": str(resolution_date)[11:13],
                    "minuts_resol": str(resolution_date)[14:16],
                    "persona_encarregada": resolution.service_person_incharge
                }
                for key, value in replacements.items():
                    logger.info(f"VALUE: {value}")
                    logger.info(f"APPOINTMENT: {appointment_template.replace(key, value)}")
                    appointment_template = appointment_template.replace(key, value)
                return appointment_template
            else:
                replacements = {
                    "data_resolucio": date(resolution_date, "d/m/Y"),
                    "hora_resol": time(resolution_date, "H"),
                    "minuts_resol": time(resolution_date, "i"),
                    "persona_encarregada": resolution.service_person_incharge
                }
                for key, value in replacements.items():
                    logger.info(f"VALUE2: {value}")
                    logger.info(f"APPOINTMENT2: {appointment_template.replace(key, value)}")
                    appointment_template = appointment_template.replace(key, value)
                return appointment_template

    def get_lopd(self) -> str:
        """
        :return: GDPR from ElementDetail if it has, otherwise the default lopd configured in Parameters
        """
        if self.record_card.element_detail.lopd:
            lopd = self.record_card.element_detail.lopd
        else:
            lopd = self.get_config_context()["lopd"]
        soup = BeautifulSoup(lopd, 'html.parser')
        lopd = soup.prettify()
        return lopd

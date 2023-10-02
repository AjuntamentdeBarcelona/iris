from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.timezone import localtime

from ariadna.models import AriadnaRecord
from iris_templates.template_params import (get_template_param, APPOINTMENT_TEMPLATE, URL_RECLAMA_QUEIXES,
                                            DISCULPES_RETARD, TEXTCARTACAP)
from iris_templates.templates_context.var_filters import date, time
from iris_templates.templates_context.vars_finder import MapVariableFinder


class RecordThemeVariableFinder(MapVariableFinder):
    variables = {
        "descripcio_tema": "description",
        "descripcio_detall": "description",
        "tematica_alta": "description",
        "text_tematica": "short_description",
        "ans_detall": "description",
    }

    def get_values(self, ctx, required_variables) -> dict:
        ctx = super().get_values(ctx, required_variables)
        ctx["descripcio_element"] = self.obj.element.description
        ctx["descripcio_area"] = self.obj.element.area.description
        return ctx


class ApplicantVariableFinder(MapVariableFinder):
    variables = {
        "tag_idioma": "language",
        "tag_nom": "",
        "primer_cognom": "",
        "segon_cognom": "",
    }

    def get_values(self, ctx, required_variables) -> dict:
        ctx = super().get_values(ctx, required_variables)
        if self.obj:
            if getattr(self.obj, "citizen", None):
                ctx.update({
                    "tag_nom": self.obj.citizen.name,
                    "primer_cognom": self.obj.citizen.first_surname,
                    "segon_cognom": self.obj.citizen.second_surname,
                })
            else:
                ctx.update({
                    "tag_nom": self.obj.social_entity.social_reason,
                    "primer_cognom": "",
                    "segon_cognom": "",
                })
        return ctx


class AnswerDataVariableFinder(MapVariableFinder):
    variables = {
        "canal_resposta_fitxa": "response_channel",
        "direccio_movil": "response_destination",
    }


class ResponsibleGroupVariableFinder(MapVariableFinder):
    variables = {
        "firma_perfil": "signature",
        "firma_grup": "signature",
        "icona_perfil": "icon",
        "icona_grup": "icon",
        "icona_signatura": "icon",
    }

    def get_values(self, ctx, required_variables) -> dict:
        ctx = super().get_values(ctx, required_variables)
        if self.obj:
            signature = self.obj.signature
            signatures = self.obj.get_ancestors(ascending=False).filter(
                level__gte=1
            ).values_list('signature', flat=True)
            for s in signatures:
                if s.strip():
                    signature = f'{s}\n{signature}'
            ctx['firma_grup'] = signature
            ctx['firma_perfil'] = signature
        return ctx


class RecordCardVariableFinder(MapVariableFinder):
    """
    Generates the required vars in order to render templates associated to a RecordCard.
    """
    variables = {
        "id_fitxa": "id",
        "record_code": "normalized_record_id",
        "codi_peticio_ciutada": "normalized_record_id",
        "identificador_fitxa": "id",
        "data_peticio_ciutada": {
            "attr": "created_at",
            "filter": date,
        },
        "departament_fitxa": "creation_department",
        "descripcio_fitxa": "description",
        "text_fitxa_alta": "description",
        "nombre_reclamacions": "claims_number",
        "data_alta": {
            "attr": "created_at",
            "filter": date,
        },
        "element_detail": RecordThemeVariableFinder,
        "id_fitxa_pare": "record_parent_claimed",
        "responsible_group": ResponsibleGroupVariableFinder,
        "recordcardresponse": AnswerDataVariableFinder,
        "data_resolucio": {
            "attr": "workflow.workflowplan.start_date_process",
            "filter": date,
        },
        "request.applicant": ApplicantVariableFinder,
        "persona_encarregada": "workflow.workflowresolution.service_person_incharge",
        "primera_fitxa_multiqueixa": "multirecord_from.normalized_record_id",
        "hora_resol": "",
        "codi_fitxa": "",
        "codi_registre": "",
        "minuts_resol": "",
        "data_resol": "",
        "data_hora_resol": "",
        "adreca_carrer": "",
        "ubicacio_alta": "",
        "url_reclama_queixes": "",
        "benv_ciut": "",
        "disculpes_retard": "",
        "caracteristiques": "",
        "resposta_immediata": "",
        "codis_peticions_ciutada": "",
    }

    @cached_property
    def lang(self) -> str:
        """
        :return: Language for the answer, according to the record configuration and applicant preferences
        """
        return self.obj.language

    def get_values(self, ctx, required_variables) -> dict:
        ctx = super().get_values(ctx, required_variables)
        ctx["data_actual"] = date(timezone.now())
        if getattr(self.obj, "ubication", None):
            ctx["adreca_carrer"] = self.obj.ubication.short_address
            ctx["ubicacio_alta"] = self.obj.ubication.short_address
        self.get_parameter_var(ctx, "url_reclama_queixes", URL_RECLAMA_QUEIXES, required_variables)
        if "url_reclama_queixes" in ctx:
            ctx["url_reclama_queixes"] = ctx["url_reclama_queixes"].replace('codi_fitxa', ctx.get('record_code', ''))
        if self.obj.show_late_answer_text():
            self.get_parameter_var(ctx, "disculpes_retard", DISCULPES_RETARD, required_variables)
        else:
            ctx["disculpes_retard"] = ''
        self.get_parameter_var(ctx, "benv_ciut", TEXTCARTACAP, required_variables)
        self.get_appointment_var(ctx, required_variables)
        self.get_attributes(ctx, required_variables)
        self.get_multirecord_codes(ctx, required_variables)
        self.set_record_code(ctx)
        return ctx

    def get_parameter_var(self, ctx, var_name, param_name, required_vars):
        if var_name in required_vars:
            ctx[var_name] = get_template_param(self.lang, param_name)
        return ctx

    def get_appointment_var(self, ctx, required_variables):
        """
        Adds the appointment vars to the context. The data_hora_resol var is generated using a template saved on a
        Parameter.
        :param ctx:
        :return:
        """
        appoint_attrs = {"data_resolucio", "data_resol", "hora_resol", "minuts_resol", "persona_encarregada"}
        if hasattr(self.obj.workflow, "workflowresolution") and appoint_attrs.intersection(required_variables):
            appointment_template = get_template_param(self.lang, APPOINTMENT_TEMPLATE)
            resolution = self.obj.workflow.workflowresolution
            resolution_date = localtime(resolution.resolution_date)
            replacements = {
                "data_resolucio": date(resolution_date),
                "data_resol": date(resolution_date),
                "hora_resol": time(resolution_date, "H"),
                "minuts_resol": time(resolution_date, "i"),
                "persona_encarregada": self.obj.workflow.workflowresolution.service_person_incharge,
            }
            for key, value in replacements.items():
                appointment_template = appointment_template.replace(key, value)
            ctx.update(replacements)
            ctx["data_hora_resol"] = appointment_template
        return ctx

    def get_attributes(self, ctx, required_variables):
        if "caracteristiques" in required_variables:
            value = ",\n".join(
                self.get_attribute_string(self.obj.recordcardspecialfeatures_set.all()) +
                self.get_attribute_string(self.obj.recordcardfeatures_set.all())
            )
            ctx["caracteristiques"] = value if value.strip() else "-"

    def get_attribute_string(self, feature_qs):
        return [
            f"{attr.feature.description.upper()}: {attr.value}"
            for attr in feature_qs.select_related("feature")
        ]

    def get_multirecord_codes(self, ctx, required_variables):
        if not self.obj.is_multirecord or "codis_peticions_ciutada" not in required_variables:
            return
        main_multirecordrecord = self.obj.multirecord_from if self.obj.multirecord_from else self.obj
        brother_codes = list(main_multirecordrecord.recordcard_set.only("normalized_record_id").values_list(
            "normalized_record_id", flat=True))
        ctx["codis_peticions_ciutada"] = ", ".join([main_multirecordrecord.normalized_record_id] + brother_codes)
        return ctx

    def set_record_code(self, ctx):
        """
        When sending an answer for register created record (which have register code), the codi_fitxa var will contain
        the register code, rather than the internal IRIS record code.
        :param ctx:
        """
        try:
            ctx["codi_fitxa"] = AriadnaRecord.objects.get(record_card=self.obj).code
            ctx["codi_registre"] = ctx["codi_fitxa"]
        except AriadnaRecord.DoesNotExist:
            ctx["codi_fitxa"] = self.obj.normalized_record_id
            ctx["codi_registre"] = ""

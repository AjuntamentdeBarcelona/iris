import pytest
from django.utils.translation import activate

from emails.emails import RecordCardAnswer
from iris_masters.data_checks.parameters import check_parameters
from iris_masters.models import RecordState, Parameter
from iris_templates.data_checks.visible_parameters import check_template_parameters
from record_cards.tests.utils import CreateRecordCardMixin


@pytest.mark.django_db
class TestRecordCardAnswerEmail(CreateRecordCardMixin):
    TRANSLATED_VAL = 'TRANSLATED VALUE'

    def test_get_context(self):
        lang = 'en'
        email = self.given_a_base_email(lang)
        self.when_parameters_exists(email)
        ctx = self.when_context_is_got(email)
        self.all_fields_should_have_value(ctx)
        self.keys_should_be_translated(ctx)

    def given_a_base_email(self, lang):
        rc = self.create_record_card(record_state_id=RecordState.PENDING_ANSWER, create_record_card_response=True)
        self.set_response_text(rc)
        rc.recordcardresponse.language = lang
        rc.recordcardresponse.save()
        # LOPD not translated
        rc.element_detail.lopd = ''
        rc.element_detail.save()
        activate(lang)
        return RecordCardAnswer(
            record_card=rc
        )

    def when_parameters_exists(self, email):
        check_parameters(sender=None, update_all=True)
        check_template_parameters(sender=None, update_all=True)
        # Mark parameters that should be translated with the same value
        params = email.required_translated_params
        Parameter.objects.filter(parameter__in=params.values()).update(valor=self.TRANSLATED_VAL+'')

    def when_context_is_got(self, email: RecordCardAnswer):
        return email.get_context_data()

    def all_fields_should_have_value(self, ctx):
        missing = [key for key, val in ctx.items() if val is None]
        assert not missing, f'All keys should have value. Missing keys {missing}'

    def keys_should_be_translated(self, ctx):
        missing = {key: ctx[key] for key in RecordCardAnswer.REQUIRED_PARAMS if self.TRANSLATED_VAL not in ctx[key]}
        assert not missing, f'Context keys should be translated, the following ones are not: {missing.items()}'

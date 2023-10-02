from abc import ABCMeta, abstractmethod

from emails.emails import ExternalTramitationEmail
from iris_masters.models import Process


class ExternalValidator(metaclass=ABCMeta):
    """
    Base class for implementing external record card validators. These validators are meant for send and validate a card
    to an external service. If the service responds OK, then the record card is validated and set to its next state,
    typically in "External Management".
    """
    support_autovalidation = True

    def __init__(self, record_card):
        self.record_card = record_card

    @abstractmethod
    def validate(self, **kwargs):
        """
        :return: True if the record card is validated within the external service.
        """
        pass

    def handle_state_change(self, **kwargs):
        return False


class DummyExternalValidator(ExternalValidator):

    def __init__(self, record_card):
        self.validated = False
        super().__init__(record_card)

    def validate(self, **kwargs):
        self.validated = True
        return True


class DummyExternalValidatorNotValidate(ExternalValidator):

    def __init__(self, record_card):
        self.validated = False
        super().__init__(record_card)

    def validate(self, **kwargs):
        return self.validated


class ExternalEmailValidator(ExternalValidator):
    force_send_external = True

    def validate(self, **kwargs):
        attachments = [
            {"filename": file.filename, "attachment": file.file.read()}
            for file in self.record_card.recordfile_set.all()
        ]
        ExternalTramitationEmail(self.record_card).send(attachments=attachments)
        return True


external_validator_registry = {}


def get_external_validator(record_card):
    """
    :param record_card:
    :return: ExternalValidator for the given record card.
    :rtype: ExternalValidator
    """
    if record_card.process_id == Process.EXTERNAL_PROCESSING_EMAIL:
        return ExternalEmailValidator(record_card)
    external_service = record_card.element_detail.external_service
    if not external_service:
        return
    validator_cls = external_validator_registry.get(external_service.sender_uid, None)
    return validator_cls(record_card, external_service) if validator_cls else None

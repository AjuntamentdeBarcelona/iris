from django_yubin.messages import TemplatedEmailMessageView


class MailView(TemplatedEmailMessageView):

    def __init__(self, record_state, record_id):
        self.record_state = record_state
        self.record_id = record_id

    def get_context_data(self, **kwargs):
        """
        here we can get the additional data we want
        """
        context = super(MailView, self).get_context_data(**kwargs)
        context['record_card_state'] = self.record_state
        context['record_card_id'] = self.record_id
        return context


class CloseRecordEmail(MailView):
    subject_template_name = 'emails/closed_emails/subject.html'
    body_template_name = 'emails/closed_emails/body.html'

from model_mommy import mommy
from rest_framework import status

from main.open_api.tests.base import BaseOpenAPITest

from iris_masters.models import RecordState
from main.urls import PUBLIC_API_URL_NAME
from record_cards.tests.utils import CreateRecordCardMixin
from surveys.models import Question, Survey, SurveyAnswer, QuestionReason


class TestSurveyMixin(CreateRecordCardMixin):
    QUESTION_NUMBER = 3
    SURVEY_SLUG = 'web-survey'

    def given_an_object(self, state):
        return self.create_record_card(record_state_id=state)

    def when_exists_survey_questions(self):
        survey = mommy.make(Survey, slug=self.SURVEY_SLUG, active=True)
        [mommy.make(Question, survey=survey) for _ in range(1, self.QUESTION_NUMBER)]
        return survey

    def when_answer_exists(self, record_card, survey):
        return mommy.make(SurveyAnswer, record_card=record_card, survey=survey)


class TestSurveyAttrList(TestSurveyMixin, BaseOpenAPITest):
    path = '/surveys/{survey}/{record_id}'
    base_api_path = '/services/iris/api-public'
    open_api_url_name = PUBLIC_API_URL_NAME

    def test_non_closed_record_card(self):
        self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.PENDING_ANSWER)
        resp = self.when_questions_are_retrieved(rc)
        assert resp.status_code == 200
        assert not resp.data['ready']
        assert not resp.data['closed']
        assert not resp.data['can_answer']
        assert len(resp.data['questions']) == 0

    def test_closed_record_card(self):
        self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        resp = self.when_questions_are_retrieved(rc)
        assert resp.status_code == 200
        assert not resp.data['ready']
        assert resp.data['closed']
        assert resp.data['can_answer']
        assert len(resp.data['questions']) > 0

    def test_answered_survey(self):
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        self.when_answer_exists(rc, survey)
        resp = self.when_questions_are_retrieved(rc)
        assert resp.status_code == 200
        assert resp.data['ready']
        assert resp.data['closed']
        assert not resp.data['can_answer']
        assert len(resp.data['questions']) == 0

    def when_questions_are_retrieved(self, rc):
        return self.operation_test('get', self.path, self.spec()['paths'][self.path]['get'], {
            'record_id': rc.normalized_record_id,
            'survey': self.SURVEY_SLUG
        })


class TestSurveyAnswer(TestSurveyMixin, BaseOpenAPITest):
    path = '/surveys/{survey}/{record_id}/answer'
    base_api_path = '/services/iris/api-public'
    open_api_url_name = PUBLIC_API_URL_NAME
    SURVEY_SLUG = 'web-survey'

    def test_create_answered(self):
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        self.when_answer_exists(rc, survey)
        self.answers = self.when_all_questions_are_answered(survey)
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_create_non_closed(self):
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.PENDING_ANSWER)
        self.answers = self.when_all_questions_are_answered(survey)
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_409_CONFLICT

    def test_create_valid(self):
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        self.answers = self.when_all_questions_are_answered(survey)
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_with_missing_questions(self):
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        missing, self.answers = self.when_questions_are_missing(survey)
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        for missed in missing:
            assert missed['question'] in resp.data['missing']

    def test_with_invalid_answers(self):
        ERROR_INDEX = 1
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        self.answers = self.when_all_questions_are_answered(survey)
        self.answers[ERROR_INDEX]['value'] = -1
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert len(resp.data['invalid'][ERROR_INDEX]) > 0, 'Invalid answers must be returned in the same array index'

    def test_with_reasons(self):
        REASON_INDEX = 1
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        self.answers = self.when_all_questions_are_answered(survey)
        reason = self.when_exists_reason_for_question(self.answers[REASON_INDEX]['question'])
        self.answers[REASON_INDEX]['value'] = 2
        self.answers[REASON_INDEX]['reason'] = reason.pk
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_201_CREATED

    def test_with_invalid_reason(self):
        ERROR_INDEX = 1
        survey = self.when_exists_survey_questions()
        rc = self.given_an_object(RecordState.CLOSED)
        self.answers = self.when_all_questions_are_answered(survey)
        self.answers[ERROR_INDEX]['value'] = 2
        self.answers[ERROR_INDEX]['reason'] = mommy.make(QuestionReason).pk
        resp = self.when_questions_are_answered(rc, self.answers)
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert len(resp.data['invalid'][ERROR_INDEX]) > 0, 'Invalid answers must be returned in the same array index'

    def get_body_parameters(self, path_spec, force_params):
        return self.answers

    def when_exists_reason_for_question(self, question_id):
        return mommy.make(QuestionReason, question_id=question_id)

    def when_all_questions_are_answered(self, survey):
        return [
            {
                'value': 6,
                'question': q.pk,
                'reason': None,
            }
            for q in survey.questions.all()
        ]

    def when_questions_are_missing(self, survey):
        expected = self.when_all_questions_are_answered(survey)
        return expected[1:], expected[:1]

    def when_questions_are_answered(self, rc, answers):
        return self.operation_test('post', self.path, self.spec()['paths'][self.path]['post'], {
            'record_id': rc.normalized_record_id,
            'survey': self.SURVEY_SLUG,
            'data': answers,
        })

from django.contrib import admin

from surveys.models import Survey, Question, QuestionReason


class SurveyQuestionInline(admin.TabularInline):
    fields = ("text", "active")
    model = Question

    def has_delete_permission(self, request, obj=None):
        return False


class QuestionReasonInline(admin.TabularInline):
    fields = ("text",)
    model = QuestionReason

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    fields = ("title", "slug", "active")
    inlines = (SurveyQuestionInline, )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    fields = ("text", "active")
    inlines = (QuestionReasonInline, )

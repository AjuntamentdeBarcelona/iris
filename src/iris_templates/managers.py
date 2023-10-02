
from django.db import models


class IrisTemplateRecordTypesManager(models.Manager):

    def unique_response_type_for_record_type(self, record_type_pk, response_type_pk, iris_template_pk):
        qs = self.filter(record_type_id=record_type_pk, iris_template__response_type_id=response_type_pk, enabled=True)
        if iris_template_pk is not None:
            qs = qs.exclude(iris_template_id=iris_template_pk)
        return not qs.exists()

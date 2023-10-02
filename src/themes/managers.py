from django.db import models


class ElementDetailFeatureManager(models.Manager):

    def get_features_pk(self):
        return self.filter(enabled=True, feature__deleted__isnull=True).select_related(
            "feature").order_by("feature_id").values_list("feature_id", flat=True)

    def get_mandatory_features_pk(self):
        return self.filter(enabled=True, feature__deleted__isnull=True, is_mandatory=True).select_related(
            "feature").order_by("feature_id").values_list("feature_id", flat=True)

    def get_public_features_pk(self, allow_hidden=False):
        if allow_hidden:
            qs = self.filter(enabled=True, feature__deleted__isnull=True)
        else:
            qs = self.filter(enabled=True, feature__deleted__isnull=True,
                             feature__visible_for_citizen=True)
        return qs.select_related(
            "feature").order_by("feature_id").distinct("feature").values_list("feature_id", flat=True)

    def get_public_mandatory_features_pk(self):
        return self.filter(enabled=True, feature__deleted__isnull=True, is_mandatory=True,
                           feature__visible_for_citizen=True).select_related(
            "feature").order_by("feature_id").distinct("feature").values_list("feature_id", flat=True)


class ApplicationElementDetailManager(models.Manager):
    enabled_params = {
        "enabled": True,
        "application__enabled": True,
        "detail__deleted__isnull": True,
        "detail__element__deleted__isnull": True,
        "detail__element__area__deleted__isnull": True
    }

    def set_params(self, application):
        params = {"application": application}
        params.update(self.enabled_params)
        return params

    def get_elementdetailpks_byapp(self, application):
        return self.filter(**self.set_params(application)).values_list("detail_id", flat=True).distinct()

    def get_elementdetailpks_multiple_apps(self, applications_pks):
        params = {"application_id__in": applications_pks}
        params.update(self.enabled_params)
        return self.filter(**params).values_list("detail_id", flat=True).distinct()

    def get_elementpks_byapp(self, application):
        return self.filter(**self.set_params(application)).select_related("detail").values_list(
            "detail__element_id", flat=True).distinct()

    def get_areapks_byapp(self, application):
        return self.filter(**self.set_params(application)).select_related("detail", "detail__element").values_list(
            "detail__element__area_id", flat=True).distinct()

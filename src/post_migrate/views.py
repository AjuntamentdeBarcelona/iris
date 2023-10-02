from django.core.management import call_command
from django.utils.decorators import method_decorator
from drf_yasg.utils import swagger_auto_schema
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from features.masks import check_masks
from iris_masters.tasks import masters_data_checks
from features.models import Feature
from iris_templates.data_checks.visible_parameters import check_template_parameters
from profiles.permission_registry import PERMISSIONS
from profiles.tasks import profiles_data_checks
from record_cards.tasks import (set_record_card_audits, post_migrate_years, remove_applicant_zero,
                                recover_claims_response_config, recover_close_user_audit, recover_ans_limits,
                                recover_claims_closing_dates, recover_theme_changed_info)
from themes.data_checks.zones import check_zones
from themes.tasks import rebuild_theme_tree, set_themes_ambits, set_response_channel_none_to_themes
from integrations.tasks import post_migrate_tasks as integrations_post_migrate_tasks


@method_decorator(name="post", decorator=swagger_auto_schema(responses={
    HTTP_204_NO_CONTENT: "Post migrate tasks queued"
}))
class PostMigrateView(APIView):
    """
    Run the post-migrate tasks:
     - masters data checks
     - permission creation
     - template parameters datachecks
     - masks datacheck
     - zones datacheck
     - delay profiles datachecks
     - remove applicant zero
     - update citizen birth year if it's lower than 1900
     - Rebuild the theme tree
     - full-fill RecordCard ambits
     - create External Services
     - if remove-email GET parameter is set to "1", clean mails register
     - if set-rchannel-none GET parameter is set to "1", set response channel None to all the ElementDetails
    """

    def post(self, request, *args, **kwargs):
        if request.GET.get("recover-responses", "0") == "1":
            recover_claims_response_config.delay()
            return Response(status=HTTP_204_NO_CONTENT)
        if request.GET.get("recover-close-audits", "0") == "1":
            recover_close_user_audit.delay()
            return Response(status=HTTP_204_NO_CONTENT)
        if request.GET.get("recover-ans-limits", "0") == "1":
            recover_ans_limits.delay()
            return Response(status=HTTP_204_NO_CONTENT)
        if request.GET.get("recover-claims-closingdate", "0") == "1":
            recover_claims_closing_dates.delay()
            return Response(status=HTTP_204_NO_CONTENT)
        if request.GET.get("recover-theme-changed-info", "0") == "1":
            recover_theme_changed_info.delay()
            return Response(status=HTTP_204_NO_CONTENT)

        masters_data_checks.delay()
        PERMISSIONS.create_db_permissions()
        check_template_parameters(None)
        check_masks(None)
        Feature.objects.filter(mask_id__isnull=True).update(mask_id=1)
        check_zones(None)
        # set_group_plates inside profiles_data_checks does the rebuildtree before calculating plates
        profiles_data_checks.delay()
        remove_applicant_zero.delay()
        post_migrate_years.delay()
        rebuild_theme_tree.delay()
        set_themes_ambits.delay()
        set_record_card_audits.delay()
        integrations_post_migrate_tasks.delay()
        if request.GET.get('remove-email', '0') == '1':
            call_command('cleanup_mail', days=0)
        if request.GET.get('set-rchannel-none', '0') == '1':
            set_response_channel_none_to_themes.delay()
        return Response(status=HTTP_204_NO_CONTENT)

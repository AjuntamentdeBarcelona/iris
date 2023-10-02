import logging
from threading import Thread

from django.conf import settings
from django.db.models import Q
from django.utils.functional import cached_property

try:
    use_mib = True
    # This should be removed, and provide a valid injection mechanism.
    # Is a temporal workaround for backwards compatibility.
    from integrations.services.mib.hooks import (modify_citizen_into_mib, modify_social_entity_into_mib, mib_is_active,
                                                 search_citizen_into_mib_with_origin, get_origin,
                                                 search_social_entity_into_mib_with_origin)
    from integrations.tasks import sync_citizen_to_mib, sync_social_entity_to_mib
except ImportError:
    use_mib = False
    search_citizen_into_mib_with_origin = None
    modify_citizen_into_mib = None
    modify_social_entity_into_mib = None
    mib_is_active = None
    get_origin = lambda: 1
    search_social_entity_into_mib_with_origin = None
    sync_citizen_to_mib = None
    sync_social_entity_to_mib = None

from record_cards.models import Applicant, Citizen, SocialEntity

logger = logging.getLogger(__name__)


class ApplicantSource:
    """
    IRIS must find applicants both in its database and in external service. The applicant source is responsible of
    finding them over a medium.
    """

    def find_by_nif(self, id_number):
        return []

    def find_by_name(self, name, first_surname, second_surname, full_normalized_name):
        return []

    def find_by_cif(self, id_number):
        return []

    def find_by_social_reason(self, social_reason):
        return []

    def sync_to_origin(self, applicant):
        """
        Syncs applicant to an external source. Each source is responsible of deciding if an apllicant must be synced.
        :param applicant:
        :return: Applicant after sync
        """
        return applicant


class EmptyResults(Exception):
    pass


class MibSource(ApplicantSource):
    DOC_TYPES = {
        "01": Citizen.NIF,
        "02": Citizen.PASS,
        "03": Citizen.NIE,
    }

    @cached_property
    def iris_origin(self):
        return int(get_origin())

    @cached_property
    def is_active(self):
        return mib_is_active()

    def find_by_nif(self, id_number, type_document=""):
        return [self.mib_to_citizen(mib_cit)
                for mib_cit in self.find_on_mib(search_citizen_into_mib_with_origin, document=id_number,
                                                type_document=type_document)]

    def find_by_name(self, name, first_surname, second_surname, full_normalized_name):
        return [self.mib_to_citizen(mib_cit)
                for mib_cit in self.find_on_mib(search_citizen_into_mib_with_origin, name=name,
                                                first_surname=first_surname, second_surname=second_surname,
                                                type_document="")]

    def find_by_cif(self, id_number):
        return [self.mib_to_social_entity(mib_se)
                for mib_se in self.find_on_mib(search_social_entity_into_mib_with_origin, cif=id_number)]

    def find_by_social_reason(self, social_reason):
        return [self.mib_to_social_entity(mib_se)
                for mib_se in self.find_on_mib(search_social_entity_into_mib_with_origin,
                                               social_reason=social_reason)]

    def sync_to_origin(self, applicant):
        if self.is_active:
            logger.info("MIB|SYNC|{}|Start".format(applicant.id))
            if applicant.citizen_id:
                logger.info("MIB|SYNC|{}|SEARCH WITH DOC TYPE {}".format(applicant.id, applicant.citizen.doc_type))
                result = self.find_by_nif(applicant.citizen.dni, applicant.citizen.doc_type)
                self._sync_info_to_mib(applicant, result, sync_citizen_to_mib, modify_citizen_into_mib)
            else:
                result = self.find_by_cif(applicant.social_entity.cif)
                self._sync_info_to_mib(applicant, result, sync_social_entity_to_mib, modify_social_entity_into_mib)

    def _sync_info_to_mib(self, applicant, result, create_on_mib, modify_on_mib):
        logger.info("MIB|SYNC|{}|FOUND {} ON MIB".format(applicant.id, len(result)))
        if applicant.info.mib_code:
            result = [res for res in result if int(res.info.mib_code) == int(applicant.info.mib_code)]
        logger.info("MIB|SYNC|{}|FOUND {} WITH THE CODE ON MIB".format(applicant.id, len(result)))
        if result:
            if getattr(result[0], "origin", 0) < self.iris_origin:
                logger.info("MIB|SYNC|{}|SYNC FROM MIB WITH ORIGIN {}".format(applicant.id, result[0].origin))
                self.update_iris_from_mib(applicant, result[0])
            else:
                if not applicant.info.mib_code:
                    logger.info("MIB|SYNC|{}|SAVING MISSING MIB CODE {}".format(applicant.id,
                                                                                result[0].info.mib_code))
                    applicant.info.mib_code = result[0].info.mib_code
                    applicant.info.save()
                logger.info("MIB|SYNC|{}|{}|MODIFY ON MIB".format(applicant.id, applicant.info.mib_code))
                modify_on_mib(applicant.info.id)
        else:
            if applicant.info.mib_code:
                logger.info("MIB|SYNC|{}|{}|MODIFY ON MIB".format(applicant.id, applicant.info.mib_code))
                modify_on_mib(applicant.info.id)
            else:
                logger.info("MIB|SYNC|{}|CREATE ON MIB".format(applicant.id))
                create_on_mib(applicant.info.id)

    def find_on_mib(self, search_fn, **kwargs):
        if not self.is_active:
            return []
        merged = {}
        results = search_fn(**kwargs)
        for result in results:
            key = result["document"]
            if key not in merged:
                merged[key] = result
            elif result.get("origin", 1) < merged[key].get("origin", 1):
                merged[key] = result
        return merged.values()

    def mib_to_citizen(self, mib_cit):
        mib_cit["doc_type"] = self.DOC_TYPES.get(mib_cit.pop("document_type"), Citizen.PASS)
        mib_cit["dni"] = mib_cit.pop("document")
        origin = int(mib_cit.pop("origin", 1))
        mib_cit.pop("social_reason", None)
        applicant = Applicant(
            citizen=Citizen(**mib_cit)
        )
        setattr(applicant, "origin", origin)
        return applicant

    def mib_to_social_entity(self, mib_cit):
        mib_cit.pop("document_type")
        mib_cit["cif"] = mib_cit.pop("document")
        mib_cit.pop("name", None)
        mib_cit.pop("first_surname", None)
        mib_cit.pop("second_surname", None)
        origin = int(mib_cit.pop("origin", 1))
        applicant = Applicant(
            social_entity=SocialEntity(**mib_cit)
        )
        setattr(applicant, "origin", origin)
        return applicant

    def update_iris_from_mib(self, applicant, mib_applicant):
        applicant.info.mib_code = mib_applicant.info.mib_code
        if applicant.citizen_id:
            applicant.citizen.name = mib_applicant.info.name
            applicant.citizen.first_surname = mib_applicant.info.first_surname
            applicant.citizen.second_surname = mib_applicant.info.second_surname
        else:
            applicant.info.mib_code = mib_applicant.info.mib_code
            applicant.info.social_reason = mib_applicant.info.social_reason
        applicant.info.save()


class IrisDBSource(ApplicantSource):
    """
    ApplicantSource with IRIS2 db as store. Mainly it uses the django models.
    """
    CITIZEN_NAME = ["name", "first_surname", "second_surname", "full_normalized_name"]
    LIMIT = 10
    DOC_TYPE = "04"

    def find_by_nif(self, id_number):
        return self.set_origin(
            self.get_citizen_qs().filter(citizen__dni__icontains=id_number)[:self.LIMIT]
        )

    def find_by_name(self, **kwargs):
        lookups = {f"citizen__{attr}__unaccent__ilike_contains": kwargs.get(attr)
                   for attr in self.CITIZEN_NAME if kwargs.get(attr)}
        return self.set_origin(
            self.get_citizen_qs().filter(**lookups)[:self.LIMIT]
        )

    def find_by_cif(self, id_number):
        return self.set_origin(
            self.get_social_entity_qs().filter(social_entity__cif__icontains=id_number)[:self.LIMIT]
        )

    def find_by_social_reason(self, social_reason):
        return self.set_origin(
            self.get_social_entity_qs().filter(social_entity__social_reason__icontains=social_reason)[:self.LIMIT]
        )

    def sync_to_origin(self, applicant):
        data = applicant.citizen if applicant.citizen else applicant.social_entity
        data.save()
        applicant.save()
        return applicant

    def get_citizen_qs(self):
        return Applicant.objects.select_related("citizen")

    def get_social_entity_qs(self):
        return Applicant.objects.select_related("social_entity")

    def set_origin(self, qs):
        result = list(qs)
        origin = int(get_origin())
        for applicant in result:
            setattr(applicant, 'origin', origin)
        return result


class IrisSource(ApplicantSource):
    """
    ApplicantSource that merge results from known IRIS sources.
    """
    DEFAULT_SOURCES = [IrisDBSource()] + ([MibSource()] if use_mib else [])
    AVOID_SYNC = [IrisDBSource]

    def __init__(self, sources=None):
        self.sources = sources if sources else self.DEFAULT_SOURCES

    def find(self, filters):
        if "dni" in filters:
            return self.find_by_nif(id_number=filters["dni"])
        elif "cif" in filters:
            return self.find_by_cif(id_number=filters["cif"])
        elif "social_reason" in filters:
            return self.find_by_social_reason(social_reason=filters["social_reason"])
        else:
            return self.find_by_name(
                name=filters.get("name"),
                first_surname=filters.get("first_surname"),
                second_surname=filters.get("second_surname"),
                full_normalized_name=filters.get("full_normalized_name")
            )

    def find_by_nif(self, **kwargs):
        return self.find_by("find_by_nif", **kwargs)

    def find_by_name(self, **kwargs):
        return self.find_by("find_by_name", **kwargs)

    def find_by_cif(self, **kwargs):
        return self.find_by("find_by_cif", **kwargs)

    def find_by_social_reason(self, **kwargs):
        return self.find_by("find_by_social_reason", **kwargs)

    def find_by(self, method, **kwargs):
        results = self.concurrent_search(method, **kwargs)
        results = self.merge_applicants(results)
        return self.merge_with_existent_in_iris(results).values()

    def concurrent_search(self, method, **kwargs):
        """
        Performs the search over the sources in a concurrent way.
        :param method:
        :param kwargs:
        :return: Applicant lists.
        """
        results = []
        calls = []

        def find_results(source, method, kwargs, results):
            try:
                results += getattr(source, method)(**kwargs)
            except EmptyResults:
                results.append([])
            except Exception as e:
                logger.exception(e)
                raise e

        for source in self.sources:
            process = Thread(target=find_results, args=[source, method, kwargs, results])
            process.start()
            calls.append(process)
        [process.join() for process in calls]
        return results

    def merge_applicants(self, applicants, merged=None):
        """
        :param merged: Current applicant dict
        :type: dict
        :param applicants:
        :return: Merged list of applicants, mapped by its legal_id
        :type: dict
        """
        merged = merged if merged else {}
        for applicant in applicants:
            if applicant.info:
                if applicant.info.legal_id.upper() == settings.CITIZEN_ND:
                    key = applicant.pk
                else:
                    key = applicant.info.legal_id
                if key in merged:
                    merged_applicant = self.merge_applicant_data(applicant, merged[key])
                    merged[key] = merged_applicant
                else:
                    merged[key] = applicant
        return merged

    def merge_with_existent_in_iris(self, merged):
        """
        One or more results from external services can exist in IRIS, we must find and merge them.
        :return: Merged list of applicants, possibly extended with IRIS db data.
        """
        missing = [applicant for applicant in merged.values() if not applicant.id]
        if not missing:
            return merged
        dnis = [applicant.info.dni for applicant in missing if applicant.citizen]
        cifs = [applicant.info.cif for applicant in missing if applicant.social_entity]
        if not dnis and not cifs:
            return merged
        lookup = Q()
        if dnis:
            lookup |= Q(citizen__dni__in=dnis)
        if cifs:
            lookup |= Q(social_entity__cif__in=cifs)
        iris_applicants = Applicant.objects.filter(lookup).select_related("social_entity", "citizen")
        return self.merge_applicants(iris_applicants, merged)

    def merge_applicant_data(self, first, second):
        """
        Each source defines a level of priority for the merge.
        :param first: Second applicant being merged
        :type: Applicant
        :param second: Second applicant being merged
        :type: Applicant
        :return: Applicant with merged data
        """
        if first.origin <= second.origin:
            return self._assign_applicant_data(second, first)
        return self._assign_applicant_data(first, second)

    def _assign_applicant_data(self, to_applicant, from_applicant):
        """
        :param to_applicant: Applicant that will be overwritten by from_applicant
        :type: Applicant
        :param from_applicant: Applicant that will be assigned to to_applicant
        :type: Applicant
        :return: to_applicant updated
        :rtype: Applicant
        """
        if to_applicant.info.legal_id == from_applicant.info.legal_id:
            if from_applicant.id:
                to_applicant.id = from_applicant.id
            if not to_applicant.info.id:
                to_applicant.info.id = from_applicant.info.id
            if not to_applicant.citizen_id:
                to_applicant.citizen_id = from_applicant.citizen_id
            if not to_applicant.social_entity_id:
                to_applicant.social_entity_id = from_applicant.social_entity_id
            to_applicant.info.copy_from(from_applicant.info)
            to_applicant.info.save()
        if to_applicant.id:
            if not to_applicant.created_at:
                to_applicant.created_at = from_applicant.created_at
            to_applicant.save()
        return to_applicant

    def sync_to_origin(self, applicant):
        """
        :param applicant:
        :type: Applicant
        """
        for source in self.sources:
            if source.__class__ not in self.AVOID_SYNC:
                source.sync_to_origin(applicant)

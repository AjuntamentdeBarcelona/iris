import io
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from PyPDF2 import PdfFileMerger

from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.translation import pgettext

from emails.emails import RecordCardAnswer
from iris_masters.models import RecordState
from iris_templates.templates_context.var_filters import date
from main.core.ordinal import cat_ordinal
from record_cards.models import RecordCardResponse
from integrations.services.letter.services import LetterServices
from integrations.services.pdf.services import PdfServices
from iris_masters.models import LetterTemplate
from record_cards.models import RecordCard, RecordFile
import pysftp

from record_cards.templates import render_record_response

logger = logging.getLogger(__name__)


def verbose_floor(floor):
    floor = floor.strip()
    if floor != '':
        try:
            n = int(floor)
            if n == 0:
                return 'Baixos'
            return cat_ordinal(n)
        except ValueError:
            return floor
    return floor


def verbose_stair(stair):
    return pgettext('Stair abbreviation', 'Esc. {}', ).format(stair)


def get_sicon_address(via_type, via_name, number, stair, floor, door):
    parts = []
    parts.append(f'{via_type.strip()} {via_name.strip()}' if via_type not in via_name else via_name)
    parts.append(number)
    if stair.strip():
        parts.append(verbose_stair(stair))
    if number or door:
        parts.append(f'{verbose_floor(floor)} {door}'.strip(' '))
    result = ', '.join(parts)
    if len(result) > 60:
        via_name = via_name[:40]
    parts = []
    parts.append(f'{via_type.strip()} {via_name.strip()}' if via_type not in via_name else via_name)
    parts.append(number)
    if stair.strip():
        parts.append(verbose_stair(stair))
    if number or door:
        parts.append(f'{verbose_floor(floor)} {door}'.strip(' '))
    result = ', '.join(parts)
    return result[:60]


def get_sicon_city(postal_code, municipality, province):
    if not province or municipality.strip().lower() == province.strip().lower():
        return f'{postal_code} {municipality}'
    return f'{postal_code} {municipality} ({province})'


def get_sicon_date(d):
    return f"{settings.CITY}, {date(d)}"


def get_lopd(record_card):
    return RecordCardAnswer(record_card).get_lopd()


def render_letter_text(record_card, letter_text=None, group=None):
    """
    Render the answer text using the same context as email, it contains the rendered variables
    :param record_card:
    :param letter_text:
    :return:

    NOT USED!
    """
    return render_to_string('letters/answer.html', RecordCardAnswer(record_card, group=group).get_context_data(**{
        'body': letter_text,
    }))


def get_citizen_name(record_card):
    if record_card.request.applicant:
        if record_card.request.applicant.citizen_id:
            citizen_data = record_card.request.applicant.citizen
            return citizen_data.name + ' ' + citizen_data.first_surname + ' ' + citizen_data.second_surname
        elif record_card.request.applicant.social_entity_id:
            se = record_card.request.applicant.social_entity
            return se.contact + ' ' + se.social_reason
        else:
            return ''
    #  Non applicant record
    return ''


def get_group_user(record_card, group):
    if group:
        return (group)
    history = record_card.recordcardstatehistory_set.order_by('created_at').filter(
        previous_state_id=RecordState.PENDING_ANSWER
    ).first()
    return (history.group, history.user_id) if history else (record_card.responsible_profile, record_card.user_id)


def create_letter_code(record_card, template_description=None, letter_text=None, group=None):
    """
    Generate PDF/XML
    """
    old = translation.get_language()
    translation.activate(record_card.language)
    if group:
        group = get_group_user(record_card, group)
        user = None
    else:
        group, user = get_group_user(record_card, group)
    if not template_description and (group.letter_template_id_id or group.letter_template_id_id == 0):
        template_description = group.letter_template_id.name
    logger.info(group.id)
    logger.info(f'RECORD CARD | {record_card.normalized_record_id} | PDF | PDF TEMPLATE: {template_description}')

    name = get_citizen_name(record_card)
    resp_data = RecordCardResponse.objects.get(record_card_id=record_card.pk)
    if resp_data.via_name:
        address = get_sicon_address(resp_data.via_type, resp_data.via_name, resp_data.number,
                                    resp_data.stair, resp_data.floor, resp_data.door)
    else:
        address = get_sicon_address(resp_data.via_type, resp_data.address_mobile_email, resp_data.number,
                                    resp_data.stair, resp_data.floor, resp_data.door)
    city = get_sicon_city(resp_data.postal_code, resp_data.municipality, resp_data.province)
    sign_text = group.signature
    letter_text = render_record_response(record_card, letter_text)
    rdto_data = {
        "format": "PDF",
        "idioma": "CA",
        "nomPlantilla": template_description,
        "versio": "01"
    }
    xml_json_data = {
        "textFirma": '<![CDATA[' + sign_text + ']]>',
        "nom": '<![CDATA[' + name + ']]>',
        "adreca": '<![CDATA[' + address + ']]>',
        "ciutat": '<![CDATA[' + city + ']]>',
        "textCarta": '<![CDATA[' + letter_text.replace('&nbsp;', '<br><br>') + ']]>',
        "data": '<![CDATA[' + get_sicon_date(timezone.now()) + ']]>',
        "lopd": '<![CDATA[' + get_lopd(record_card) + ']]>',
    }
    for key, value in xml_json_data.items():
        if not value:
            xml_json_data[key] = ''
        elif not value.strip():
            xml_json_data[key] = ''
    logger.info(f'RECORD CARD | {record_card.normalized_record_id} | PDF | CREATE PDF DATA: {xml_json_data}')
    logger.info(f'RECORD CARD | {record_card.normalized_record_id} | PDF | CREATING PDF TEMPLATE: {rdto_data}')
    result = LetterServices().send_to_report(xml_json_data, rdto_data)
    result_xml = create_letter_xml(name, address, resp_data.postal_code,
                                   resp_data.municipality,
                                   resp_data.province,
                                   record_card.normalized_record_id,
                                   user) if user else None
    logger.info(f'RECORD CARD | {record_card.normalized_record_id} | PDF | CREATED')
    translation.activate(old)
    return result, result_xml


def create_letter_xml(name, address, postal_code,
                      municipality, province,
                      normalized_record_id, user):
    xml_json_data = {
        "nomDestinatari": name,
        "adreca": address,
        "codiPostal": postal_code,
        "municipi": municipality.upper(),
        "provincia": province.upper(),
        "codiFitxa": normalized_record_id,
        "codigoSicer": normalized_record_id,
        "Matriculaempleado": user
    }
    result_xml = PdfServices(xml_file=True).create_xml(xml_json_data, encoding="ISO-8859-1")
    return result_xml.encode(encoding="ISO-8859-1")


def move_to_sftp(file_name, buffer):
    buffer.seek(0)
    real_file_name = file_name.split('/')[-1]
    file_name = 'SICON/' + real_file_name
    dest_path = settings.SFTP_PATH
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None
    sftp_hostname = settings.SFTP_HOSTNAME
    sftp_username = settings.SFTP_USERNAME
    sftp_password = settings.SFTP_PASSWORD
    with pysftp.Connection(host=sftp_hostname,
                           username=sftp_username,
                           password=sftp_password,
                           cnopts=cnopts) as sftp:
        sftp.putfo(buffer, dest_path+file_name)


def create_pdf(record_card_id, file_name=None):
    record_card = RecordCard.objects.get(pk=record_card_id)
    template_name = LetterTemplate.objects.get(id=record_card.responsible_profile.letter_template_id.pk).name
    logger.info(f"RECORD CARD | {record_card.normalized_record_id} | LETTER | CREATE FROM TEMPLATE: {template_name}")
    if not file_name:
        file_name = f"sicon/{template_name}_{record_card.normalized_record_id}.pdf"
    pdf_content, xml_content = create_letter_code(record_card)
    # upload pdf file
    default_storage.delete(file_name)
    buffer = io.BytesIO()
    pdf_merger = PdfFileMerger()
    pdf_merger.append(ContentFile(pdf_content.content))
    attached_files = RecordFile.objects.filter(file_type=4, record_card_id=record_card.pk).order_by("created_at")
    if attached_files:
        for attachment in attached_files:
            pdf_merger.append(ContentFile(attachment.file.read()))
    pdf_merger.write(buffer)
    move_to_sftp(file_name, buffer)
    buffer.seek(0)
    default_storage.save(file_name, buffer)
    buffer.seek(0)
    logger.info(f"RECORD CARD | {record_card.normalized_record_id} | LETTER | SENT: {file_name}")
    # upload xml file
    if xml_content:
        file_name = file_name.replace('pdf', 'xml')
        buffer = io.BytesIO()
        default_storage.delete(file_name)
        move_to_sftp(file_name, ContentFile(xml_content))
        default_storage.save(file_name, ContentFile(xml_content))
        logger.info(f"RECORD CARD | {record_card.normalized_record_id} | LETTER XML | SENT: {file_name}")

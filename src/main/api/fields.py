import io

import PyPDF2

from django.core.files.base import ContentFile
from django.utils.translation import ugettext_lazy as _
from drf_extra_fields.fields import Base64FileField
import docx2txt
from openpyxl.reader.excel import ExcelReader


class CustomBase64File(Base64FileField):
    ALLOWED_TYPES = ["pdf", "docx", "xlsx"]
    INVALID_TYPE_MESSAGE = _("File extension is not allowed")

    def get_file_extension(self, filename, decoded_file):
        try:
            PyPDF2.PdfFileReader(io.BytesIO(decoded_file))
            return "pdf"
        except PyPDF2.utils.PdfReadError:
            pass

        try:
            docx_file = ContentFile(decoded_file)
            docx2txt.process(docx_file)
            return "docx"
        except Exception:
            pass

        try:
            excel_file = ContentFile(decoded_file, "test.xlsx")
            ExcelReader(excel_file)
            return "xlsx"
        except Exception:
            pass

        return None

import re


def get_record_code_from_text(text):
    # I09345848L-01
    regex1 = "\D\d{8}\D-\d{2}"  # noqa W605
    # 4381BZC-02
    regex2 = "\d{4}\D{3}-\d{2,}"  # noqa W605
    # 4381BZC
    regex3 = "\d{4}\D{3}"  # noqa W605
    # 039AUIB-02
    regex4 = "\d{3}[A-Za-z]{4}-\d{2,}"  # noqa W605
    # 039AUIB
    regex5 = "\d{3}[A-Za-z]{4}"  # noqa W605
    # AAA1234-02
    regex6 = "\D{3}\d{4}-\d{2,}"  # noqa W605
    # AAA1234
    regex7 = "\D{3}\d{4}"  # noqa W605

    regexs = [regex1, regex2, regex3, regex4, regex5, regex6, regex7]
    for regex in regexs:
        record_codes = re.compile(regex).findall(text)
        if record_codes:
            return record_codes[-1]
    return ""

import shortuuid


def generate_reference() -> str:
    """
    Generate a reference with 3 letters and 4 digits
    :return: str
    """
    valid_chars = "BCDFGHJKLMNPQRSTVWXYZ"
    su = shortuuid.ShortUUID(alphabet="0123456789")
    uid = su.random(length=4 + 3*2)  # Representamos las letras con dos números
    reference = ""
    char_part = uid[4:]
    for i in range(0, len(char_part), 2):
        char_code = uid[i:i+4]
        char_index = int(char_code) % len(valid_chars)
        reference += valid_chars[char_index]
    return reference + uid[:4]


def set_reference(model_class, reference_field) -> str or Exception:
    reference = generate_reference()
    max_tries = 20
    for loop in range(max_tries):
        if not model_class.objects.filter(**{reference_field: reference}).exists():
            return reference
        reference = generate_reference()
    raise Exception("Can not generate a valid reference, max number of tries excedeed")


def generate_next_reference(record_reference) -> str and int:
    """
    Generate a reference for a claim.
    The structures must be: normalized_record_id - Number.
    Examples:

    :param record_reference: Reference of the claimed record
    :return: Reference of a claim and number of records
    """
    if "-" not in record_reference:
        new_claim_number = 2
        normalized_record_id = record_reference
    else:
        normalized_record_id, current_claim = record_reference.split("-")
        new_claim_number = int(current_claim) + 1
    if new_claim_number < 10:
        new_claim_number = "0{}".format(new_claim_number)

    return "{}-{}".format(normalized_record_id, new_claim_number), int(new_claim_number)

ORD_ABBRV = {
    1: 'r',
    2: 'n',
    3: 'r',
    4: 't',
}


def cat_ordinal(number):
    """
    Represents a number as an ordinal in Catalan language.
    This kind of function is very language specific, so packages as django humanize don't provide an localized
    implementation.
    :return: Ordinal string for the number in Catalan.
    """
    abbrv = ORD_ABBRV.get(number, 'è')
    return f'{number}{abbrv}'

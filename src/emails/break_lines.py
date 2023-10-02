def break_text_lines(line_length, text):
    lines = text.split("\n")
    final_text = ""

    for line in lines:

        if len(line) > line_length:
            line_to_add = break_lines_by_points(line_length, line)
        else:
            line_to_add = f"{line}\n" if line else ""

        if line_to_add:
            final_text += line_to_add

    return final_text


def break_lines_by_points(line_length, text):

    lines = text.split(".")
    final_text = ""

    for line in lines:

        if len(line) > line_length:
            line_to_add = f"{break_lines_by_words(line_length, line)[:-1]}.\n"
        else:
            line_to_add = f"{line}.\n" if line else ""

        if line_to_add:
            final_text += line_to_add

    return final_text


def break_lines_by_words(line_length, text):

    words = text.split(" ")
    final_text = ""

    for word in words:

        if len(word) > line_length:
            word_to_add = break_words(line_length, word)
        else:
            word_to_add = f"{word}\n" if word else ""

        if word_to_add:
            final_text += word_to_add

    return final_text


def break_words(line_length, text):
    final_text = ""
    for i in range(0, len(text), line_length):
        final_text += f"{text[i:i+line_length]}\n"
    return final_text

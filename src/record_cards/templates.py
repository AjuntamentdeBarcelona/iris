from iris_templates.renderer import Iris1TemplateRenderer


def render_record_response(record_card, response_text=None, renderer=None):
    """
    :param renderer: Reuse previous renderer
    :param record_card:
    :param response_text: Response text for previews, None for real render from record card
    :return: Record card response text with all the vars replaced.
    """
    text = response_text if response_text else record_card.recordcardtextresponse_set.first().response
    if not renderer:
        return Iris1TemplateRenderer(record_card).render(text)
    return renderer.render(text)

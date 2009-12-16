from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django import template

register = template.Library()

@register.simple_tag
def get_email_share_url_for(content_object):
    content_type = ContentType.objects.get_for_model(content_object)
    return reverse('email-share', args=[
            content_type.pk, content_object.pk])

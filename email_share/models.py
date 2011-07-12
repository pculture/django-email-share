from django.conf import settings
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.core.mail import EmailMultiAlternatives
from django.db import models
from django.template import Context, TemplateDoesNotExist
from django.template.loader import select_template
from django.utils.encoding import force_unicode

def select_template_for_content_type(template, content_type):
    return select_template([
            # model specific
            'email_share/%s/%s/%s' % (content_type.app_label,
                                      content_type.model,
                                      template),
            # app specific
            'email_share/%s/%s' % (content_type.app_label,
                                   template),
            # generic
            'email_share/%s' % (template,)])

class ShareEmail(models.Model):
    content_type=models.ForeignKey(ContentType)
    object_id=models.IntegerField()
    content_object=generic.GenericForeignKey()

    user = models.ForeignKey('auth.User', null=True)
    sender_email = models.EmailField('From', blank=True)
    recipient_email = models.EmailField('To')

    message = models.TextField(blank=True)

    ip_address = models.IPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @models.permalink
    def get_absolute_url(self):
        parts = (force_unicode(self.sender_email),
                 force_unicode(self.recipient_email),
                 force_unicode(self.message),
                 force_unicode(settings.SECRET_KEY))
        parts = tuple([part.encode('utf8') for part in parts])
        return ('email-share-sent', (self.pk, abs(hash(parts))))

    def send(self, extra_context=None):
        context = {
            'content_object': self.content_object,
            'user': self.user,
            'sender': self.sender_email,
            'recipient': self.recipient_email,
            'message': self.message,
            'share_email': self
            }
        if extra_context:
            context.update(extra_context)
        context = Context(context)

        subject_template = select_template_for_content_type('subject.txt',
                                                            self.content_type)
        subject = subject_template.render(context)
        subject = subject.replace('\n', ' ') # one line

        text_template = select_template_for_content_type('body.txt',
                                                         self.content_type)
        text_body = text_template.render(context)

        message = EmailMultiAlternatives(subject, text_body,
                                         to=[self.recipient_email],
                                         headers={
                'Reply-To': self.sender.email})

        try:
            html_template = select_template_for_content_type('body.html',
                                                             self.content_type)
        except TemplateDoesNotExist:
            # no HTML template, just move on
            pass
        else:
            html_body = html_template.render(context)
            message.attach_alternative(html_body, 'text/html')

        message.send()

import re

from django.forms.fields import email_re
from django.forms import CharField, ValidationError
from django.forms.models import ModelForm
from django.utils.translation import ugettext as _

from email_share.models import ShareEmail

email_separator_re = re.compile(r'[^\w\.\-\+@_]+')

class EmailListField(CharField):
    # based on code from http://www.djangosnippets.org/snippets/1958/
    def clean(self, value):
        super(EmailListField, self).clean(value)
        emails = email_separator_re.split(value)
        if not emails:
            raise ValidationError(_(u'Enter at least one e-mail address.'))
        for email in emails:
            if not email_re.match(email):
                raise ValidationError(
                    _('%s is not a valid e-mail address.') % email)
        return emails

class ShareEmailForm(ModelForm):

    class Meta:
        model = ShareEmail
        fields = ('sender_email', 'recipient_email', 'message')

    def __init__(self, *args, **kwargs):
        if 'content_object' in kwargs:
            self.content_object = kwargs.pop('content_object')
        else:
            self.content_object = None

        if 'request' in kwargs:
            self.request = kwargs.pop('request')
            if getattr(self.request, 'user') and \
                    self.request.user.is_authenticated():
                self.user = getattr(self.request, 'user')
            else:
                self.user = None
        else:
            self.request = self.user = None

        super(ModelForm, self).__init__(*args, **kwargs)


    def clean_sender_email(self):
        if self.user and self.user.email:
            # use the user's e-mail if it's present
            return self.user.email
        value = self.cleaned_data.get('sender_email')
        if not value:
            raise ValidationError('This field is required.')
        return value

    def save(self, *args, **kwargs):
        original_commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        share_email = super(ModelForm, self).save(*args, **kwargs)
        share_email.content_object = self.content_object
        if self.request:
            share_email.user = self.user
            share_email.ip_address = self.request.META.get('REMOTE_ADDR', '')
        if original_commit:
            share_email.save()
        return share_email

class ShareMultipleEmailForm(ShareEmailForm):

    recipient_email = EmailListField(label="To")

    def save(self, *args, **kwargs):
        shares = ShareMultipleEmail()
        for email in self.cleaned_data['recipient_email']:
            data = self.data.copy()
            data['recipient_email'] = email
            shares.append(ShareEmailForm(data,
                                         content_object=self.content_object,
                                         request=self.request).save(*args,
                                                                     **kwargs))
        return shares

class ShareMultipleEmail(list):
    def send(self, *args, **kwargs):
        for email in self:
            email.send(*args, **kwargs)

    def get_absolute_url(self):
        return self[0].get_absolute_url()

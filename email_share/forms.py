import re

try:
    from django.forms.fields import email_re # Django 1.1
except ImportError:
    from django.core.validators import email_re # Django 1.2+
from django import forms
from django.utils.translation import ugettext as _

from email_share.models import ShareEmail

email_separator_re = re.compile(r'[^\w\.\-\+@_]+')

class EmailListField(forms.CharField):
    # based on code from http://www.djangosnippets.org/snippets/1958/
    def clean(self, value):
        super(EmailListField, self).clean(value)
        emails = email_separator_re.split(value)
        if not emails:
            raise forms.ValidationError(
                _(u'Enter at least one e-mail address.'))
        for email in emails:
            if not email_re.match(email):
                raise forms.ValidationError(
                    _('%s is not a valid e-mail address.') % email)
        return emails

class ShareEmailForm(forms.ModelForm):

    class Meta:
        model = ShareEmail
        fields = ('sender_email', 'recipient_email', 'message')

    def __init__(self, *args, **kwargs):
        if 'content_object' in kwargs:
            self.content_object = kwargs.pop('content_object')
        else:
            self.content_object = None

        self.request = kwargs.pop('request', None)
        if self.request and \
                getattr(self.request, 'user') and \
                self.request.user.is_authenticated():
            self.user = getattr(self.request, 'user')
            if self.user.email:
                kwargs.setdefault('initial', {})
                kwargs['initial']['sender_email'] = self.user.email
        else:
            self.user = None

        super(forms.ModelForm, self).__init__(*args, **kwargs)

    def clean_sender_email(self):
        value = self.cleaned_data.get('sender_email')
        if not value:
            raise forms.ValidationError('This field is required.')
        return value

    def save(self, *args, **kwargs):
        original_commit = kwargs.get('commit', True)
        kwargs['commit'] = False
        share_email = super(forms.ModelForm, self).save(*args, **kwargs)
        share_email.content_object = self.content_object
        if self.request:
            share_email.user = self.user
            share_email.ip_address = self.request.META.get('REMOTE_ADDR', '')
        if original_commit:
            share_email.save()
        return share_email

class ShareMultipleEmailForm(ShareEmailForm):
    sender_email = forms.EmailField(label="From")
    recipient_email = EmailListField(label="To")
    message = forms.CharField(label="Message", widget=forms.Textarea)

    class Meta:
        model = ShareEmail
        # we'll do the validation ourselves
        exclude = ['sender_email', 'recipient_email', 'message', 'object_id',
                   'content_type', 'user', 'ip_address']

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

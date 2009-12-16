from django.forms import ValidationError
from django.forms.models import ModelForm

from email_share.models import ShareEmail

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

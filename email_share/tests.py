import os.path

from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from django.core import mail
from django.core.urlresolvers import reverse
from django.test import Client, TestCase

from email_share.forms import ShareEmailForm, ShareMultipleEmailForm
from email_share.models import ShareEmail

class ShareEmailTest(TestCase):

    urls = 'email_share.urls'

    def setUp(self):
        self.old_TEMPLATE_DIRS = settings.TEMPLATE_DIRS
        self.old_TEMPLATE_LOADERS = settings.TEMPLATE_LOADERS
        self.old_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS
        settings.TEMPLATE_DIRS = [
            os.path.join(os.path.dirname(__file__), 'test_templates')]
        settings.TEMPLATE_LOADERS = [
            'django.template.loaders.filesystem.load_template_source']
        settings.TEMPLATE_CONTEXT_PROCESSORS = []

    def tearDown(self):
        settings.TEMPLATE_DIRS = self.old_TEMPLATE_DIRS
        settings.TEMPLATE_LOADERS = self.old_TEMPLATE_LOADERS
        settings.TEMPLATE_CONTEXT_PROCESSORS = self.old_CONTEXT_PROCESSORS

    def test_send_email(self):
        """
        ShareEmail.send() should send a message.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use
        email = ShareEmail.objects.create(
            content_object=content_object,
            sender_email='sender@example.com',
            recipient_email='recipient@example.com',
            message='Message from the sender!'
            )
        email.send()

        self.assertEquals(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEquals(message.recipients(), ['recipient@example.com'])

    def test_form(self):
        """
        ShareEmailForm should create a ShareEmail object given the e-mail
        addresses and a message.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use
        form = ShareEmailForm({
                'sender_email': 'sender@example.com',
                'recipient_email': 'recipient@example.com',
                'message': 'Message from the sender!'
                }, content_object=content_object)

        self.assertTrue(form.is_valid())

        email = form.save()
        self.assertTrue(email.content_object, content_object)
        self.assertEquals(email.sender_email, 'sender@example.com')
        self.assertEquals(email.recipient_email, 'recipient@example.com')
        self.assertEquals(email.message, 'Message from the sender!')

    def test_multiple_form(self):
        """
        ShareMultipleEmailForm should accept multiple e-mails addresses.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use
        form = ShareMultipleEmailForm({
                'sender_email': 'sender@example.com',
                'recipient_email': """recipient@example.com
recipient2@example.com, recipient3@example.com""",
                'message': 'Message from the sender!'
                }, content_object=content_object)

        self.assertTrue(form.is_valid(), form.errors)

        emails = form.save()
        self.assertEquals(len(emails), 3)
        self.assertEquals([email.recipient_email for email in emails],
                          ['recipient@example.com', 'recipient2@example.com',
                           'recipient3@example.com'])
        for email in emails:
            self.assertTrue(email.content_object, content_object)
            self.assertEquals(email.sender_email, 'sender@example.com')
            self.assertEquals(email.message, 'Message from the sender!')

    def test_share_email_GET(self):
        """
        The share_email view should render the 'email_share/form.html' template
        and pass the form and the content_object to the template.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use
        c = Client()
        response = c.get(reverse('email-share',
                                  args=[
                    ContentType.objects.get_for_model(ContentType).pk,
                    content_object.pk]))
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name, 'email_share/form.html')
        self.assertTrue(isinstance(response.context['form'], ShareEmailForm))
        self.assertEquals(response.context['content_object'], content_object)

    def test_share_email_POST(self):
        """
        The share_email view should send an e-mail and redirect to the
        email-share-sent view when POSTed to.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use
        c = Client()
        response = c.post(reverse('email-share',
                                  args=[
                    ContentType.objects.get_for_model(ContentType).pk,
                    content_object.pk]),
                         {'sender_email': 'sender@example.com',
                          'recipient_email': 'recipient@example.com',
                          'message': 'Message from the sender!'})
        share_email = ShareEmail.objects.get()
        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'],
                          'http://testserver%s' % (
                share_email.get_absolute_url(),))

    def test_share_email_sent(self):
        """
        The sent view should render the 'email_share/sent.html' view and
        include the content_object and share_email in the template.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use

        email = ShareEmail.objects.create(
            content_object=content_object,
            sender_email='sender@example.com',
            recipient_email='recipient@example.com',
            message='Message from the sender!'
            )

        c = Client()
        response = c.get(email.get_absolute_url())
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.template.name, 'email_share/sent.html')
        self.assertEquals(response.context['content_object'], content_object)
        self.assertEquals(response.context['share_email'], email)

    def test_share_email_sent_bad_url(self):
        """
        The sent view should return a 404 if the hash for the sent email is
        wrong.
        """
        content_object = ContentType.objects.all()[0] # get a random object to
                                                      # use

        email = ShareEmail.objects.create(
            content_object=content_object,
            sender_email='sender@example.com',
            recipient_email='recipient@example.com',
            message='Message from the sender!'
            )

        c = Client()
        response = c.get(reverse('email-share-sent', args=[email.pk, 0]))
        self.assertEquals(response.status_code, 404)

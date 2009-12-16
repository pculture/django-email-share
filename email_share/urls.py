from django.conf.urls.defaults import *

urlpatterns = patterns(
    'email_share.views',
    (r'^(\d+)/(\d+)/$', 'share_email', {}, 'email-share'),
    (r'^sent/(\d+)/(\d+)/$', 'sent', {}, 'email-share-sent'))

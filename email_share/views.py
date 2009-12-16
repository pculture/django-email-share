from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template.context import RequestContext

from email_share.forms import ShareEmailForm
from email_share.models import ShareEmail

def share_email(request, content_type_pk, object_id, extra_context=None):
    content_type = get_object_or_404(ContentType, pk=content_type_pk)
    try:
        content_object = content_type.get_object_for_this_type(pk=object_id)
    except ObjectDoesNotExist:
        raise Http404

    if request.method == 'POST':
        form = ShareEmailForm(request.POST,
                              content_object=content_object,
                              request=request)
        if form.is_valid():
            share_email = form.save()
            share_email.send(extra_context=extra_context)
            return HttpResponseRedirect(share_email.get_absolute_url())
    else:
        form = ShareEmailForm(content_object=content_object,
                              request=request)

    return render_to_response('email_share/form.html',
                              {'form': form,
                               'content_object': content_object},
                              context_instance=RequestContext(request))

def sent(request, share_email_pk, share_email_hash):
    share_email = get_object_or_404(ShareEmail, pk=share_email_pk)
    if request.path != share_email.get_absolute_url():
        raise Http404

    return render_to_response('email_share/sent.html',
                              {'content_object': share_email.content_object,
                               'share_email': share_email},
                              context_instance=RequestContext(request))

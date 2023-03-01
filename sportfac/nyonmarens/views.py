from django.views.generic import FormView
from django.urls import reverse_lazy

from .forms import WhistleForm


class WhistleView(FormView):
    template_name = "nyonmarens/whistle.html"
    form_class = WhistleForm
    success_url = reverse_lazy("nyonmarens:whistle_thanks")

    def form_valid(self, form):
        form.send_mail()
        return super(WhistleView, self).form_valid(form)
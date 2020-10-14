# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views.register import SlotsView

urlpatterns = [
    url('', SlotsView.as_view())
]

# -*- coding: utf-8 -*-
from __future__ import absolute_import
from django.conf.urls import url

from .views.register import SlotsView, SuccessfulRegister

urlpatterns = [
    url('success$', SuccessfulRegister.as_view(), name='success'),
    url('$', SlotsView.as_view(), name='register'),

]

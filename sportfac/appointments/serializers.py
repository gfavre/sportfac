# -*- coding: utf-8 -*-
from django.utils.translation import ugettext as _

from phonenumber_field.modelfields import PhoneNumberField
from rest_framework import serializers

from .models import AppointmentSlot
from registrations.models import Child


class SlotSerializer(serializers.ModelSerializer):
    available_places = serializers.SerializerMethodField
    title = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = ('id', 'title', 'available_places', 'places', 'start', 'end', 'url', 'color')

    def get_available_places(self, obj):
        return obj.available_places

    def get_title(self, obj):
        if obj.title:
            return obj.title
        else:
            return _('%(available)s out of %(total)s available') % {'available': obj.available_places,
                                                                    'total': obj.places}

    def get_url(self, obj):
        return obj.api_register_url

    def get_color(self, obj):
        return obj.available_places > 0 and 'green' or 'gray'


class AppointmentSerializer(serializers.Serializer):
    children = serializers.PrimaryKeyRelatedField(many=True, queryset=Child.objects.all())
    email = serializers.EmailField()
    phone = serializers.CharField(validators=PhoneNumberField().validators)
    url = serializers.URLField(required=False)


class AdminAppointmentSlotSerializer(SlotSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = ('id', 'title', 'available_places', 'places', 'start', 'end', 'url', 'color')

    def get_url(self, obj):
        return obj.api_management_url
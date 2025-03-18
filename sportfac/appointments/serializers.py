from django.utils.translation import gettext as _

from phonenumber_field.modelfields import PhoneNumberField
from rest_framework import serializers

from backend.dynamic_preferences_registry import global_preferences_registry
from registrations.models import Child
from .models import AppointmentSlot, Rental


class SlotSerializer(serializers.ModelSerializer):
    available_places = serializers.SerializerMethodField
    title = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    color = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = ("id", "title", "available_places", "places", "start", "end", "url", "color")

    def get_available_places(self, obj):
        return obj.available_places

    def get_title(self, obj):
        return _("%(available)s out of %(total)s available") % {
            "available": obj.available_places,
            "total": obj.places,
        }

    def get_url(self, obj):
        return obj.api_register_url

    def get_color(self, obj):
        return obj.available_places > 0 and "green" or "gray"


class AppointmentSerializer(serializers.Serializer):
    children = serializers.PrimaryKeyRelatedField(many=True, queryset=Child.objects.all())
    email = serializers.EmailField()
    phone = serializers.CharField(validators=PhoneNumberField().validators)
    url = serializers.URLField(required=False)


class AdminAppointmentSlotSerializer(SlotSerializer):
    url = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentSlot
        fields = ("id", "title", "available_places", "places", "appointment_type", "start", "end", "url", "color")

    def get_url(self, obj):
        return obj.api_management_url


class RentalSerializer(serializers.ModelSerializer):
    pickup_appointment = serializers.SerializerMethodField()
    return_appointment = serializers.SerializerMethodField()

    class Meta:
        model = Rental
        fields = ["id", "child", "pickup_appointment", "return_appointment"]

    def get_pickup_appointment(self, obj):
        if obj.pickup_appointment and obj.pickup_appointment.slot:
            return obj.pickup_appointment.slot.id
        return None

    def get_return_appointment(self, obj):
        if obj.return_appointment and obj.return_appointment.slot:
            return obj.return_appointment.slot.id
        return None

    def create(self, validated_data):
        child = validated_data["child"]
        # Prevent duplicate rentals for the same child
        if "amount" not in validated_data:
            preferences = global_preferences_registry.manager()
            validated_data["amount"] = preferences["site__RENTAL_PRICE"]
        if Rental.objects.filter(child=child).exists():
            raise serializers.ValidationError("Rental already exists for this child.")
        return super().create(validated_data)


class RegisterChildrenSerializer(serializers.Serializer):
    children = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False, help_text="A list of child IDs to register."
    )
    slot = serializers.PrimaryKeyRelatedField(queryset=AppointmentSlot.objects.all())
    appointment_type = serializers.ChoiceField(
        choices=["pickup", "return"], required=False, help_text="Specify if the slot is for pickup or return."
    )

    def validate_children(self, value):
        user = self.context.get("request").user

        # Check that each child belongs to the authenticated user
        valid_child_ids = set(Child.objects.filter(family=user).values_list("id", flat=True))
        for child_id in value:
            if child_id not in valid_child_ids:
                raise serializers.ValidationError(f"Child ID {child_id} does not belong to the user.")
        return value

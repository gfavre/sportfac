from profiles.models import FamilyUser


for user in FamilyUser.objects.all():
    if user.is_kepchup_staff:
        continue
    user.soft_delete()

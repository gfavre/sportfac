from django.utils.translation import activate
from activities.models import Course


activate('fr')

print('\t'.join(['Activité', 'Cours', 'Lieu', 'Moniteur(s)', 'Téléphone(s)', 'Email(s)', 'Nombre d\'inscrits']))
for course in Course.objects.prefetch_related('instructors', 'participants').select_related('activity'):
    place = course.place
    place = place.replace('\r\n', '\n')
    place = place.replace('\n', ', ')

    print('\t'.join([course.activity.name,
                     '%s, %s' % (course.day_name, course.start_time.strftime("%H:%M")),
                     place,
                     '; '.join([unicode(s.full_name) for s in course.instructors.all()]),
                     ', '.join([unicode(s.best_phone) for s in course.instructors.all()]),
                     ', '.join([unicode(s.email) for s in course.instructors.all()]),
                     str(course.count_participants)

                     ]))

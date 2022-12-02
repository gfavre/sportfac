from __future__ import absolute_import
from django.utils.timezone import now


def closest_session(sessions_iterable):
    dates = sorted([(session, (session.date - now().date()).days) for session in sessions_iterable],
                   lambda x, y: cmp(x[1], y[1]))
    if not len(dates):
        return None
    dates_past = [session for (session, nb_days) in dates if nb_days <= 0]
    if len(dates_past):
        return dates_past[-1]
    dates_future = [session for (session, nb_days) in dates if nb_days > 0]
    return dates_future[0]

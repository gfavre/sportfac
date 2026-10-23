import hashlib
import json
from collections import Counter

from django.core import signing


SIGNING_SALT = "diplomas.send-confirmation"


def mail_counts(diplomas):
    counts = Counter(diploma.mail_status for diploma in diplomas)
    return {status: counts[status] for status in ("pending", "sending", "sent", "failed")}


def confirmation_token(batch, diplomas, supplements, user):
    payload = {
        "batch": str(batch.pk),
        "modified": str(batch.modified),
        "season": batch.season,
        "issued_on": str(batch.issued_on),
        "status": batch.status,
        "subject": batch.subject,
        "message": batch.message,
        "diplomas": [
            [
                str(d.pk),
                str(d.modified),
                d.mail_status,
                str(d.parent_id),
                d.parent.email,
                d.parent.is_active,
                d.first_name,
                d.last_name,
                d.activity,
                d.course_number,
                d.level,
                d.evaluation,
                d.place,
                d.instructors,
            ]
            for d in diplomas
        ],
        "supplements": [[s.pk, s.name, str(s.modified)] for s in supplements],
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return signing.dumps({"batch": str(batch.pk), "user": str(user.pk), "state": digest}, salt=SIGNING_SALT)


def confirmation_matches(token, current_token):
    try:
        previous = signing.loads(token, salt=SIGNING_SALT, max_age=3600)
        current = signing.loads(current_token, salt=SIGNING_SALT, max_age=3600)
    except (signing.BadSignature, TypeError):
        return False
    return previous == current

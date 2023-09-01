# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

from registrations.models import Bill


print("Facture\tMontant\tNom\tTéléphone\temail")
for bill in Bill.objects.filter(total__gt=0, status="waiting"):
    print(
        (
            "\t".join(
                [
                    bill.billing_identifier,
                    str(bill.total),
                    bill.family.full_name,
                    str(bill.family.best_phone.as_national),
                    bill.family.email,
                ]
            )
        )
    )

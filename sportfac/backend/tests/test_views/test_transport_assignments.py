from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.storage.fallback import FallbackStorage
from django.test import RequestFactory
from django.test import override_settings
from django.urls import reverse

from activities.tests.factories import ExtraNeedFactory
from backend.views.registration_views import GenerateBibsView
from backend.views.transport_assignment_views import TransportAssignmentView
from profiles.tests.factories import FamilyUserFactory
from registrations.models import ExtraInfo
from registrations.models import Registration
from registrations.models import Transport
from registrations.tests.factories import ExtraInfoFactory
from registrations.tests.factories import RegistrationFactory
from sportfac.utils import TenantTestCase

from .base import fake_registrations_open_middleware


@override_settings(KEPCHUP_EXPLICIT_SESSION_DATES=False)
class TransportAssignmentTests(TenantTestCase):
    def setUp(self):
        super().setUp()
        self.manager = FamilyUserFactory(is_manager=True)
        self.car = Transport.objects.create(name="Car 7")
        self.question = ExtraNeedFactory(question_label="Arrêt de transport", choices=["73 Chailly", "74 Clarens"])
        self.first = RegistrationFactory(transport=None, child__bib_number="301")
        ExtraInfoFactory(registration=self.first, key=self.question, value="73 Chailly")
        self.other = RegistrationFactory(transport=None)
        ExtraInfoFactory(registration=self.other, key=self.question, value="74 Clarens")

    def request(self, method="get", data=None, user=None, query=""):
        request = getattr(RequestFactory(), method)(
            "/backend/registrations/transport/assignments/" + query, data or {}
        )
        request.user = user if user is not None else self.manager
        request.session = {}
        request._messages = FallbackStorage(request)
        fake_registrations_open_middleware(request)
        return request

    def view(self, method="get", data=None, user=None, query="", car=None):
        kwargs = {"pk": car.pk} if car else {}
        return TransportAssignmentView.as_view()(self.request(method, data, user, query), **kwargs)

    def test_general_screen_filters_exact_stop_and_collapses_children(self):
        RegistrationFactory(child=self.first.child, transport=None)
        response = self.view(data={"question": self.question.pk, "stop": "73 Chailly"})
        self.assertContains(response, "73 Chailly", status_code=200)
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [self.first.child_id])
        self.assertContains(response, "Sélectionner tous les enfants filtrés")
        self.assertContains(response, "Tout désélectionner")
        self.assertContains(response, "La sélection inclut toutes les pages de résultats.")
        content = response.content.decode()
        self.assertLess(content.index('id="select-filtered"'), content.index('id="assignment-children"'))

    def test_missing_answers_conflicting_answers_and_canceled_answers(self):
        missing = RegistrationFactory(transport=None)
        second = RegistrationFactory(child=self.first.child)
        ExtraInfoFactory(registration=second, key=self.question, value="74 Clarens")
        canceled = RegistrationFactory(status="canceled")
        ExtraInfoFactory(registration=canceled, key=self.question, value="75 Annulé")
        response = self.view()
        self.assertContains(response, "Plusieurs réponses : à vérifier")
        self.assertNotContains(response, "75 Annulé")
        response = self.view(data={"stop": "__missing__"})
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [missing.child_id])

    def test_course_filter_combines_courses_and_exact_stop(self):
        ExtraInfoFactory(registration=self.other, key=self.question, value="73 Chailly")
        second = RegistrationFactory(child=self.first.child, transport=None)
        canceled = RegistrationFactory(status="canceled", transport=None)
        response = self.view(data={"course": [self.first.course_id], "stop": "73 Chailly"})
        self.assertContains(response, 'id="course-filter"', status_code=200)
        self.assertContains(response, 'id="course-filter-toggle"')
        self.assertContains(response, f'type="checkbox" value="{self.first.course_id}" checked')
        self.assertContains(response, 'class="transport-course-options"')
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [self.first.child_id])
        self.assertEqual(len(response.context_data["table_children"]), 2)
        self.assertNotIn(canceled.course_id, [course.pk for course in response.context_data["courses"]])
        row = response.context_data["children"][0]
        self.assertEqual(set(row["course_ids"]), {str(self.first.course_id), str(second.course_id)})
        response = self.view(data={"course": [self.first.course_id, self.other.course_id]})
        self.assertEqual(len(response.context_data["children"]), 2)
        response = self.view(data={"course": [canceled.course_id]})
        self.assertEqual(response.context_data["children"], [])

    def test_course_filter_rejects_other_children_and_assigns_all_active_registrations(self):
        second = RegistrationFactory(child=self.first.child, transport=None)
        query = f"?course={self.first.course_id}"
        response = self.view(
            "post", {"children": [self.first.child_id, self.other.child_id], "destination": self.car.pk}, query=query
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context_data["assignment_form"].errors)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.transport_id)
        response = self.view("post", {"children": [self.first.child_id], "destination": self.car.pk}, query=query)
        self.assertEqual(response.status_code, 302)
        for registration in (self.first, second):
            registration.refresh_from_db()
            self.assertEqual(registration.transport_id, self.car.pk)
        self.other.refresh_from_db()
        self.assertIsNone(self.other.transport_id)

    def test_bulk_assignment_updates_all_active_registrations_and_preserves_business_state(self):
        second = RegistrationFactory(child=self.first.child, transport=None)
        canceled = RegistrationFactory(child=self.first.child, transport=None, status="canceled")
        original_status = self.first.status
        original_paid = self.first.paid
        course = self.first.course
        original_count = course.nb_participants
        with patch.object(Registration, "save", side_effect=AssertionError("No billing or capacity side effects")):
            response = self.view(
                "post", {"children": [self.first.child_id, self.other.child_id], "destination": self.car.pk}
            )
        self.assertEqual(response.status_code, 302)
        for registration in (self.first, second, self.other):
            registration.refresh_from_db()
            self.assertEqual(registration.transport_id, self.car.pk)
        canceled.refresh_from_db()
        self.assertIsNone(canceled.transport_id)
        self.assertEqual(self.first.status, original_status)
        self.assertEqual(self.first.paid, original_paid)
        self.first.child.refresh_from_db()
        self.assertEqual(self.first.child.bib_number, "301")
        course.refresh_from_db()
        self.assertEqual(course.nb_participants, original_count)
        self.assertEqual(ExtraInfo.objects.get(registration=self.first, key=self.question).value, "73 Chailly")

    def test_selection_outside_filter_and_invalid_car_are_rejected_atomically(self):
        query = f"?question={self.question.pk}&stop=73%20Chailly"
        for payload, url in (
            ({"children": [self.first.child_id, self.other.child_id], "destination": self.car.pk}, query),
            ({"children": [self.first.child_id], "destination": "9999999"}, ""),
            ({"children": [], "destination": self.car.pk}, ""),
        ):
            response = self.view("post", payload, query=url)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context_data["assignment_form"].errors)
            self.first.refresh_from_db()
            self.assertIsNone(self.first.transport_id)

    def test_car_screen_defaults_to_members_and_can_add_candidates(self):
        self.first.transport = self.car
        self.first.save()
        response = self.view(car=self.car)
        self.assertContains(response, "Répartir les enfants", status_code=200)
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [self.first.child_id])
        self.assertEqual(response.context_data["assignment_form"].initial["destination"], self.car)
        response = self.view(
            "post", {"children": [self.other.child_id], "destination": self.car.pk}, car=self.car, query="?car=none"
        )
        self.assertEqual(response.status_code, 302)
        self.other.refresh_from_db()
        self.assertEqual(self.other.transport_id, self.car.pk)

    def test_car_stops_are_saved_and_offer_candidates_without_assigning(self):
        response = self.view(
            "post", {"action": "stops", "stop_question": self.question.pk, "stop_values": ["73 Chailly"]}, car=self.car
        )
        self.assertEqual(response.status_code, 302)
        self.car.refresh_from_db()
        self.assertEqual(self.car.stop_question, self.question)
        self.assertEqual(self.car.stop_values, ["73 Chailly"])
        self.first.refresh_from_db()
        self.assertIsNone(self.first.transport_id)
        response = self.view(car=self.car, data={"car": "all", "stop": "__served__"})
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [self.first.child_id])

    def test_invalid_stop_or_question_cannot_be_saved(self):
        for data in (
            {"action": "stops", "stop_question": self.question.pk, "stop_values": ["invented"]},
            {"action": "stops", "stop_question": ExtraNeedFactory().pk, "stop_values": ["73 Chailly"]},
        ):
            response = self.view("post", data, car=self.car)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context_data["stops_form"].errors)
            self.car.refresh_from_db()
            self.assertEqual(self.car.stop_values, [])

    def test_question_can_be_selected_without_relying_on_label(self):
        question = ExtraNeedFactory(question_label="Lieu de départ", choices=["Gare"])
        ExtraInfoFactory(registration=self.first, key=question, value="Gare")
        response = self.view(data={"question": question.pk, "stop": "Gare"})
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [self.first.child_id])

    def test_anonymous_parents_and_restricted_managers_cannot_read_or_assign(self):
        for user in (AnonymousUser(), FamilyUserFactory(), FamilyUserFactory(is_restricted_manager=True)):
            for method in ("get", "post"):
                for car in (None, self.car):
                    with self.subTest(user=user, method=method, car=car):
                        response = self.view(
                            method, {"children": [self.first.child_id], "destination": self.car.pk}, user=user, car=car
                        )
                        self.assertEqual(response.status_code, 302)
        self.first.refresh_from_db()
        self.assertIsNone(self.first.transport_id)

    def test_urls_and_bib_screen_link_to_dedicated_assignment(self):
        self.assertEqual(reverse("backend:transport-assignments"), "/backend/registrations/transport/assignments/")
        self.assertEqual(
            reverse("backend:transport-assign-children", args=[self.car.pk]),
            f"/backend/registrations/transport/{self.car.pk}/assignments/",
        )
        response = GenerateBibsView.as_view()(self.request())
        self.assertContains(response, reverse("backend:transport-assignments"), status_code=200)
        self.assertNotContains(response, 'id="assign-bib-transports"')

    def test_navigation_links_from_list_and_car_detail(self):
        from backend.views.registration_views import TransportDetailView
        from backend.views.registration_views import TransportListView

        response = TransportListView.as_view()(self.request())
        self.assertContains(response, reverse("backend:transport-assignments"), status_code=200)
        self.assertContains(response, reverse("backend:transport-assign-children", args=[self.car.pk]))
        response = TransportDetailView.as_view()(self.request(), pk=self.car.pk)
        self.assertContains(
            response, reverse("backend:transport-assign-children", args=[self.car.pk]), status_code=200
        )

    def test_invalid_destination_preserves_selected_children(self):
        response = self.view("post", {"children": [self.first.child_id], "destination": "9999999"})
        self.assertContains(response, f'data-child-id="{self.first.child_id}" data-selected="true"', status_code=200)

    def test_datatable_keeps_all_children_available_for_immediate_filter_changes(self):
        response = self.view(data={"question": self.question.pk, "stop": "73 Chailly"})
        self.assertEqual(
            {row["child"].pk for row in response.context_data["table_children"]},
            {
                self.first.child_id,
                self.other.child_id,
            },
        )
        self.assertEqual([row["child"].pk for row in response.context_data["children"]], [self.first.child_id])
        self.assertContains(response, 'id="assignment-children"', status_code=200)
        self.assertContains(response, "jquery.dataTables.min.js")
        self.assertNotContains(response, "Filtrer les enfants")
        self.assertNotContains(response, 'class="well"')
        self.assertContains(response, 'data-stops="[&quot;73 Chailly&quot;]"')

    def test_question_is_visible_before_table_and_assignment_follows_table(self):
        response = self.view()
        self.assertContains(response, "Question utilisée pour les arrêts", status_code=200)
        html = response.rendered_content
        self.assertLess(html.index('id="question-form"'), html.index('id="assignment-children"'))
        self.assertLess(html.index("</table>"), html.index('id="assignment-action-controls"'))
        self.assertNotContains(response, "Réglages des arrêts")

    def test_pending_filter_includes_incomplete_conflicting_and_prefixless_assignments(self):
        ready_car = Transport.objects.create(name="Prêt", bib_prefix=8)
        ready = RegistrationFactory(transport=ready_car)
        prefixless = RegistrationFactory(transport=self.car)
        conflict = RegistrationFactory(transport=ready_car)
        RegistrationFactory(child=conflict.child, transport=self.car)
        response = self.view(data={"car": "pending"})
        ids = {entry["child"].pk for entry in response.context_data["children"]}
        self.assertEqual(ids, {self.first.child_id, self.other.child_id, prefixless.child_id, conflict.child_id})
        self.assertNotIn(ready.child_id, ids)
        self.assertContains(response, "Configurer le préfixe de dossard", status_code=200)

    def test_child_link_scopes_the_table_and_assignment_to_the_exact_child(self):
        query = f"?child={self.first.child_id}&from=bibs"
        response = self.view(query=query)
        self.assertEqual(
            [entry["child"].pk for entry in response.context_data["table_children"]], [self.first.child_id]
        )
        self.assertContains(response, "Revenir aux dossards", status_code=200)
        response = self.view("post", {"children": [self.other.child_id], "destination": self.car.pk}, query=query)
        self.assertTrue(response.context_data["assignment_form"].errors)
        response = self.view("post", {"children": [self.first.child_id], "destination": self.car.pk}, query=query)
        self.assertEqual(response.status_code, 302)
        self.first.refresh_from_db()
        self.assertEqual(self.first.transport_id, self.car.pk)

    def test_car_offers_direct_access_to_unassigned_children_matching_its_stops(self):
        self.car.stop_question = self.question
        self.car.stop_values = ["73 Chailly"]
        self.car.save()
        response = self.view(car=self.car)
        self.assertContains(response, "Enfants à placer pour les arrêts de ce car", status_code=200)
        self.assertContains(response, "stop=__served__&amp;car=none")
        self.assertContains(response, "Inclure les enfants déjà affectés")

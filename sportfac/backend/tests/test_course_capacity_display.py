from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase

from django.template import Context
from django.template import Engine


class CourseCapacityDisplayTests(TestCase):
    def render_capacity(self, count, maximum, **kwargs):
        source = (Path(__file__).parents[1] / "templates/backend/course/detail.html").read_text()
        fragment = source.split('<p class="course-capacity-summary">', 1)[1].split(
            "{% if course.has_participants %}", 1
        )[0]
        template = Engine(libraries={"i18n": "django.templatetags.i18n"}).from_string("{% load i18n %}" + fragment)
        course = SimpleNamespace(
            count_participants=count,
            max_participants=maximum,
            min_participants=10,
            full=count >= maximum,
            minimal_participants_reached=count >= 10,
            **kwargs,
        )
        return template.render(Context({"course": course}, use_l10n=False))

    def test_closed_registrations_show_actual_occupancy(self):
        html = self.render_capacity(2, 16, allow_new_participants=False, percentage_full=100)
        self.assertIn("width: min(100%, 12%);", html)
        self.assertIn("2 inscrits sur 16", html)

    def test_full_course(self):
        self.assertIn("width: min(100%, 100%);", self.render_capacity(16, 16))

    def test_over_capacity_is_visually_capped(self):
        self.assertIn("width: min(100%, 125%);", self.render_capacity(20, 16))

    def test_zero_capacity(self):
        self.assertIn("width: min(100%, 0%);", self.render_capacity(0, 0))

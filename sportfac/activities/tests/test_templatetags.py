from __future__ import absolute_import
from datetime import datetime, timedelta

from django.test import TestCase, override_settings
from django.template import Template, Context, TemplateSyntaxError


class TemplateTagDurationTests(TestCase):
    
    def setUp(self):
        self.tpl = Template("{% load duration %}{{ delta | duration }}")
        self.tpl2 = Template("{% load duration %}{{ delta | duration:True }}")

    def render(self, value, tpl=None):
        if not tpl:
            tpl = self.tpl
        return tpl.render(Context({
            'delta': value,
        })) 

    def test_bad_value(self):
        """
        template filter expects timedelta object
        """
        self.assertEqual(self.render(False), '')
        self.assertEqual(self.render(''), 'n/a')
        self.assertEqual(self.render('somestring'), '')
        self.assertEqual(self.render(datetime.now()), '')
        self.assertNotEqual(len(self.render(timedelta(0))), 0)

    @override_settings(LANGUAGE_CODE='en-US', LANGUAGES=(('en', 'English'),))
    def test_duration(self):
        """
        test various durations
        """
        self.assertEqual(self.render(timedelta(seconds=0)), '0 minute')
        self.assertEqual(self.render(timedelta(seconds=30)), '0 minute')
        self.assertEqual(self.render(timedelta(seconds=60)), '1 minute')
        self.assertEqual(self.render(timedelta(seconds=3599)), '59 minutes')
        self.assertEqual(self.render(timedelta(seconds=3600)), '1 hour')
        self.assertEqual(self.render(timedelta(seconds=3660)), '1 hour, 1 minute')
        self.assertEqual(self.render(timedelta(seconds=7200)), '2 hours')
        self.assertEqual(self.render(timedelta(seconds=7320)), '2 hours, 2 minutes')
        self.assertEqual(self.render(timedelta(days=2, seconds=7320)), '2 days, 2 hours, 2 minutes')
        self.assertEqual(self.render(timedelta(days=1)), '1 day')

    @override_settings(LANGUAGE_CODE='en-US', LANGUAGES=(('en', 'English'),))
    def test_argument(self):
        """
        test when display of seconds is on.
        """
        self.assertEqual(self.render(timedelta(seconds=0), self.tpl2), '0 second')
        self.assertEqual(self.render(timedelta(seconds=30), self.tpl2), '30 seconds')
        self.assertEqual(self.render(timedelta(seconds=60), self.tpl2), '1 minute')
        self.assertEqual(self.render(timedelta(seconds=3599), self.tpl2), '59 minutes, 59 seconds')
        self.assertEqual(self.render(timedelta(seconds=3600), self.tpl2), '1 hour')
    

class TemplateTagSecondsTests(TestCase):
    
    def setUp(self):
        self.tpl = Template("{% load duration %}{{ delta | seconds }}")

    def render(self, value, tpl=None):
        if not tpl:
            tpl = self.tpl
        return tpl.render(Context({
            'delta': value,
        })) 

    def test_bad_value(self):
        """
        template filter expects timedelta object
        """
        self.assertEqual(self.render(False), '0')
        self.assertEqual(self.render(''), '0')
        self.assertEqual(self.render('somestring'), '0')
        self.assertEqual(self.render(datetime.now()), '0')

    def test_duration(self):
        """
        test various durations
        """
        self.assertEqual(self.render(timedelta(seconds=0)), '0')
        self.assertEqual(self.render(timedelta(seconds=30)), '30')
        self.assertEqual(self.render(timedelta(seconds=3600)), '3600')
        self.assertEqual(self.render(timedelta(days=4)), str(4*86400))
        self.assertEqual(self.render(timedelta(days=4, seconds=3600)), str(3600+ 4*86400))


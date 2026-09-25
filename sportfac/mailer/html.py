"""Common HTML handling for previews and delivery; plain messages stay untouched."""
import re
from html import unescape

import bleach
from bleach.css_sanitizer import CSSSanitizer
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


TAGS = frozenset(
    {
        "p",
        "br",
        "strong",
        "b",
        "em",
        "i",
        "u",
        "s",
        "a",
        "img",
        "div",
        "span",
        "ul",
        "ol",
        "li",
        "table",
        "thead",
        "tbody",
        "tfoot",
        "tr",
        "th",
        "td",
        "h1",
        "h2",
        "h3",
        "h4",
        "blockquote",
        "hr",
    }
)
ATTRIBUTES = {
    "*": ["style"],
    "a": ["href", "title"],
    "img": ["src", "alt", "width", "height"],
    "table": ["border", "cellpadding", "cellspacing", "width"],
    "td": ["colspan", "rowspan", "width"],
    "th": ["colspan", "rowspan", "scope", "width"],
}
CSS_PROPERTIES = [
    "color",
    "background-color",
    "font-size",
    "font-family",
    "font-weight",
    "font-style",
    "text-align",
    "text-decoration",
    "border",
    "border-collapse",
    "border-color",
    "border-width",
    "border-style",
    "padding",
    "width",
    "height",
    "vertical-align",
    "margin",
]


def clean_email_html(value):
    return bleach.clean(
        value,
        tags=TAGS,
        attributes=ATTRIBUTES,
        protocols=["http", "https", "mailto"],
        css_sanitizer=CSSSanitizer(allowed_css_properties=CSS_PROPERTIES),
        strip=True,
    )


def plain_email_body(value):
    value = re.sub(r"</(?:p|div|tr|h[1-6]|li)>|<br\s*/?>", "\n", value, flags=re.I)
    value = re.sub(r"</t[dh]>", " — ", value, flags=re.I)
    return unescape(strip_tags(value)).strip()


def clean_email_template(value):
    from uuid import uuid4

    tokens = {}

    def protect(match):
        token = "MAILTOKEN" + uuid4().hex
        tokens[token] = match.group(0)
        return token

    cleaned = clean_email_html(re.sub(r"{{.*?}}|{%.*?%}|{#.*?#}", protect, value, flags=re.S))
    for token, original in tokens.items():
        cleaned = cleaned.replace(token, original)
    return cleaned


def make_email(*, is_html=False, body, **kwargs):
    if not is_html:
        return EmailMultiAlternatives(body=body, **kwargs)
    html = clean_email_html(body)
    email = EmailMultiAlternatives(body=plain_email_body(html), **kwargs)
    email.attach_alternative(html, "text/html")
    return email


def template_is_html(name):
    from .models import GenericEmail

    return isinstance(name, str) and GenericEmail.objects.filter(body_template__name=name, is_html=True).exists()

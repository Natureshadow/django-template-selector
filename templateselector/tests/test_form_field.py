# -*- coding: utf-8 -*-
from __future__ import unicode_literals, absolute_import

from uuid import UUID

import pytest

from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured
from django.forms import Form, IntegerField
from django.test import override_settings
from django.utils.encoding import force_text
from templateselector.fields import TemplateChoiceField
from templateselector.widgets import TemplateSelector, AdminTemplateSelector


@pytest.yield_fixture
def modelcls():
    from templateselector.tests.models import MyModel
    yield MyModel

def test_field_warns_if_providing_coerce_callable():
    with pytest.raises(ImproperlyConfigured):
        TemplateChoiceField(coerce=int, match="^.*$")

def test_field_warns_if_providing_dumb_display_name():
    with pytest.raises(ImproperlyConfigured):
        TemplateChoiceField(display_name='goose', match="^.*$")


def test_field_warns_if_missing_caret_at_start():
    with pytest.raises(ImproperlyConfigured):
        TemplateChoiceField(match=".*$")


def test_field_warns_if_missing_dollar_at_end():
    with pytest.raises(ImproperlyConfigured):
        TemplateChoiceField(match="^.*")


def test_model_field_yields_correct_formfield(modelcls):
    x = modelcls()
    y = x._meta.get_field('f').formfield()
    assert isinstance(y, TemplateChoiceField)


def test_choices():
    x = TemplateChoiceField(match="^admin/[0-9]+.html$")
    assert set(x.choices) == {('admin/404.html', '404'), ('admin/500.html', '500')}


def test_choices_using_custom_setting_mapping():
    s = {
        'admin/404.html': 'Page Not Found',
        'admin/500.html': 'Server Error',
    }
    with override_settings(TEMPLATESELECTOR_DISPLAY_NAMES=s):
        x = TemplateChoiceField(match="^admin/[0-9]+.html$")
        assert set(x.choices) == set(s.items())


def test_choices_using_custom_namer():
    def namer(data):
        return str(UUID('F'*32))
    x = TemplateChoiceField(match="^admin/[0-9]+.html$", display_name=namer)
    assert set(x.choices) == {('admin/404.html', 'ffffffff-ffff-ffff-ffff-ffffffffffff'),
                              ('admin/500.html', 'ffffffff-ffff-ffff-ffff-ffffffffffff')}


@pytest.yield_fixture
def form_cls():
    class MyForm(Form):
        a = IntegerField()
        b = TemplateChoiceField(match="^admin/[0-9]+.html$")
    return MyForm


def test_form_usage_invalid(form_cls):
    f = form_cls(data={'a': '1', 'b': 'goose'})
    assert f.is_valid() is False
    assert f.errors == {'b': ['Select a valid choice. goose is not one of the available choices.']}

def test_form_usage_ok(form_cls):
    f = form_cls(data={'a': '1', 'b': 'admin/404.html'})
    assert f.is_valid() is True
    assert f.errors == {}


@pytest.mark.xfail
def test_form_usage_render(form_cls):
    f = form_cls(data={'a': '1', 'b': 'admin/404.html'})
    rendered = force_text(f)
    assert rendered == ''


def test_admin_default_formfield(rf, modelcls):
    modeladmin = admin.site._registry[modelcls]
    request = rf.get('/')
    form = modeladmin.get_form(request=request)()
    widget = form.fields['f'].widget
    assert isinstance(widget, TemplateSelector)
    assert isinstance(widget, AdminTemplateSelector)
# -*- coding: utf-8 -*-

from django import forms
from ios_notifications.models import Device


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device

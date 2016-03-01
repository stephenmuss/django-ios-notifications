# -*- coding: utf-8 -*-

from django import forms
from django.forms.widgets import PasswordInput

import OpenSSL
from .models import Device, APNService


class DeviceForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = '__all__'


class APNServiceForm(forms.ModelForm):
    class Meta:
        model = APNService
        fields = '__all__'

    START_CERT = '-----BEGIN CERTIFICATE-----'
    END_CERT = '-----END CERTIFICATE-----'
    START_KEY = '-----BEGIN RSA PRIVATE KEY-----'
    END_KEY = '-----END RSA PRIVATE KEY-----'
    START_ENCRYPTED_KEY = '-----BEGIN ENCRYPTED PRIVATE KEY-----'
    END_ENCRYPTED_KEY = '-----END ENCRYPTED PRIVATE KEY-----'

    passphrase = forms.CharField(widget=PasswordInput(render_value=True), required=False)

    def clean_certificate(self):
        if not self.START_CERT or not self.END_CERT in self.cleaned_data['certificate']:
            raise forms.ValidationError('Invalid certificate')
        return self.cleaned_data['certificate']

    def clean_private_key(self):
        has_start_phrase = self.START_KEY in self.cleaned_data['private_key'] \
            or self.START_ENCRYPTED_KEY in self.cleaned_data['private_key']
        has_end_phrase = self.END_KEY in self.cleaned_data['private_key'] \
            or self.END_ENCRYPTED_KEY in self.cleaned_data['private_key']
        if not has_start_phrase or not has_end_phrase:
            raise forms.ValidationError('Invalid private key')
        return self.cleaned_data['private_key']

    def clean_passphrase(self):
        passphrase = self.cleaned_data['passphrase']
        if passphrase is not None and len(passphrase) > 0:
            try:
                OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, self.cleaned_data['private_key'], str(passphrase))
            except OpenSSL.crypto.Error:
                raise forms.ValidationError('The passphrase for the private key appears to be invalid')
        return self.cleaned_data['passphrase']

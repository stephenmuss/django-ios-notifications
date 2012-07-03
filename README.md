django-ios-notifications
=================

Django iOS Notifications makes it easy to send push notifications to iOS devices.


Installation
-----------------

You can install with pip: `pip install git+git://github.com/stephenmuss/django-ios-notifications.git`.

You then need to add `ios_notifications` to `INSTALLED_APPS` in your settings file.

If you want to use the API for registering devices you will also need to make the appropriate changes to your urls file:

```python
    urlpatterns = patterns('',
        ...
        url(r'^ios-notifications/', include('ios_notifications.urls')),
        ...
    )
```

After that you will need to run `./manage.py syncdb` to create the database tables required for django-ios-notifications.


Setting up the APN Services
-----------------

Before you can add some devices and push notifications you'll need to set up an APN Service.
An example of how to do this in a development environment follows.

Start up your development server: `./manage.py runserver` and open up the following url in a web browser http://127.0.0.1:8000/admin/ios_notifications/apnservice/add/. You'll see a form to be able to create a new APN Service.

I am making the assumption that you have already created a private key and certificate. If not I suggest you follow one of the online guides to complete this step. One such example can be found at http://www.raywenderlich.com/3443/apple-push-notification-services-tutorial-part-12

The name of the service can be any arbitrary string.

The hostname will need to be a valid hostname for one of the Apple APN Service hosts. Currently this is `gateway.sandbox.push.apple.com` for sandbox testing and `gateway.push.apple.com` for production use.

For the certificate and private key fields paste in your certificate and key including the lines with:

`----BEGIN CERTIFICATE-----`,
`-----END CERTIFICATE-----`,
`-----BEGIN RSA PRIVATE KEY-----`
and `-----END RSA PRIVATE KEY-----`.

After this you are ready to save the APN Service.


Registering devices
-----------------

There are a few different ways you can register a device. You can either create the device in the admin interface at http://127.0.0.1:8000/admin/ios_notifications/device/add/ or use the API provided by django-ios-notifications to do so.

If you want to add the device through the admin interface you will need to know the device's token represented by 64 hexadecimal characters (be sure to exclude any `<`, `>` and whitespace characters).

Otherwise the django-ios-notifications API provides a REST interface for you to be able to add the device; this would normally be done by sending a request from you iOS app.

To register your device you will need to make a POST request from your device and pass the appropriate parameters as part of the URL.

The URL requires you to substitute in the device's 64 character hexadecimal token and the id of the APN Service to associate with this device.

For example if you wanted to register a device with the token `0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029` using an APN Service with the id 10 you would make a POST request to the following location:

http://127.0.0.1:8000/ios-notifications/register-device/0fd12510cfe6b0a4a89dc7369d96df956f991e66131dab63398734e8000d0029/10/

You do not need to pass any parameters as part of the request body.

The API will return you a response in JSON format to let you know whether your request was successful or not.


Creating and sending notifications
-----------------

As with devices, there are a few different ways you can create notifications.

You can create a notification in the admin interface by going to http://127.0.0.1:8000/admin/ios_notifications/notification/add/

If you create a notification and save it by hitting `Save and continue editing` you will notice that you
are now able to push this notification by clicking the `Push now` button which has appeared.
Clicking this button will send the notification to all active devices registered with the appropriate APN Server,
so make sure that you are really ready to send it before clicking the button.

Another options is to use the built in management command provided by django-ios-notifications.
You can do this by calling `./manage.py push_ios_notification` from the command line.
You will need to provide some arguments to the command in order to create and send a notification.

There are two required options and two optional ones.

The required arguments are `--message` and `--service`.

`--message` is a string containing the main message of your notification. e.g. `--message='This is a push notification from Django iOS Notifications!'`

`--service` is the id of the APN Service you wish to use. e.g. `--service=123`.

The optional arguments you may pass are `--badge` and `--sound`.

`--badge` is an integer value to represent the badge value that will appear over your app's springboard icon after receiving the notification.
e.g. `--badge=2`.

`--sound` is the sound to be played when the device receives your application. This can either be one of the built in sounds or one that you have
included in your app. e.g. `--sound=default`.

Note that if you do not provide the optional arguments the default values for both are `None`. This means the device will neither play a sound
or update the badge of your app's icon when receiving the notification.

A full example: `./manage.py push_ios_notification --message='This is a push notification from Django iOS Notifications!' --service=123 --badge=1 --sound=default`.

***

NOTE: This is a work in progress and is far from being production ready.
Use at your own risk.


This source code is released under a New BSD License. See the LICENSE file for full details.

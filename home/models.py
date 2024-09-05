from django.db import models

from wagtail.models import Page

from django.db import models
from datetime import timedelta
from decimal import Decimal
import uuid

from django.conf import settings

from django.contrib import admin
from django.utils import timezone
from django.contrib.auth import get_user_model

from modelcluster.fields import ParentalKey

def get_sentinel_user():
    return get_user_model().objects.get_or_create(username='deleted')[0]

class ContactMail(models.Model):
    name = models.CharField(max_length=255, blank=True)
    inquiry = models.CharField(max_length=255, blank=True)
    message = models.TextField(blank=True)
    email = models.CharField(max_length=255, blank=True)
    file = models.CharField(max_length=255, null=True, blank=True)
    url = models.CharField(max_length=255, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def clean_email(self):
        original_email = self.cleaned_data.get('email')

        if "@" not in original_email:
            raise ValidationError("Invalid Email address")

        if "." not in original_email:
            raise ValidationError("Invalid Email address")

        return original_email

    def save(self, *args, **kwargs):
        # onsave add create date or update edit date
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(ContactMail, self).save(*args, **kwargs)


class ContactMailAdmin(admin.ModelAdmin):
    list_display = ('name','email','url','create_date','edit_date')
    search_fields = ('name','email')
    list_filter = ('name',)
    display = 'Contact Form'


class PortfolioItem(models.Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    catagory = models.CharField(max_length=255, null=True, blank=True)
    url = models.CharField(max_length=255, null=True, blank=True)
    file = models.FileField(upload_to="uploads", blank=True, null=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # onsave add create date or update edit date
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(PortfolioItem, self).save(*args, **kwargs)


class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ('name','type','create_date','edit_date')
    search_fields = ('name','email')
    list_filter = ('name',)
    display = 'PortfolioItem'

class Portfolio(models.Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    catagory = models.CharField(max_length=255, null=True, blank=True)
    url = models.CharField(max_length=255, null=True, blank=True)
    image_logo = models.FileField(upload_to="uploads", blank=True, null=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # onsave add create date or update edit date
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(Portfolio, self).save(*args, **kwargs)


class PortfolioAdmin(admin.ModelAdmin):
    list_display = ('name','type','create_date','edit_date')
    search_fields = ('name','email')
    list_filter = ('name',)
    display = 'Portfolio'


class Artist(models.Model):
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(null=True, blank=True)
    portfolio = models.ForeignKey(Portfolio, models.SET_NULL, null=True, blank=True)
    type = models.CharField(max_length=255, null=True, blank=True)
    catagory = models.CharField(max_length=255, null=True, blank=True)
    url = models.CharField(max_length=255, null=True, blank=True)
    source = models.CharField(max_length=255, null=True, blank=True)
    create_date = models.DateTimeField(null=True, blank=True)
    edit_date = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        # onsave add create date or update edit date
        if self.create_date == None:
            self.create_date = timezone.now()
        self.edit_date = timezone.now()
        super(Artist, self).save(*args, **kwargs)


class ArtistAdmin(admin.ModelAdmin):
    list_display = ('name','type','create_date','edit_date')
    search_fields = ('name','email')
    list_filter = ('name',)
    display = 'Artist'


class HomePage(Page):
    pass

class AboutPage(Page):
    pass

class ArtistsPage(Page):
    pass

class SubmitPage(Page):
    pass

class ArtPge(Page):
    pass

class LivestreamPage(Page):
    pass

class LiveStreamUkrainePage(Page):
    pass



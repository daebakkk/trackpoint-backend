from django.contrib import admin
from .models import Asset, Assignment, Staff

admin.site.register(Staff)
admin.site.register(Asset)
admin.site.register(Assignment)

from django.contrib import admin
from invoicing.models import *


@admin.register(Account, Invoice, InvoiceItem, Units)
class InvoicingAdmin(admin.ModelAdmin):
    pass

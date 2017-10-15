import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from decimal import Decimal
import uuid
from django.utils import timezone
from invoicing import model_functions
from django.utils.translation import ugettext_lazy as _
from django.core.validators import DecimalValidator, MaxLengthValidator
import re

'''
Note:   foreignkey = OneToMany
'''

LOGO_DIR = 'logo'


def set_filename(instance, filename):
    return '{}/{}/{}-{}'.format(settings.MEDIA_ROOT,
                                LOGO_DIR,
                                instance.account_id, filename
                                )


class Account(models.Model):
    ACCOUNT_CONTACT_TITLE_CHOICES = (
        ('MR', 'Mr.'),
        ('MRS', 'Mrs.'),
        ('MS', 'Ms.'),
        ('DR', 'Dr.')
    )
    ACCOUNT_STATUS = (
        ('OPEN', 'Open'),
        ('SUSPENDED', 'Suspended'),
        ('ACCOUNT_OUTSTANDING', 'Outstanding'),
        ('CLOSED', 'Closed')
    )
    ACCOUNT_TYPE = (
        ('CLIENT_REGULAR', 'Client Account'),
        ('OWN_BUSINESS_PRIMARY', 'Business Profile (Primary)'),
        ('OWN_BUSINESS', 'Business Profile (Extra)')
    )

    ''' note: pass functions like uuid.uuid4 and datatime.utcnow WITHOUT parentheses, so func called on each
     new instance, than being called once when model imported and the value being used for every instance created'''
    date_added = models.DateTimeField(default=timezone.now, blank=False, null=True, verbose_name='Date added',
                                      editable=False)
    account_id = models.CharField(max_length=255, blank=False, null=True, unique=True, default=uuid.uuid4,
                                  verbose_name='Account ID')
    account_name = models.CharField(max_length=255, blank=False, null=True, verbose_name=_('Account name'))
    contact_title = models.CharField(max_length=3, blank=False, null=True, choices=ACCOUNT_CONTACT_TITLE_CHOICES,
                                     default=ACCOUNT_CONTACT_TITLE_CHOICES[0][0], verbose_name=_('Contact title'))
    contact_surname = models.CharField(max_length=255, blank=False, null=True, verbose_name=_('Contact surname'))
    contact_first_name = models.CharField(max_length=255, blank=False, null=True, verbose_name=_('Contact first name'))
    contact_email = models.EmailField(blank=False, null=True, verbose_name=_('Contact email'))
    contact_phone = models.CharField(max_length=21, blank=True, null=True, verbose_name=_('Phone'))
    company_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Company name'))
    company_website = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Company website'))
    addr_number = models.CharField(max_length=11, blank=True, null=True, verbose_name=_('Building #'))
    addr_name = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Building name'))
    addr_street = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Street'))
    addr_locality = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Locality'))
    addr_town = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('Town'))
    addr_county = models.CharField(max_length=255, blank=True, null=True, verbose_name=_('County/State'))
    addr_postcode = models.CharField(max_length=8, blank=True, null=True, verbose_name=_('Postcode/zip'))
    account_status = models.CharField(max_length=21, blank=False, null=True, default=ACCOUNT_STATUS[0][0],
                                      choices=ACCOUNT_STATUS, verbose_name=_('Account status'))
    account_type = models.CharField(max_length=21, blank=False, null=True, default=ACCOUNT_TYPE[0][0],
                                    choices=ACCOUNT_TYPE, verbose_name=_('Account type'))
    logo = models.ImageField(upload_to=set_filename,
                             null=False, blank=True,
                             verbose_name=_('Business Logo'))
    email_notifications = models.BooleanField(blank=False, null=False, default=False,
                                              verbose_name='Email notifications')

    def __str__(self):
        return self.account_name

    def ensure_blank_validator(self):
        """
        This validator is to ensure nobody messes with an account_id. The field is not disabled, as a value is
        required to be returned in order to grab the relevant object to update. Therefore, account_id is passed as
        a hidden field through to the form. It should not be updated, therefore, but if it is, then ensure it is
        return to None before saving.
        """
        for f in ['account_id']:
            if hasattr(self, f):
                delattr(self, f)  # remove any posted account_id

    def logo_validator(self):
        """
        This validator replaces any existing logo with a newly uploaded one. It removes the existing logo file
        from the OS. It also appends the account_id to the filename.
        """
        try:
            existing_instance = Account.objects.get(account_id=getattr(self, 'account_id'))
            if existing_instance.logo and self.logo != existing_instance.logo:
                try:
                    # remove existing logo if exists
                    os.remove('{}'.format(existing_instance.logo.file.name))
                except FileNotFoundError:
                    pass
        except Account.DoesNotExist:
            pass  # new account, don't need to worry

    def full_clean(self, exclude=None, validate_unique=True):
        self.ensure_blank_validator()
        self.logo_validator()
        super(Account, self).full_clean(exclude=exclude, validate_unique=validate_unique)

    def save(self, *args, **kwargs):
        """
        Override save method to perform capitalization, etc.
        """
        # capitalize certain fields
        for f in ['contact_surname',
                  'contact_first_name',
                  'company_name',
                  'addr_name',
                  'addr_street',
                  'addr_locality',
                  'addr_town',
                  'addr_county']:
            value = getattr(self, f, False)
            if value:
                setattr(self, f, value.title())
        # uppercase postcode & account name
        for f in ['addr_postcode', 'account_name']:
            value = getattr(self, f, False)
            if value:
                setattr(self, f, value.upper())
        # remove protocol from website FQDN, if added
        if getattr(self, 'company_website', False):
            setattr(self, 'company_website', re.sub('http(s)?://', '', getattr(self, 'company_website')))
        super(Account, self).save(*args, **kwargs)


class InvoiceItem(models.Model):
    TAX_STATUS = (
        ('STANDARD', 'Standard rate'),
        ('REDUCED', 'Reduced rate'),
        ('ZERO', 'Zero rated')
    )
    # To change, create new item and 'retire' old one
    # (thus not effective existing invoices & preserving item history in the DB).
    datetime_created = models.DateTimeField(default=timezone.now, blank=False, null=True, verbose_name='Created')
    item_name = models.CharField(max_length=255, blank=False, null=True, verbose_name='Item')
    desc = models.CharField(max_length=255, blank=False, null=True, verbose_name='Description')
    price = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.00'), blank=False,
                                null=True, verbose_name='Price', validators=[
            DecimalValidator(6, 2)])
    tax_status = models.CharField(max_length=11, blank=False, null=False, default=TAX_STATUS[0][0],
                                  choices=TAX_STATUS, verbose_name='Tax status')
    retired = models.BooleanField(blank=False, null=False, default=False, verbose_name='Deactivate')

    def __str__(self):
        return self.item_name


class Units(models.Model):
    item = models.ForeignKey(InvoiceItem, on_delete=models.PROTECT)
    invoice = models.ForeignKey('Invoice', on_delete=models.CASCADE)  # model in quotes to prevent table not found error
    quantity = models.IntegerField(default=1, blank=False, null=False)

    class Meta:
        unique_together = ('item', 'invoice')


class Invoice(models.Model):
    INVOICE_STATUS = (
        ('DRAFT', 'DRAFT'),
        ('ISSUED', 'ISSUED'),
        ('SENT', 'SENT'),
        ('OVERDUE', 'OVERDUE'),
        ('PAID_PARTIALLY', 'PAID PARTIALLY'),
        ('PAID_IN_FULL', 'PAID IN FULL'),
        ('CANCELLED', 'CANCELLED')
    )

    DISCOUNT_RATE = tuple((n, n) for n in range(0, 101, 5))

    TAX = (
        ('STANDARD', 'Invoice taxed at standard rate'),
        ('REDUCED', 'Invoice taxed at reduced rate'),
        ('NONE', 'No tax added to this invoice')
    )

    MONTHS = {
        1: _('Jan'), 2: _('Feb'), 3: _('Mar'), 4: _('Apr'),
        5: _('May'), 6: _('Jun'), 7: _('Jul'), 8: _('Aug'),
        9: _('Sep'), 10: _('Oct'), 11: _('Nov'), 12: _('Dec')
    }

    RECURRING = (
        (0, _('No')),
        (1, _('Daily')),
        (2, _('Monthly')),
        (3, _('Annual')),
    )

    client = models.ForeignKey('Account', related_name='invoice', on_delete=models.PROTECT,
                               verbose_name=_('Client'))
    invoice_number = models.CharField(max_length=255, blank=False, null=False, unique=True,
                                      default=model_functions.generate_invoice_random_id,
                                      verbose_name=_('Invoice number'))
    related_ticket_references = models.CharField(max_length=255, blank=False, null=True, unique=False,
                                                 verbose_name=_('Related ticket references'))
    invoice_comments = models.TextField(blank=True, null=False, unique=False, verbose_name=_('Invoice comments'),
                                        validators=[MaxLengthValidator(2500)])
    datetime_created = models.DateTimeField(default=timezone.now, blank=False, null=True,
                                            verbose_name=_('Created'), editable=False)
    datetime_issued = models.DateTimeField(blank=True, null=True, verbose_name=_('Issued'))
    date_due = models.DateField(blank=False, null=False, default=timezone.now, verbose_name=_('Invoice due'))
    overdue = models.BooleanField(default=False, verbose_name='Overdue')
    invoice_items = models.ManyToManyField(InvoiceItem, through=Units, related_name='invoice',
                                           verbose_name=_('Items'))
    discount_rate = models.SmallIntegerField(blank=False, default=DISCOUNT_RATE[0][0], choices=DISCOUNT_RATE,
                                             verbose_name=_('Discount'))
    tax = models.CharField(blank=False, null=True, max_length=21, default=TAX[2][0], choices=TAX,
                           verbose_name=_('Tax status'))
    invoice_status = models.CharField(max_length=21, blank=False, null=True, default=INVOICE_STATUS[0][0],
                                      choices=INVOICE_STATUS, verbose_name=_('Invoice status'))
    marked_as_paid = models.DateTimeField(blank=True, null=True, verbose_name=_('Date marked as paid'))
    paid_amount = models.DecimalField(blank=False, null=False, default=0.00, max_digits=9, decimal_places=2,
                                      verbose_name=_('Amount paid'))
    issued_by = models.ForeignKey('Account', related_name='invoice_issued_by', on_delete=models.PROTECT,
                                  verbose_name=_('Issued by'), null=True, blank=False)
    pdf_invoice = models.FileField(upload_to=settings.INVOICING.get('PDF_DIR'), null=False,
                                   blank=True, verbose_name=_('Issued invoice PDF'))
    pdf_receipt = models.FileField(upload_to=settings.INVOICING.get('PDF_DIR'), null=False,
                                   blank=True, verbose_name=_('Issued receipt PDF'))
    invoice_emailed = models.BooleanField(default=False, verbose_name=_('Invoice email sent'))
    receipt_emailed = models.BooleanField(default=False, verbose_name=_('Receipt email sent'))
    recurring = models.SmallIntegerField(blank=False, null=True, default=RECURRING[0][0], choices=RECURRING,
                                         verbose_name=_('Recurring period'))
    parent_invoice = models.ForeignKey('Invoice', related_name='parent', on_delete=models.PROTECT,
                                       verbose_name=_('Parent invoice'), blank=True, null=True)

    def __str__(self):
        return self.invoice_number


def validate_invoice_item_name(value):
    """
    Do model validations. Note, should either return field IN_UNALTERED_STATE, or validation error.
    """
    error = ValidationError(_('You cannot assign the same name to two active items!'))
    try:
        InvoiceItem.objects.get(item_name=value, retired=False)
        raise error
    except InvoiceItem.DoesNotExist:
        pass

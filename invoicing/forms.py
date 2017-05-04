import io
from PIL import Image
from django.forms import ModelForm, BooleanField
from invoicing.models import *
from django.forms.widgets import *
from django.forms import CharField, Select
from django.utils.translation import ugettext_lazy as _
from django.forms import DateField, ModelMultipleChoiceField, ChoiceField, ModelChoiceField, DecimalField, IntegerField


class AccountForm(ModelForm):
    class Meta:
        model = Account
        fields = [
            'account_type',
            'account_name',
            'contact_title',
            'contact_surname',
            'contact_first_name',
            'contact_email',
            'contact_phone',
            'company_name',
            'company_website',
            'addr_number',
            'addr_name',
            'addr_street',
            'addr_locality',
            'addr_town',
            'addr_county',
            'addr_postcode',
            'email_notifications',
            'logo',
        ]

    def __init__(self, *args, **kwargs):
        super(AccountForm, self).__init__(*args, **kwargs)
        self.empty_permitted = False

        # # SET WIDGET ATTRIBUTES
        # default attributes
        default_attributes = {'class': 'form-control', 'size': '20'}
        self.fields['account_name'].widget = TextInput(attrs=default_attributes)
        self.fields['contact_surname'].widget = TextInput(attrs=default_attributes)
        self.fields['contact_first_name'].widget = TextInput(attrs=default_attributes)
        self.fields['contact_email'].widget = EmailInput(attrs=default_attributes)
        self.fields['contact_phone'].widget = TextInput(attrs=default_attributes)
        self.fields['company_name'].widget = TextInput(attrs=default_attributes)
        self.fields['company_website'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_number'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_name'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_street'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_locality'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_town'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_county'].widget = TextInput(attrs=default_attributes)
        self.fields['addr_postcode'].widget = TextInput(attrs=default_attributes)
        self.fields['logo'].widget = FileInput(attrs={'class': 'form-control'})
        self.fields['logo'].help_text = _('Uploading a new image will overwrite existing')
        self.fields['email_notifications'].widget = CheckboxInput(attrs={'class': 'form-control'})
        self.fields['email_notifications'].help_text = _(
            'Send invoice/receipt email (with PDFs) when invoice status changed?')
        # non-default attributes
        self.fields['contact_title'].widget = Select(attrs={'class': 'form-control'
                                                            },
                                                     choices=self.Meta.model.ACCOUNT_CONTACT_TITLE_CHOICES)
        self.fields['account_type'] = ChoiceField(choices=Account.ACCOUNT_TYPE,
                                                  widget=Select(attrs={'class': 'form-control'}))
        # extra form fields (not included model)
        self.fields['form_hidden_field_post_action'] = CharField(
            widget=HiddenInput())  # for view's routing of POST request
        self.fields['account_id'] = CharField(widget=HiddenInput())
        self.fields['account_id'].required = False

    def clean_logo(self):
        try:
            image = self.cleaned_data.get('logo', None)
            if image:
                # check it's not over 1MB
                if image.size > settings.INVOICING.get('LOGO_MAX_FILESIZE', 1024 * 1024):
                    raise ValidationError(_('Image too large - it is over 1MB!'))
                # resize the image dimensions
                max_size = settings.INVOICING.get('LOGO_SIZE', (75, 75))
                logo_file = io.BytesIO(image.read())
                logo = Image.open(logo_file)
                # w, h = logo.size
                # logo = logo.resize((round(w/2), round(h/2)), Image.ANTIALIAS)
                logo.thumbnail(max_size, Image.ANTIALIAS)
                logo_file = io.BytesIO()
                logo.save(logo_file, format='JPEG', quality=100)
                image.file = logo_file
            else:
                print('No image ...')
        except FileNotFoundError:
            raise ValidationError(_('The image does not exist'))
        return image


class InvoiceForm(ModelForm):
    class Meta:
        model = Invoice
        fields = ['date_due',
                  'invoice_items',
                  'discount_rate',
                  'tax',
                  'invoice_status',
                  'invoice_number',
                  'issued_by',
                  'invoice_emailed',
                  'receipt_emailed',
                  'paid_amount',
                  'recurring',
                  # note: don't add client here, as need to convert id to model instance in save method
                  ]

    class MyNumberInput(TextInput):
        input_type = 'number'

    def __init__(self, *args, **kwargs):
        super(InvoiceForm, self).__init__(*args, **kwargs)
        self.empty_permitted = False
        self.fields['date_due'] = DateField(widget=SelectDateWidget(empty_label=None,
                                                                    months=self.Meta.model.MONTHS,
                                                                    attrs={
                                                                        'class': 'form-control invoice_date_widget'}))
        self.fields['invoice_items'] = ModelMultipleChoiceField(queryset=InvoiceItem.objects.all())
        self.fields['issued_by'] = ModelChoiceField(queryset=Account.objects.all())
        self.fields['paid_amount'] = DecimalField(max_digits=9, decimal_places=2)
        # # SET WIDGET ATTRIBUTES
        self.fields['invoice_items'].widget = SelectMultiple(attrs={'class': 'form-control'})
        self.fields['invoice_items'].help_text = _('Select items, then quantities below')
        self.fields['paid_amount'].widget = self.MyNumberInput(attrs={'class': 'form-control', 'min': '0.00',
                                                                      'step': '0.01', 'disabled': True})
        self.fields['paid_amount'].help_text = _('Enter partial payment amount')
        self.fields['issued_by'].widget = Select(attrs={'class': 'form-control'})
        self.fields['issued_by'].help_text = _('Select a business to issue from')
        self.fields['discount_rate'].widget = Select(attrs={'class': 'form-control'},
                                                     choices=self.Meta.model.DISCOUNT_RATE)
        self.fields['tax'].widget = Select(attrs={'class': 'form-control'},
                                           choices=self.Meta.model.TAX)
        self.fields['invoice_status'].widget = Select(attrs={'class': 'form-control'},
                                                      choices=self.Meta.model.INVOICE_STATUS)
        self.fields['invoice_number'] = CharField(
            widget=HiddenInput())  # to pass ID to view when updating existing inst.
        self.fields['invoice_emailed'].widget = CheckboxInput(attrs={'class': 'form-control'})
        self.fields['receipt_emailed'].widget = CheckboxInput(attrs={'class': 'form-control'})
        self.fields['recurring'] = ChoiceField(choices=Invoice.RECURRING)
        self.fields['recurring'].widget = Select(attrs={'class': 'form-control'},
                                                 choices=Invoice.RECURRING)
        self.fields['recurring'].help_text = _('Is this to be a recurring invoice?')
        # # extra form fields (not included model)
        self.fields['form_hidden_field_post_action'] = CharField(
            widget=HiddenInput())  # for view's routing of POST request
        self.fields['client'] = CharField(widget=HiddenInput())  # to pass client if a new invoice
        # set required to False for all fields, to avoid validation issues when updating.
        for k, v in self.fields.items():
            self.fields[k].required = False


class InvoiceItemForm(ModelForm):
    class Meta:
        model = InvoiceItem
        fields = [
            'item_name',
            'desc',
            'price',
            'tax_status',
            'retired'
        ]

    def __init__(self, *args, **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)
        self.empty_permitted = False
        # # # SET WIDGET ATTRIBUTES
        self.fields['item_name'].widget = TextInput(attrs={'class': 'form-control'})
        self.fields['desc'].widget = Textarea(attrs={'class': 'form-control'})
        self.fields['price'].widget = TextInput(attrs={'class': 'form-control'})
        self.fields['tax_status'].widget = Select(attrs={'class': 'form-control'},
                                                  choices=self.Meta.model.TAX_STATUS)
        self.fields['retired'] = BooleanField()
        self.fields['retired'].widget = CheckboxInput(attrs={'class': 'form-control'})
        # # extra form fields (not included model (to avoid requirement, or prevent passing to model, etc))
        self.fields['form_hidden_field_post_action'] = CharField(
            widget=HiddenInput())  # for v's routing of POST request
        self.fields['invoice_item_id'] = CharField(widget=HiddenInput())
        # All fields unrequired by default (require in view as necessary) to allow disabling of fields when updating
        for k, v in self.fields.items():
            self.fields[k].required = False

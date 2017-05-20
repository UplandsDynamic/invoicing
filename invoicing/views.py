import smtplib
from django.db.models import Q
from django.shortcuts import render, redirect
from django.template import RequestContext
from django.template.loader import get_template
from django.test import RequestFactory
from weasyprint import HTML, CSS
from aninstance_framework import base, helpers, auth
from invoicing import forms
from invoicing.models import *
from django.conf import settings
from math import ceil
import decimal
from django.db import IntegrityError
from aninstance_framework.search_forms import RightSidebarSearchForm
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext as __
from collections import OrderedDict
from django.utils import timezone as utc
from django.http import HttpResponse
from django.core.mail import EmailMultiAlternatives
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.loader import render_to_string
import html2text

# PDF TYPES
PDF_TYPES = {
    'invoice': 'invoice',
    'invoice_update': 'invoice_update',
    'receipt': 'receipt'
}


# TODO Change loginrequired to only admin ...

class Invoicing(base.AninstanceGenericView):
    DEFAULT_SITE_FQDN = base.SITE_FQDN
    DEFAULT_SITE_PROTO = API_PROTO = 'https' if not settings.DEBUG else 'http'
    API_BASE_URL = '{}/api/invoicing'.format(base.SITE_FQDN)
    PARAM_STR_ACTION_NEW_ACCOUNT = 'new_account'
    PARAM_STR_ACTION_EDIT_ACCOUNT = 'edit_account'
    PARAM_STR_ACTION_VIEW_ACCOUNTS = 'view_accounts'
    PARAM_STR_ACTION_VIEW_BUSINESS_ACCOUNTS = 'view_business_accounts'
    PARAM_STR_ACTION_VIEW_SINGLE_ACCOUNT = 'view_account'
    PARAM_STR_ACTION_EDIT_BUSINESS_ACCOUNT = 'edit_business_account'
    PARAM_STR_POST_ACTION_EDIT_BUSINESS_ACCOUNT = 'update_business_account'
    PARAM_STR_POST_ACTION_NEW_BUSINESS_ACCOUNT = 'new_account'
    PARAM_STR_POST_ACTION_EDIT_ACCOUNT = 'update_account'
    PARAM_STR_ACTION_PDF_GEN = 'pdf_gen'
    PARAM_STR_ID_INVOICE_NUMBER = 'invoice_number'
    PARAM_STR_ID_ACCOUNT_NUMBER = 'profile_number'
    PARAM_STR_ID_INVOICE_ITEM_NUMBER = 'invoice_item_number'
    PARAM_STR_ID_ACCOUNT_ID = 'account_id'
    PARAM_STR_ACTION_VIEW_INVOICES = 'view_invoices'
    PARAM_STR_ACTION_VIEW_INVOICE = 'view_invoice'
    PARAM_STR_ACTION_NEW_INVOICE = 'new_invoice'
    PARAM_STR_ACTION_EDIT_INVOICE = 'edit_invoice'
    PARAM_STR_ACTION_NEW_INVOICE_ITEM = 'new_invoice_item'
    PARAM_STR_ACTION_VIEW_INVOICE_ITEMS = 'view_invoice_items'
    PARAM_STR_ACTION_VIEW_INVOICE_ITEM = 'view_invoice_item'
    PARAM_STR_ACTION_EDIT_INVOICE_ITEM = 'edit_invoice_item'
    PARAM_STR_ACTION_USAGE = 'usage'
    PARAM_STR_ACTION_EMAIL_PDF = 'email_pdf'
    PARAM_STR_ACTION_EMAIL_SUCCESS = 'email_success'
    PARAM_STR_ACTION_EMAIL_FAIL = 'email_fail'
    PARAM_STR_PDF_TYPE = 'pdf_type'
    POST_ACTION_FIELD = 'form_hidden_field_post_action'
    POST_ACCOUNT_ID_FIELD = 'account_id'  # added to pre-filled form as a hidden field when updating existing client
    POST_INVOICE_NUMBER_ID_FIELD = 'invoice_number'
    POST_INVOICE_ITEM_ID_FIELD = 'invoice_item_id'
    # OVERRIDES OF SUPERCLASS DEFAULTS (these also can be overridden yet again in this CBV's methods, later)
    TEMPLATE_NAME = 'invoicing/invoicing.html'
    FRAGMENT_KEY = 'invoicing'
    USE_CACHE = False
    PARAM_STR = 'action'
    RIGHT_SIDEBAR_SEARCH_PLACEHOLDER_TEXT = _('Who?')  # requires overriding of form_right_search in context
    RIGHT_SIDEBAR_SEARCH_BUTTON_TEXT = _('Find an account')
    PAGINATION_ITEMS_PER_PAGE = 5
    MODELS_TO_SEARCH = {'view_invoices': ['invoicing.invoice'],
                        'view_invoice': ['invoicing.invoice'],
                        'view_accounts': ['invoicing.account'],
                        'view_account': ['invoicing.account'],
                        'view_business_account': ['invoicing.account'],
                        'view_business_accounts': ['invoicing.account'],
                        'view_invoice_item': ['invoicing.invoiceitem'],
                        'view_invoice_items': ['invoicing.invoiceitem'],
                        }  # overwrite again in methods
    ITEMS_DASH_MENU = {'dropdown': [
        {'name': _('Dashboard'), 'action': 'dash'},
        {'name': _('View client accounts'), 'action': PARAM_STR_ACTION_VIEW_ACCOUNTS},
        {'name': _('Create new account'), 'action': PARAM_STR_ACTION_NEW_ACCOUNT},
        {'name': _('View invoice items'), 'action': PARAM_STR_ACTION_VIEW_INVOICE_ITEMS},
        {'name': _('View business profiles'), 'action': PARAM_STR_ACTION_VIEW_BUSINESS_ACCOUNTS},
        {'name': _('Docs: Usage instructions'), 'action': PARAM_STR_ACTION_USAGE},
    ],
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # define view specific contexts
        self.dash_button = 'Button'
        self.dash_action_button_1 = 'Action 1'
        self.dash_action_button_2 = 'Action 2'
        self.context.update({
            'heading_dash_menu': _('Menu'),
            'items_dash_menu': self.ITEMS_DASH_MENU,
            'dash_button': self.dash_button,
            'dash_action_button_1': self.dash_action_button_1,
            'dash_action_button_2': self.dash_action_button_2,
            'form_right_search': RightSidebarSearchForm(  # overridden to redefine placeholder
                placeholder=self.RIGHT_SIDEBAR_SEARCH_PLACEHOLDER_TEXT),
        })
        self.authentication_required = True if not settings.DEMO else False  # require authorization for this CBV
        self.auth_level = auth.USER_LEVEL.get('staff')

    def get(self, request):
        # call to super
        super().get(request)
        # clear any existing params so clean url passed back to for template URLs
        self.context.update({'param_str': '?{}='.format(self.PARAM_STR)})
        # get param value if any
        action = request.GET.get(self.PARAM_STR, None)
        # add any special contexts for actions (template snippets to include defined by ref to url param in template)
        if action == self.PARAM_STR_ACTION_NEW_ACCOUNT:  # new account
            return self.create_or_edit_account(request)
        elif action == self.PARAM_STR_ACTION_VIEW_ACCOUNTS or action == self.PARAM_STR_ACTION_VIEW_BUSINESS_ACCOUNTS:  # view accounts
            # SET UP SEARCH
            self.MODELS_TO_SEARCH = {
                'view_clients': ['invoicing.account'],
                'view_client': ['invoicing.account']
            }
            if 'q' in request.GET:
                return redirect(self.search_url)
            # return the account_view method
            return self.account_view(request)
        elif action == self.PARAM_STR_ACTION_VIEW_SINGLE_ACCOUNT:  # view single client
            # set up search
            self.MODELS_TO_SEARCH = {
                'view_clients': ['invoicing.account'],
                'view_client': ['invoicing.account']
            }
            if 'q' in request.GET:
                return redirect(self.search_url)
            # if requesting model id instead of account_id, get the account_id
            model_id = helpers.sanitize_url_param(request.GET.get('id'))
            account_id = helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_ACCOUNT_ID))
            if model_id:
                try:
                    account_id = Account.objects.get(id=model_id).account_id
                except Account.DoesNotExist:
                    account_id = None
            return self.account_view(request, account_id=account_id)
        elif action == self.PARAM_STR_ACTION_EDIT_ACCOUNT:  # edit client
            return self.create_or_edit_account(request, account_id=helpers.sanitize_url_param(
                request.GET.get(self.PARAM_STR_ID_ACCOUNT_ID)))
        elif action == self.PARAM_STR_ACTION_VIEW_INVOICE:  # view single invoice
            # set up search
            self.MODELS_TO_SEARCH = {
                'view_invoices': ['invoicing.invoice'],
                'view_invoice': ['invoicing.invoice'],
            }
            if 'q' in request.GET:
                return redirect(self.search_url)
            return self.invoice_view(request, inv_num=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_INVOICE_NUMBER)))
        elif action == self.PARAM_STR_ACTION_VIEW_INVOICES:  # view invoices
            # set up search
            self.MODELS_TO_SEARCH = {
                'view_invoices': ['invoicing.invoice'],
                'view_invoice': ['invoicing.invoice'],
            }
            if 'q' in request.GET:
                return redirect(self.search_url)
            # return the invoice_view method
            return self.invoice_view(request, client_account=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_ACCOUNT_ID
            )))
        elif action == self.PARAM_STR_ACTION_NEW_INVOICE:  # new invoice for client
            return self.new_invoice_view(request, client_account=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_ACCOUNT_ID)))
        elif action == self.PARAM_STR_ACTION_EDIT_INVOICE:  # edit invoice
            return self.new_invoice_view(request, inv_num=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_INVOICE_NUMBER)))
        elif action == self.PARAM_STR_ACTION_VIEW_INVOICE_ITEMS:  # view invoice items
            # set up search
            self.MODELS_TO_SEARCH = {
                'view_invoice_items': ['invoicing.invoiceitem']}
            if 'q' in request.GET:
                return redirect(self.search_url)
            return self.invoice_items_view(request)
        elif action == self.PARAM_STR_ACTION_VIEW_INVOICE_ITEM:  # view single invoice item
            # set up search
            self.MODELS_TO_SEARCH = {
                'view_invoice_item': ['invoicing.invoiceitem']}
            if 'q' in request.GET:
                return redirect(self.search_url)
            return self.invoice_items_view(request, single_item_id=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_INVOICE_ITEM_NUMBER)))
        elif action == self.PARAM_STR_ACTION_NEW_INVOICE_ITEM:  # new invoice item
            return self.new_invoice_item_view(request)
        elif action == self.PARAM_STR_ACTION_EDIT_INVOICE_ITEM:  # edit invoice item view
            return self.new_invoice_item_view(request, invoice_item=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_INVOICE_ITEM_NUMBER)))
        elif action == self.PARAM_STR_ACTION_PDF_GEN:  # generate PDF view
            return self.pdf_view(request, invoice_number=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_INVOICE_NUMBER)), pdf_type=PDF_TYPES[helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_PDF_TYPE))])
        elif action == self.PARAM_STR_ACTION_EMAIL_PDF:  # email invoice or receipt pdf
            # set up search
            self.MODELS_TO_SEARCH = {
                'view_invoices': ['invoicing.invoice'],
                'view_invoice': ['invoicing.invoice'],
            }
            if 'q' in request.GET:
                return redirect(self.search_url)
            return self.invoice_view(request, inv_num=helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_ID_INVOICE_NUMBER)), type=PDF_TYPES[helpers.sanitize_url_param(request.GET.get(
                self.PARAM_STR_PDF_TYPE))], email=True)
        elif action == self.PARAM_STR_ACTION_EDIT_BUSINESS_ACCOUNT:  # edit business profile
            return self.create_or_edit_account(request, account_id=helpers.sanitize_url_param(
                request.GET.get(self.PARAM_STR_ID_ACCOUNT_NUMBER)))
        elif action == self.PARAM_STR_ACTION_USAGE:  # usage instructions
            return self.app_docs_view(request)
        else:  # default dash
            return self.default_view(request)

    def post(self, request):
        # call to super
        super().get(request)
        # get action from param
        action = request.POST.get(self.POST_ACTION_FIELD, None)
        if action == self.PARAM_STR_ACTION_NEW_ACCOUNT:
            return self.post_new_account(request)
        elif action == self.PARAM_STR_POST_ACTION_EDIT_ACCOUNT:
            return self.post_edit_account(request)
        elif action == self.PARAM_STR_POST_ACTION_NEW_BUSINESS_ACCOUNT:
            return self.post_new_account(request)
        elif action == self.PARAM_STR_ACTION_NEW_INVOICE:
            return self.post_new_invoice(request)
        elif action == self.PARAM_STR_ACTION_EDIT_INVOICE:
            return self.post_edit_invoice(request)
        elif action == self.PARAM_STR_ACTION_NEW_INVOICE_ITEM:
            return self.post_new_invoice_item(request)
        elif action == self.PARAM_STR_ACTION_EDIT_INVOICE_ITEM:
            return self.post_edit_invoice_item(request)
        else:
            return self.post_default(request)

    """
    GET REQUEST HANDLERS
    """

    def default_view(self, request):
        self.context.update({'panel_heading': _('Invoicing'),
                             'dash_blurb': _('Please select a task from the menu above!'),
                             'dash_image': '{}/{}'.format(settings.STATIC_URL,
                                                          'images/aninstance_invoicing_wierd_logo.png'),
                             })
        return render(request, self.TEMPLATE_NAME, self.context)

    def app_docs_view(self, request):
        self.context.update({
            'panel_heading': _('Documents: Usage Instructions'),
            'dash_blurb': _('Usage instructions for Aninstance Invoicing'),
        })
        return render(request, self.TEMPLATE_NAME, self.context)

    def create_or_edit_account(self, request, account_id=None):
        """
        Note: A business profile is just another Client profile, but with "own_business" field set to "True".
        """
        if account_id:  # edit existing client account
            try:
                # set initial and get existing instance
                initial = {self.POST_ACTION_FIELD: self.PARAM_STR_POST_ACTION_EDIT_ACCOUNT,
                           self.POST_ACCOUNT_ID_FIELD: account_id}
                existing_instance = Account.objects.get(account_id=account_id)
                # create the form
                form = forms.AccountForm(instance=existing_instance,
                                         initial=initial)
                # remove primary business account option if already taken (unless edited account IS the primary)
                try:
                    Account.objects.get(~Q(account_id=account_id), account_type=Account.ACCOUNT_TYPE[1][0])
                    form.fields['account_type'].choices = (
                        (Account.ACCOUNT_TYPE[0][0], Account.ACCOUNT_TYPE[0][1]),
                        (Account.ACCOUNT_TYPE[2][0], Account.ACCOUNT_TYPE[2][1])
                    )
                except Account.DoesNotExist:
                    pass
                # get url for logo
                logo = '{}{}/{}'.format(settings.MEDIA_URL, LOGO_DIR,
                                        str(existing_instance.logo).split('/')[-1]) if existing_instance.logo else None
                self.context.update({
                    'account_form': form,
                    'panel_heading': _('Edit account'),
                    'logo': logo
                })
            except Account.DoesNotExist:
                self.context.update({
                    'account_form': None,
                    'error_message': _('Account does not exist!'),
                    'panel_heading': _('Edit account')
                })
        else:  # new account
            form = forms.AccountForm(
                initial={self.POST_ACTION_FIELD: self.PARAM_STR_ACTION_NEW_ACCOUNT,
                         'account_type': Account.ACCOUNT_TYPE[0][0]
                         })
            # remove primary business account option if already taken
            try:
                Account.objects.get(account_type=Account.ACCOUNT_TYPE[1][0])
                form.fields['account_type'].choices = (
                    (Account.ACCOUNT_TYPE[0][0], Account.ACCOUNT_TYPE[0][1]),
                    (Account.ACCOUNT_TYPE[2][0], Account.ACCOUNT_TYPE[2][1])
                )
                form.fields['account_id'].widget.attrs['disabled'] = True
            except Account.DoesNotExist:
                pass
            self.context.update({
                'account_form': form,
                'panel_heading': _('Create account')
            })
        return render(request, self.TEMPLATE_NAME, self.context)

    def account_view(self, request, account_id=None):
        self.context.update({'blurb': _('Tap on an account name to view more data')})
        if self.PARAM_STR in request.GET:  # single account
            if request.GET.get(self.PARAM_STR) == helpers.sanitize_url_param(
                    self.PARAM_STR_ACTION_VIEW_SINGLE_ACCOUNT):
                c = Account.objects.filter(account_id=account_id)
            elif request.GET.get(self.PARAM_STR) == helpers.sanitize_url_param(
                    self.PARAM_STR_ACTION_VIEW_BUSINESS_ACCOUNTS):  # if business accounts requested
                c = Account.objects.filter(account_type__in=[i[0] for i in Account.ACCOUNT_TYPE[1:]]).order_by(
                    'account_name')
            else:  # if client accounts requested
                c = Account.objects.filter(account_type=Account.ACCOUNT_TYPE[0][0]).order_by('account_name')
            # work out total pages
            total_pages = ceil(c.count() / self.PAGINATION_ITEMS_PER_PAGE)
            # slice the query as per page to get
            to_display_start = (self.PAGINATION_ITEMS_PER_PAGE * self.requested_page) \
                               - (self.PAGINATION_ITEMS_PER_PAGE - 1) if not account_id else ''
            to_display_end = to_display_start + self.PAGINATION_ITEMS_PER_PAGE if not account_id else ''
            c_slice = c[to_display_start - 1:to_display_end - 1] if not account_id else c[:]
            # format for display
            accounts = []
            if c_slice.exists():
                for account in c_slice.iterator():
                    # put invoice data in an ordered dict
                    account_data = OrderedDict()
                    for field in Account._meta.get_fields():
                        if not field.auto_created and not field.is_relation and not field.related_model:  # (Ref:footnote 1)
                            account_data.update({field.verbose_name: getattr(account, field.name)})
                            # for add account_id for template link as tpl won't get dict key with spaces without iterating
                            account_data.update({'account_id': getattr(account, 'account_id')})
                    # replace account type with human readable
                    account_data.update({'Account type':
                                             dict(Account.ACCOUNT_TYPE).get(getattr(account, 'account_type'))})
                    # add account to accounts list
                    accounts.append(account_data)
                self.context.update({
                    'panel_heading': _('View accounts') if not account_id else _('View account'),
                    'accounts': accounts,
                    'pagination': True,
                    'total_pages': range(1, total_pages + 1),
                    'blurb': _('Tap on an account name to view more data') if not account_id else
                    '{}{}'.format(_('Here is the requested record for '), c[0].account_name),
                    'right_sidebar_search': True,
                    'edit_account_blurb': _('Edit this account record'),
                    'edit_account_param_str': self.PARAM_STR_ACTION_EDIT_ACCOUNT,
                    'edit_account_id_param_str': self.PARAM_STR_ID_ACCOUNT_ID,
                    'view_invoices_param_str': self.PARAM_STR_ACTION_VIEW_INVOICES,
                    'view_invoices_blurb': _('View invoices for this account'),
                    'dash_button': _('New invoice for'),
                    'new_invoice_param_str': self.PARAM_STR_ACTION_NEW_INVOICE,
                })
            else:
                self.context.update({'no_results': _('There are no accounts to display!'),
                                     'panel_heading': _('View accounts')})
        else:
            self.context.update({'no_results': _('Stop messing about!'),
                                 'panel_heading': _('View accounts')})
        return render(request, self.TEMPLATE_NAME, self.context)

    def new_invoice_view(self, request, client_account=None, inv_num=None):
        """
        View to create or edit an invoice
        """
        error_message = _('The invoice you are looking for does not appear to exist!')
        try:
            client_record = Account.objects.get(account_id=client_account)
        except Account.DoesNotExist:
            client_record = None
        # CREATE NEW
        if client_record:
            try:
                form = forms.InvoiceForm(
                    initial={self.POST_ACTION_FIELD: self.PARAM_STR_ACTION_NEW_INVOICE,
                             'client': client_account,
                             'date_due': utc.now(),
                             'issued_by': Account.objects.filter(account_type=Account.ACCOUNT_TYPE[1][0])[0].pk})
                # only show non-retired invoice items for new invoices
                form.fields['invoice_items'].queryset = InvoiceItem.objects.filter(retired=False)
                # only show business account types for issued_by
                form.fields['issued_by'].queryset = Account.objects.filter(
                    account_type__in=[a[0] for a in Account.ACCOUNT_TYPE[1:]])
                form.fields['issued_by'].required = True
                form.fields['invoice_status'].choices = Invoice.INVOICE_STATUS[0:2]
                self.context.update({
                    'invoice_form': form,
                    'panel_heading': _('Add an invoice for {}'.format(client_record.account_name)),
                    'invoice_submit_button_text': _('Create invoice')
                })
            except IndexError as e:  # exception if no Account object of type OWN_BUSINESS_PRIMARY (no biz defined!)
                self.context.update({
                    'invoice_form': None,
                    'error_message': _('You do not appear to have defined your own business account yet!'),
                    'panel_heading': _('No business defined!')
                })
        elif inv_num:
            # EDIT
            self.context.update({'invoice_submit_button_text': _('Edit invoice')})
            try:
                _c = Invoice.objects.get(invoice_number=inv_num)
                # add extra fields
                initial = {self.POST_ACTION_FIELD: self.PARAM_STR_ACTION_EDIT_INVOICE,
                           self.POST_INVOICE_NUMBER_ID_FIELD: inv_num,
                           'client': _c.client.account_id,
                           'recurring': Invoice.RECURRING[_c.recurring][0] if _c.recurring else Invoice.RECURRING[0][0]
                           }
                # populate form with existing instance data
                form = forms.InvoiceForm(instance=_c, initial=initial)
                # populate issued_by with selected queryset
                form.fields['issued_by'].queryset = Account.objects.filter(
                    account_type__in=[a[0] for a in Account.ACCOUNT_TYPE[1:]])
                # make any changes to fields - e.g. disabling, changing available choices, etc
                form.fields['invoice_status'].help_text = _('Available options dependent on current status')
                form.fields['invoice_number'].widget.attrs['disabled'] = True
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[:1]]:  # if existing <= ISSUED
                    # only show non-retired invoice items if invoice not yet ISSUED
                    form.fields['invoice_items'].queryset = InvoiceItem.objects.filter(retired=False)
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[1:]]:  # if existing >= ISSUED
                    form.fields['date_due'].widget.attrs['disabled'] = True
                    form.fields['date_due'].help_text = _('Due date cannot be changed once invoice is issued')
                    form.fields['discount_rate'].widget.attrs['disabled'] = True
                    form.fields['discount_rate'].help_text = _('Discount cannot be changed once invoice is issued')
                    form.fields['invoice_items'].widget.attrs['disabled'] = True
                    form.fields['invoice_items'].help_text = _('Items cannot be changed once invoice is issued')
                    form.fields['issued_by'].widget.attrs['disabled'] = True
                    form.fields['issued_by'].help_text = _('Business cannot be selected once invoice is issued')
                    # for >= ISSUED, define field's queryset to only show items already chosen for this invoice
                    form.fields['invoice_items'].queryset = InvoiceItem.objects.filter(
                        id__in=[i.get('item_id') for i in Units.objects.filter(invoice=_c.id).values()])
                    form.fields['tax'].widget.attrs['disabled'] = True
                    form.fields['tax'].help_text = _('Tax status cannot be changed once invoice is issued')
                    form.fields['invoice_status'].choices = Invoice.INVOICE_STATUS[1:]
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[2:]]:  # if existing => SENT
                    form.fields['invoice_status'].choices = Invoice.INVOICE_STATUS[2:]
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[3:]]:  # if existing => OVERDUE
                    form.fields['invoice_status'].choices = Invoice.INVOICE_STATUS[3:6]
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[4:]]:  # if existing => PAID_PARTIALLY
                    form.fields['invoice_status'].choices = Invoice.INVOICE_STATUS[4:6]
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[5:]]:  # if existing => PAID_IN_FULL
                    form.fields['invoice_status'].widget.attrs['disabled'] = True
                    pass
                if _c.invoice_status in [s[0] for s in Invoice.INVOICE_STATUS[1:5]]:  # of existing <= PAID_PARTIALLY
                    form.fields['paid_amount'].widget.attrs['disabled'] = False
                self.context.update({
                    'invoice_form': form,
                    'panel_heading': _('Edit invoice record'),
                    'item_qty': [(c.item.id, c.quantity) for c in Units.objects.filter(
                        invoice__invoice_number=inv_num)],
                })
            except Invoice.DoesNotExist:
                self.context.update({
                    'invoice_form': None,
                    'error_message': _('The invoice you were looking for does not appear to exist!'),
                    'panel_heading': _('Edit invoice')
                })
        else:
            self.context.update({
                'invoice_form': None,
                'panel_heading': _('No invoice available'),
                'error_message': error_message
            })
        return render(request, self.TEMPLATE_NAME, self.context)

    def invoice_view(self, request, inv_num=None, client_account=None, type=None, email=None):
        """
        View to show the selected invoice (inv_num = invoice number)
        """
        # if arriving back at this view via request to email PDF (action=self.PARAM_STR_ACTION_EMAIL_PDF)
        if email:
            if pdf_gen_or_fetch_or_email(invoice_number=inv_num, type=type, email=True):
                self.context.update({'status_message': _('Email successfully transmitted')})
            elif pdf_gen_or_fetch_or_email(invoice_number=inv_num, type=type, email=True) == False:
                self.context.update({'error_message': _('Email transmission failed!')})
            else:
                self.context.update({'error_message': _('Email has already been sent!')})
        # create query
        i = None
        try:
            if client_account:
                i = Invoice.objects.filter(
                    client__account_id=client_account).order_by(
                    'datetime_issued')
            elif inv_num:
                i = Invoice.objects.filter(invoice_number=inv_num)
        except Invoice.DoesNotExist:
            pass
        if i:
            # work out total pages
            total_pages = ceil(i.count() / self.PAGINATION_ITEMS_PER_PAGE)
            # slice the query as per page to get
            if not inv_num:
                invoices_to_display_start = (self.PAGINATION_ITEMS_PER_PAGE * self.requested_page) \
                                            - (self.PAGINATION_ITEMS_PER_PAGE - 1)
                invoices_to_display_end = invoices_to_display_start + self.PAGINATION_ITEMS_PER_PAGE
                i_slice = i[invoices_to_display_start - 1:invoices_to_display_end - 1]
            else:
                i_slice = i
            # format for display
            invoices = []
            if i_slice:
                for invoice in i_slice:
                    # append invoice to invoices list
                    invoices.append(invoice_instance_to_dict(invoice))
            self.context.update({
                'panel_heading': _('View invoices') if not inv_num else _('View invoice'),
                'invoices': invoices,
                'invoice_status_choices': Invoice.INVOICE_STATUS,
                # to allow value to be reconciled to human readable name
                'pagination': True,
                'total_pages': range(1, total_pages + 1),
                'blurb': _('Below are listed all invoices for {}. Tap an invoice to view in full.'.format(
                    i[0].client.account_name)),
                'right_sidebar_search': True,
                'form_right_search': RightSidebarSearchForm(
                    placeholder=_('Search')),
                'right_sidebar_search_button_text': _('Find an invoice'),
                'edit_invoice_button': _('Edit this invoice'),
                'edit_inv_param_str': self.PARAM_STR_ACTION_EDIT_INVOICE,
                'gen_pdf_param_str': self.PARAM_STR_ACTION_PDF_GEN,
                'invoice_number_param_str': self.PARAM_STR_ID_INVOICE_NUMBER,
                'dash_button': _('Create invoice for client'),
                'client_id': i[0].client.account_id,
                'currency_symbol': settings.INVOICING.get('CURRENCY').get('SYMBOL'),
                'pdf_types': PDF_TYPES,
                'email_pdf_param_str': self.PARAM_STR_ACTION_EMAIL_PDF,
            })
        else:
            self.context.update({'no_results': _('There are no matching invoices available!'),
                                 'blurb': _('View client invoices'),
                                 'dash_button': _('Create invoice for this client'),
                                 'client_id': client_account,
                                 'panel_heading': _('No invoices to show!')
                                 })
        return render(request, self.TEMPLATE_NAME, self.context)

    def invoice_items_view(self, request, single_item_id=None):
        """
        View to show invoice items
        """
        # update up context
        self.context.update({'dash_button': _('Create new item')})
        # create query
        i = None
        try:
            if single_item_id:
                i = InvoiceItem.objects.filter(id=single_item_id)
            else:
                i = InvoiceItem.objects.all()
                # remove retired items from the fray
                i = i.filter(retired=False)
        except InvoiceItem.DoesNotExist:
            pass
        if i:
            # work out total pages
            total_pages = ceil(i.count() / self.PAGINATION_ITEMS_PER_PAGE)
            # slice the query as per page to get
            if not single_item_id:
                invoices_to_display_start = (self.PAGINATION_ITEMS_PER_PAGE * self.requested_page) \
                                            - (self.PAGINATION_ITEMS_PER_PAGE - 1)
                invoices_to_display_end = invoices_to_display_start + self.PAGINATION_ITEMS_PER_PAGE
                i_slice = i[invoices_to_display_start - 1:invoices_to_display_end - 1]
            else:
                i_slice = i
            # format for display
            if i_slice:
                invoice_items = []
                for item in i_slice:
                    item_data = OrderedDict()
                    special_fields = list()
                    for field in InvoiceItem._meta.get_fields():
                        if not field.auto_created:  # disallow, to avoid adding m2m autocreated fields to other tables
                            # special behaviours for fields
                            if field.name == 'DEFAULT_EXAMPLE':
                                special_fields.append(None)  # would append any specially processed field here
                            else:  # not processed as special field - just dumped as-is
                                item_data.update({field.verbose_name: getattr(item, field.name)})
                        if field.name == 'id':  # allow id field even though it is autocrated
                            special_fields.append({'id': getattr(item, field.name)})
                    try:
                        # add items at the end
                        item_data.update(*special_fields)
                    except UnboundLocalError as e:
                        # no items
                        pass
                    # append invoice to invoices list
                    invoice_items.append(item_data)
                self.context.update({
                    'panel_heading': _('View invoice items'),
                    'invoice_items': invoice_items,
                    # to allow value to be reconciled to human readable name
                    'pagination': True,
                    'total_pages': range(1, total_pages + 1),
                    'blurb': _('Below are listed all active invoice items (tap on item title to view more)')
                    if len(i_slice) > 1 else _('Below are selected invoice item(s)'),
                    'right_sidebar_search': True,
                    'form_right_search': RightSidebarSearchForm(
                        placeholder=_('Find item')),
                    'right_sidebar_search_button_text': _('Find an invoice item'),
                    'edit_invoice_item_blurb': _('Edit item'),
                    'edit_invoice_item_param_str': self.PARAM_STR_ACTION_EDIT_INVOICE_ITEM,
                    'edit_invoice_item_id_param_str': self.PARAM_STR_ID_INVOICE_ITEM_NUMBER,
                    'new_invoice_item_param_str': self.PARAM_STR_ACTION_NEW_INVOICE_ITEM,
                    'currency_symbol': settings.INVOICING.get('CURRENCY').get('SYMBOL'),
                })
        else:
            self.context.update({'no_results': _('There are no matching items available!'),
                                 'blurb': _('View invoice items')})
        return render(request, self.TEMPLATE_NAME, self.context)

    def new_invoice_item_view(self, request, invoice_item=None):
        """
        View to create or edit an invoice item
        """
        self.context.update({'invoice_item_button': _('Submit item')})
        error_message = _('The invoice item you are looking for does not appear to exist!')
        try:
            existing_item = InvoiceItem.objects.get(id=invoice_item)
        except InvoiceItem.DoesNotExist:
            existing_item = None
        # CREATE NEW
        if not existing_item:
            form = forms.InvoiceItemForm(
                initial={self.POST_ACTION_FIELD: self.PARAM_STR_ACTION_NEW_INVOICE_ITEM,
                         'tax_status': InvoiceItem.TAX_STATUS[0][0]})
            for f in form.fields.keys():
                form.fields[f].required = True
            form.fields['retired'].disabled = True
            form.fields['retired'].required = False
            self.context.update({
                'invoice_item_form': form,
                'panel_heading': _('Add an invoice item')
            })
        elif existing_item:
            # EDIT
            try:
                # add extra fields
                initial = {self.POST_ACTION_FIELD: self.PARAM_STR_ACTION_EDIT_INVOICE_ITEM,
                           self.POST_INVOICE_ITEM_ID_FIELD: invoice_item,
                           }
                # populate form with existing instance data
                form = forms.InvoiceItemForm(instance=existing_item, initial=initial)
                # grab units that have used this item (if any)
                units_used_in = Units.objects.filter(item=invoice_item)
                # make any changes to fields - e.g. disabling, changing available choices, etc
                for field in InvoiceItem._meta.get_fields():
                    if not field.auto_created:
                        if units_used_in.exists():
                            if field.name != 'retired' and field.name != 'datetime_created':
                                form.fields[field.name].help_text = _(
                                    '{} cannot be changed once item has been billed'.
                                        format(field.verbose_name))
                                form.fields[field.name].disabled = True
                self.context.update({
                    'invoice_item_form': form,
                    'panel_heading': _('Edit invoice item record'),
                    'panel_footer': _('Note: This item has been billed in {} invoices').format(
                        len(units_used_in) if units_used_in.exists() else 0)
                })
            except InvoiceItem.DoesNotExist:
                self.context.update({
                    'invoice_item_form': None,
                    'error_message': _('The invoice item you were looking for does not appear to exist!'),
                    'panel_heading': _('Edit invoice item')
                })
        return render(request, self.TEMPLATE_NAME, self.context)

    def pdf_view(self, request, invoice_number, pdf_type):
        # generate view response
        pdf_file = pdf_gen_or_fetch_or_email(invoice_number=invoice_number, type=pdf_type)
        if pdf_file:
            http_response = HttpResponse(pdf_file, content_type='application/pdf')
            http_response['Content-Disposition'] = 'inline; filename="Aninstance_{}_{}.pdf"'.format(PDF_TYPES[
                                                                                                        pdf_type],
                                                                                                    invoice_number)
            return http_response
        else:
            return HttpResponse(_('The requested invoice was not available!'),
                                content_type='text/html')

    """
    POST REQUEST HANDLERS
    """

    @staticmethod
    def post_default(request):  # if not a valid post request
        return redirect('invoicing')

    def post_new_account(self, request):
        form = forms.AccountForm(request.POST, request.FILES)
        if form.is_valid():
            # save manually because otherwise django fks it up, because, well, it's django.
            exclude = ['date_added', 'account_id']
            new = Account()
            for k, v in form.cleaned_data.items():
                if k not in exclude and k in forms.AccountForm.Meta.fields:
                    if v is not None and v is not '':
                        setattr(new, k, v)  # set the new value
            new.save()
            return redirect('{}?{}={}'.format(
                request.path,
                self.PARAM_STR,
                self.PARAM_STR_ACTION_VIEW_ACCOUNTS if form.cleaned_data.get(
                    'account_type') == Account.ACCOUNT_TYPE[0:1][0][0] else self.PARAM_STR_ACTION_VIEW_BUSINESS_ACCOUNTS
            ))
        else:
            self.context.update({
                'account_form': form,
            })
        return render(request, self.TEMPLATE_NAME, self.context)

    def post_edit_account(self, request):
        account_id = helpers.sanitize_post_data(request.POST.get('account_id', None))
        try:
            existing_record = Account.objects.get(account_id=account_id)
            form = forms.AccountForm(request.POST, request.FILES)
            if form.is_valid():
                exclude = ['date_added', 'account_id']
                for k, v in form.cleaned_data.items():
                    if k not in exclude and k in forms.AccountForm.Meta.fields:
                        if v is not None and v is not '':
                            setattr(existing_record, k, v)  # set the new value
                existing_record.save()
                self.context.update({'status_message': _('Account updated!'),
                                     'account_form': form,
                                     'panel_heading': _('Edit account')})
                return redirect('{}?{}={}&{}={}'.format(
                    request.path,
                    self.PARAM_STR,
                    self.PARAM_STR_ACTION_VIEW_SINGLE_ACCOUNT,
                    self.PARAM_STR_ID_ACCOUNT_ID,
                    account_id
                ))
            else:
                pass  # pass to error response
        except (IntegrityError, Account.DoesNotExist):
            pass  # pass to error response
        self.context.update({'error_message': _('An error occurred so the account was not updated!'),
                             'account_form': forms.AccountForm(request.POST, request.FILES)})
        return render(request, self.TEMPLATE_NAME, self.context)

    def post_new_invoice(self, request):
        self.context.update({'invoice_submit_button_text': _('New invoice')})
        invoice_form = forms.InvoiceForm(request.POST)
        if invoice_form.is_valid():
            # get the client object from the ID
            try:
                client = Account.objects.get(account_id=helpers.sanitize_url_param(
                    request.POST.get('client')))
                # grab the items and quantities from POST
                updated_item_qty = dict()
                for f in forms.InvoiceForm().fields['invoice_items'].choices:
                    try:
                        updated_item_qty[f[0]] = int(
                            helpers.sanitize_post_data(
                                request.POST.get('item_qty_field_{}'.format(f[0]))))
                    except TypeError:  # retired items would be None qty if not selected, hence fail int()
                        pass
            except Account.DoesNotExist:
                self.context.update({
                    'invoice_form': invoice_form,
                    'error_message': _('The assigned client does not appear to exist!')
                })
                return render(request, self.TEMPLATE_NAME, self.context)
            saved_instance = invoice_form.save(commit=False)
            # update the model instance with the client obj (obtained from the ID, above)
            saved_instance.client = client
            # save the time again manually, because django autosaves instance to utc.now for some obscure reason
            setattr(saved_instance, 'date_due', invoice_form.cleaned_data.get('date_due'))
            # SAVE THE MODEL
            saved_instance.save()
            # save the m2m (needs to be done manually, as using intermediary model)
            for item_id, qty in updated_item_qty.items():  # for every form item selected (i.e. has a val)
                if qty:
                    u = Units()  # get Unit obj (Unit is the intermediary model)
                    u.quantity = qty
                    u.item_id = item_id
                    u.invoice_id = saved_instance.id  # get the ID from the just saved invoice instance
                    u.save()  # save the thang!
            # if new invoice saved with status of ISSUED, generate an invoice PDF immediately!
            pdf_gen_or_fetch_or_email(invoice_number=saved_instance.invoice_number,
                                      email=False,
                                      regenerate=False,
                                      type=PDF_TYPES.get('invoice')
                                      )
            return redirect('{}?{}={}&{}={}'.format(
                request.path,
                self.PARAM_STR,
                self.PARAM_STR_ACTION_VIEW_INVOICES,
                self.PARAM_STR_ID_ACCOUNT_ID,
                client.account_id
            ))
        else:
            self.context.update({
                'invoice_form': forms.InvoiceForm(request.POST)
            })
            return render(request, self.TEMPLATE_NAME, self.context)

    def post_edit_invoice(self, request):
        invoice_number = helpers.sanitize_url_param(request.GET.get('invoice_number'))
        self.context.update({'invoice_submit_button_text': _('Edit invoice')})
        try:
            original_record = Invoice.objects.get(invoice_number=invoice_number)
            invoice_form = forms.InvoiceForm(request.POST)
            # populate issued_by
            if invoice_form.is_valid():
                try:
                    # grab the updated items and quantities from POST
                    updated_item_qty = dict()
                    for f in forms.InvoiceForm().fields['invoice_items'].choices:
                        try:
                            updated_item_qty[f[0]] = int(
                                helpers.sanitize_post_data(
                                    request.POST.get('item_qty_field_{}'.format(f[0]))))
                        except TypeError:  # retired items would be None qty if not selected, hence fail int()
                            pass
                    # get the client object from the ID
                    try:
                        client = Account.objects.get(account_id=helpers.sanitize_url_param(
                            request.POST.get('client')))
                    except Account.DoesNotExist:
                        self.context.update({
                            'invoice_form': invoice_form,
                            'error_message': _('The assigned client does not appear to exist!')
                        })
                        return render(request, self.TEMPLATE_NAME, self.context)
                    # manually save because auto saving mysteriously misses some fields due to django wierdness!
                    current = Invoice.objects.get(invoice_number=invoice_number)
                    for k, v in invoice_form.cleaned_data.items():  # iterate through included form fields
                        if k != 'client' and k != 'invoice_items' and k in forms.InvoiceForm.Meta.fields:
                            if v is not None and v is not '':
                                setattr(current, k, v)  # set the new value
                    current.client = client
                    # save the m2m (needs to be done separately, as using intermediary model)
                    units = Units.objects.filter(invoice__invoice_number=invoice_number)
                    for item_id, qty in updated_item_qty.items():  # for every form item selected (i.e. has a val)
                        try:  # if item in the form and in Units, edit values & save
                            if qty:
                                u = units.get(item_id=item_id)
                                u.quantity = qty
                                u.save()
                            else:
                                units.get(item_id=item_id).delete()  # delete any with 0 quantity
                        except Units.DoesNotExist:  # if item does not have a Unit, create and save
                            if qty:
                                u = Units()
                                u.quantity = qty
                                u.item_id = item_id
                                u.invoice_id = original_record.id
                                u.save()
                                # delete any existing Units for this invoice that aren't in the form
                    if invoice_form['invoice_status'].value() in Invoice.INVOICE_STATUS[:1][0]:
                        # note: only if status <= ISSUED, as if >= ISSUED field disabled so no invoice_items passed
                        units.filter(~Q(item_id__in=[i for i in updated_item_qty.keys()])).delete()
                        # actions taken if values on certain fields changed
                    # SAVE THE CHANGES TO THE INVOICE
                    try:
                        current.save()
                    except ValidationError as e:
                        self.context.update({'error_message': _(
                            'There was a problem updating the invoice: {}. '
                            '<a class="error_link" href="{}">Try again!</a>'.format(
                                e.message, '?action=edit_invoice&invoice_number={}'.format(invoice_number)
                            )),
                            'invoice_form': None})
                        return render(request, self.TEMPLATE_NAME, self.context)
                    # update pdf if necessary (also triggers auto email from signals, if client set to receive these)
                    if 'invoice_status' in invoice_form.changed_data or 'paid_amount' in invoice_form.changed_data:
                        pdf_gen_or_fetch_or_email(invoice_number=invoice_number,
                                                  regenerate=True,
                                                  type=PDF_TYPES['receipt'] if current.invoice_status ==
                                                                               Invoice.INVOICE_STATUS[5][
                                                                                   0] else
                                                  PDF_TYPES['invoice'])
                    # return the view
                    return redirect('{}?{}={}&{}={}&{}={}'.format(
                        request.path,
                        self.PARAM_STR,
                        self.PARAM_STR_ACTION_VIEW_INVOICE,
                        self.PARAM_STR_ID_INVOICE_NUMBER,
                        invoice_number,
                        self.PARAM_STR_ID_ACCOUNT_ID,
                        current.client.account_id
                    ))
                except IntegrityError as e:
                    self.context.update({'error_message': _('There was a problem updating the invoice!'),
                                         'invoice_form': None})
                    return render(request, self.TEMPLATE_NAME, self.context)
            else:
                self.context.update({
                    'invoice_form': None,
                    'error_message': _('The invoice could not be updated: {}'.format(
                        [v for k, v in forms.InvoiceForm(request.POST).errors.items()][0]))
                })
                return render(request, self.TEMPLATE_NAME, self.context)
        except Invoice.DoesNotExist:
            return redirect('invoicing')

    def post_new_invoice_item(self, request):
        self.context.update({'invoice_item_button': _('Submit item')})
        invoice_item_form = forms.InvoiceItemForm(request.POST)
        # do custom pre-clean validation for item_name
        try:
            validate_invoice_item_name(invoice_item_form.data['item_name'])
            # regular clean & validation
            if invoice_item_form.is_valid():
                # save manually
                new = InvoiceItem()
                for k, v in invoice_item_form.cleaned_data.items():
                    if k in forms.InvoiceItemForm.Meta.fields:
                        if v is not None and v is not '':
                            setattr(new, k, v)  # set the new value
                new.save()
                return redirect('{}?{}={}&{}={}'.format(
                    request.path,
                    self.PARAM_STR,
                    self.PARAM_STR_ACTION_VIEW_INVOICE_ITEM,
                    self.PARAM_STR_ID_INVOICE_ITEM_NUMBER,
                    new.id
                ))
            else:
                self.context.update({'error_message': _('There was a problem with submitting the form!')})
        except ValidationError as v:
            self.context.update({'error_message': '\n'.join(v)})
        self.context.update({'invoice_item_form': invoice_item_form})  # returned by default (i.e. if validation failed)
        return render(request, self.TEMPLATE_NAME, self.context)

    def post_edit_invoice_item(self, request):
        self.context.update({'invoice_item_button': _('Submit item')})
        invoice_item_id = helpers.sanitize_url_param(request.POST.get(
            self.POST_INVOICE_ITEM_ID_FIELD))
        try:
            existing_record = InvoiceItem.objects.get(id=invoice_item_id)
            invoice_item_form = forms.InvoiceItemForm(request.POST)
            if invoice_item_form.is_valid():
                try:
                    used_in_units = Units.objects.filter(item__id=invoice_item_id)
                    if invoice_item_form.cleaned_data['retired'] and not used_in_units.exists():
                        existing_record.delete()
                        return redirect('{}?{}={}'.format(
                            request.path,
                            self.PARAM_STR,
                            self.PARAM_STR_ACTION_VIEW_INVOICE_ITEMS
                        ))
                    else:
                        # save manually
                        for k, v in invoice_item_form.cleaned_data.items():
                            if k in forms.InvoiceItemForm.Meta.fields:
                                if v is not None and v is not '':
                                    setattr(existing_record, k, v)  # set the new value
                        existing_record.save()
                    return redirect('{}?{}={}&{}={}'.format(
                        request.path,
                        self.PARAM_STR,
                        self.PARAM_STR_ACTION_VIEW_INVOICE_ITEM,
                        self.PARAM_STR_ID_INVOICE_ITEM_NUMBER,
                        invoice_item_id
                    ))
                except IntegrityError as e:
                    self.context.update({'error_message': _('There was a problem updating the invoice item!'),
                                         'invoice_invoice_form': invoice_item_form})
                    return render(request, self.TEMPLATE_NAME, self.context)
            else:
                self.context.update({
                    'invoice_item_form': forms.InvoiceItemForm(request.POST),
                    'error_message': _('The invoice item could not be updated!')
                })
        except InvoiceItem.DoesNotExist:
            return redirect('invoicing')
        return render(request, self.TEMPLATE_NAME, self.context)

    """
    NON-STATIC HELPER METHODS
    """

    """
    STATIC HELPER FUNCTIONS
    """


def pdf_gen_or_fetch_or_email(invoice_number=None, type=None, email=None, regenerate=False):
    invoice = Invoice.objects.get(invoice_number=invoice_number)
    # generate fake request for Weasyprint (to enable calling of function outwith calling a view)
    factory = RequestFactory()
    url = '{}://{}/{}'.format(Invoicing.DEFAULT_SITE_PROTO,
                              Invoicing.DEFAULT_SITE_FQDN,
                              'invoicing?action={}'.format(
                                  Invoicing.PARAM_STR_ACTION_EMAIL_PDF))
    request = factory.get(url, SERVER_NAME=Invoicing.DEFAULT_SITE_FQDN)
    try:
        if email and (invoice.pdf_invoice or invoice.pdf_receipt):  # if called to email and invoice/receipt exists
            return _emailer(details={'invoice': invoice, 'type': type, 'request': request})
        if type == PDF_TYPES[
            'invoice'] and invoice.pdf_invoice and not regenerate:  # if called to view & saved invoice exists
            return invoice.pdf_invoice
        elif type == PDF_TYPES[
            'receipt'] and invoice.pdf_receipt and not regenerate:  # if called to view & saved receipt exists
            return invoice.pdf_receipt
        # if invoice or receipt not saved, or regenerate was True, generate
        invoice_instance_data_dict = invoice_instance_to_dict(invoice)
        invoice_data = dict()
        for k, v in invoice_instance_data_dict.items():
            if k == 'Items':
                items_list = list()
                for i in v:
                    items_list.append({'name': i.item.item_name,
                                       'desc': i.item.desc,
                                       'price': i.item.price,
                                       'tax_status': i.item.tax_status,
                                       'qty': i.quantity
                                       })
                invoice_data.update({'Items': items_list})
            else:
                invoice_data.update({k: v})
        # get url for logo
        try:
            proto = 'https' if request.is_secure() else 'http'
            business_logo = '{}://{}{}{}/{}'.format(proto, request.get_host(),
                                                    settings.MEDIA_URL, LOGO_DIR, str(getattr(
                    invoice_data.get('Issued by'), 'logo')).split('/')[-1])
        except AttributeError:
            business_logo = None
        # define context
        html_context = {'invoice_number': invoice_number,
                        'invoice_data': invoice_data,
                        'business_logo': business_logo,
                        'business_name_in_header': settings.INVOICING.get('BUSINESS_NAME_IN_PDF_HEADER'),
                        'currency_symbol': settings.INVOICING.get('CURRENCY').get('SYMBOL')
                        }
        html_template = get_template('invoicing/snippets/invoice_pdf.html')
        rendered_html = html_template.render(html_context).encode(
            encoding='UTF-8')
        pdf_file = HTML(string=rendered_html).write_pdf(
            stylesheets=[CSS(settings.STATIC_ROOT + '/css/invoice_pdf.css')])
        # save copy of pdf
        if type == PDF_TYPES['invoice']:  # save invoice
            filename = 'Aninstance_{}_#{}.pdf'.format(type, invoice_number)
            invoice.pdf_invoice = SimpleUploadedFile(filename,
                                                     pdf_file,
                                                     content_type='application/pdf')
        elif type == PDF_TYPES['receipt']:  # save receipt
            invoice.pdf_receipt = SimpleUploadedFile('Aninstance_{}_#{}.pdf'.format(type,
                                                                                    invoice_number),
                                                     pdf_file,
                                                     content_type='application/pdf')
        # add additional param to inform pre_save signal what this is
        invoice.save_pdf = True
        # save
        invoice.save()
        if email:  # if called to email, do that
            return _emailer(details={'invoice': invoice, 'type': type, 'request': request})
        return pdf_file  # if called to view, return the pdf file to the calling view
    except Invoice.DoesNotExist:
        return False


def _emailer(details=None):
    if details:
        # INVOICE
        if details.get('type') == PDF_TYPES['invoice'] or details.get('type') == PDF_TYPES['invoice_update']:
            # check to ensure email hasn't already been sent if invoice_update not the type & get instance
            try:
                if not PDF_TYPES['invoice_update']:  # if not update, look for instance with invoice_emailed = False
                    instance = Invoice.objects.get(invoice_number=details.get('invoice').invoice_number,
                                                   invoice_emailed=False)
                else:  # if update, don't worry about the emailed status - just grab the instance to email again
                    instance = Invoice.objects.get(invoice_number=details.get('invoice').invoice_number)
            except Invoice.DoesNotExist:  # returns None if already sent
                return None
            # rather than use a string, render the message from a template
            message_html = render_to_string('invoicing/snippets/invoice_email.html',
                                            {'client': details.get('invoice').client.company_name or
                                                       details.get('invoice').client.account_name,
                                             'invoice_number': details.get('invoice').invoice_number,
                                             'business': details.get('invoice').issued_by.company_name
                                             })
            # convert html to plaintext (markdown)
            message_plaintext = html2text.html2text(message_html)
            subject = __('{} invoice #{}'.format(details.get('invoice').issued_by.company_name,
                                                 details.get('invoice').invoice_number))
            if message_html and message_plaintext and subject:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=message_plaintext,
                    to=["{}<{}>".format(details.get('invoice').client.company_name or
                                        details.get('invoice').client.account_name,
                                        details.get('invoice').client.contact_email)],
                    reply_to=["{}<{}>".format(details.get('invoice').issued_by.company_name,
                                              details.get('invoice').issued_by.contact_email)],
                )
                msg.attach_file(details.get('invoice').pdf_invoice.path, mimetype='application/pdf')
                msg.attach_alternative(message_html, 'text/html')
                msg.track_clicks = True
                if settings.INVOICING.get('EMAIL_ACTIVE', False):  # if email activated
                    try:
                        msg.send()
                        # save sent status
                        instance.invoice_emailed = True
                        instance.save()
                        # return success page
                        return True
                    except smtplib.SMTPException as e:
                        pass  # email failed to send (defaults to returning False)
        # RECEIPT
        elif details.get('type') == PDF_TYPES['receipt']:
            # check to ensure email hasn't already been sent & get instance
            try:
                instance = Invoice.objects.get(invoice_number=details.get('invoice').invoice_number,
                                               receipt_emailed=False)  # returns if not sent
            except Invoice.DoesNotExist:  # email sent
                return None
            message_html = render_to_string('invoicing/snippets/receipt_email.html',
                                            {'client': details.get('invoice').client.company_name or
                                                       details.get('invoice').client.account_name,
                                             'invoice_number': details.get('invoice').invoice_number,
                                             'business': details.get('invoice').issued_by.company_name
                                             })
            # convert html to plaintext (markdown)
            message_plaintext = html2text.html2text(message_html)
            subject = __('{} receipt for invoice #{}'.format(details.get('invoice').issued_by.company_name,
                                                             details.get('invoice').invoice_number))
            if message_html and message_plaintext and subject:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=message_plaintext,
                    to=["{}<{}>".format(details.get('invoice').client.company_name or
                                        details.get('invoice').client.account_name,
                                        details.get('invoice').client.contact_email)],
                    reply_to=["{}<{}>".format(details.get('invoice').issued_by.company_name,
                                              details.get('invoice').issued_by.contact_email)],
                )
                msg.attach_file(details.get('invoice').pdf_receipt.path, mimetype='application/pdf')
                msg.attach_alternative(message_html, 'text/html')
                msg.track_clicks = True
                if settings.INVOICING.get('EMAIL_ACTIVE', False):  # if email activated
                    try:
                        msg.send(fail_silently=False)
                        # save sent status
                        instance.receipt_emailed = True
                        instance.save()
                        # return success page
                        return True
                    except smtplib.SMTPException as e:
                        pass  # email failed to send (defaults to returning False)
    # return failure page
    return False


def invoice_sums(invoice_data=None, invoice=None):
    """
    Method to do maths on the invoice. Returns invoice_data dict.
    """
    # get items from rest of the data
    items = invoice_data.get('Items')
    # set up decimal
    TWOPLACES = Decimal('0.01')

    # discount maths
    def apply_discount(subtotal, rate):
        return Decimal(subtotal - (subtotal * Decimal(rate / 100).quantize(TWOPLACES,
                                                                           rounding=decimal.ROUND_HALF_DOWN))).quantize(
            TWOPLACES, rounding=decimal.ROUND_HALF_DOWN)

    # tax maths
    def add_tax(subtotal, rate):
        # note: rate param is the item's tax rating. Invoice tax rating is invoice_data.get('Tax')
        if invoice_data.get('Tax status') == 'STANDARD':  # invoice not eligible for reduced; standard rate applied
            return Decimal(subtotal + (Decimal(subtotal * Decimal(
                settings.INVOICING.get('TAX').get('STANDARD') / 100).quantize(TWOPLACES,
                                                                              rounding=decimal.ROUND_HALF_DOWN))).quantize(
                TWOPLACES, rounding=decimal.ROUND_HALF_DOWN)).quantize(TWOPLACES, rounding=decimal.ROUND_HALF_DOWN)
        elif invoice_data.get(
                'Tax status') == 'REDUCED':  # + standard, reduced or zero rate, as per item's 'rate' (param)
            return Decimal(subtotal + (Decimal(subtotal * Decimal(
                settings.INVOICING.get('TAX').get(rate) / 100).quantize(TWOPLACES,
                                                                        rounding=decimal.ROUND_HALF_DOWN))).quantize(
                TWOPLACES, rounding=decimal.ROUND_HALF_DOWN)).quantize(TWOPLACES, rounding=decimal.ROUND_HALF_DOWN)
        elif invoice_data.get('Tax status') == 'NONE':  # don't + any tax
            return subtotal

    # get items data
    items_data = list()
    if items:
        for count, i in enumerate(items):  # for every item create a data dict
            items_data.append({'name': i.item.item_name,
                               'desc': i.item.desc,
                               'price': i.item.price,
                               'tax': i.item.tax_status,
                               'quantity': i.quantity,
                               })
            try:  # add results of maths to the data dict
                items_data[count].update({'item_total':
                                              Decimal(i.item.price * i.quantity).quantize(TWOPLACES,
                                                                                          rounding=decimal.ROUND_HALF_DOWN)})
                items_data[count].update(
                    {'item_total_less_discount': apply_discount(subtotal=items_data[count].get('item_total'),
                                                                rate=invoice_data.get(
                                                                    'Discount'),
                                                                )})
                items_data[count].update(
                    {'item_total_plus_tax': add_tax(subtotal=items_data[count].get('item_total_less_discount'),
                                                    rate=items_data[count].get('tax'),
                                                    )})
            except Exception as e:
                print('Error adding calc results to data dictionary: {}'.format(e))
        # items total
        items_total = Decimal(sum(i.get('item_total', 0) for i in items_data))
        invoice_data.update({_('Items total'): items_total})
        # after discount
        items_total_less_discount = Decimal(sum(i.get('item_total_less_discount', 0) for i in items_data))
        invoice_data.update({_('Total after discount'): items_total_less_discount})
        # after tax
        items_total_plus_tax = Decimal(sum(i.get('item_total_plus_tax', 0) for i in items_data))
        invoice_data.update({_('Total after tax'): items_total_plus_tax})
        # after total paid
        if invoice:
            try:
                invoice_data.update({_('Amount outstanding'): items_total_plus_tax - Decimal(invoice.paid_amount)})
            except AttributeError:
                pass
    # return
    return invoice_data


def invoice_instance_to_dict(invoice=None):
    # put invoice data in an ordered dict
    invoice_data = OrderedDict()
    special_fields = list()
    for field in Invoice._meta.get_fields():
        if not field.auto_created:  # allow field.is_relation and field.related_model here, for inv. items
            # special behaviours for fields
            if field.name == 'invoice_items':
                invoice_items = Units.objects.filter(invoice__invoice_number=invoice.invoice_number)
                if invoice_items.exists():
                    items = [item for item in invoice_items.iterator()]
                    special_fields.append({field.verbose_name: items})
            elif field.name == 'invoice_status':  # switch invoice.invoice_status with it's human-readable value
                invoice_data.update({'Invoice status': dict(Invoice.INVOICE_STATUS)[invoice.invoice_status]})
            # default behaviour
            else:  # not processed as special field - just dumped as-is
                invoice_data.update({field.verbose_name: getattr(invoice, field.name)})
    try:
        # add special behaviour items (defined above and not added yet) at the end of dict
        invoice_data.update(*special_fields)
        # sums
        invoice_data = invoice_sums(invoice_data, invoice)
    except UnboundLocalError as e:
        # no items assigned to this invoice
        pass
    return invoice_data


"""
Footnotes:
1. Only get what we need. See: https://docs.djangoproject.com/en/1.9/ref/models/meta/#migrating-from-the-old-api
"""

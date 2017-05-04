from django import template
from django.conf import settings
from django.utils.html import conditional_escape
from invoicing.models import Account, InvoiceItem, Invoice
from aninstance_framework import helpers
from invoicing.models import LOGO_DIR

register = template.Library()


# TAGS

@register.simple_tag()
def get_invoice_number(value, autoescape=True):
    # take the invoice item ordereddict and returns the 'Invoice number' field
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    return esc(value.get('Invoice number', None))


@register.simple_tag()
def format_utc_str_for_template(value, autoescape=True):
    # converts utc string to formatted string in client's tz
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    return esc('{}'.format(helpers.format_utc_str_for_template(
        value=value,
        autoescape=autoescape
    )))


@register.simple_tag()
def get_invoice_tax_status(value, autoescape=True):
    # grabs human-readable tax status
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    try:
        return esc(dict(Invoice.TAX)[value])
    except:
        return None


@register.simple_tag()
def get_item_tax_status(value, autoescape=True):
    # grabs human-readable tax status
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    try:
        return esc(dict(InvoiceItem.TAX_STATUS)[value])
    except:
        return None


# FILTERS

@register.filter(needs_autoescape=True)
def get_dict_value(value, param, autoescape=True):
    """
    This filter returns value of a dict, in the case that the dict key has spaces (unable to grab
    via template), and the dict value is a model instance.
    E.g. it would be equivalent to the following view code, where the dict values are model instances:

        result = getattr(data_data.get('my key'), 'my_attribute')

    The filter takes the following format in the template (based on above example):

        the_dict|get_dict_value:'my key, my_attribute'

    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    key_list = param.split(',')
    r = value
    try:
        for c, k in enumerate(key_list):
            r = r.get(k.strip()) if c < 1 else getattr(r, k.strip())
    except AttributeError as e:
        pass
    return r or ''  # do not escape as return value may be a list/dict


@register.filter(needs_autoescape=True)
def recurring_human_readable(value, autoescape=True):
    """
    This filter returns text for the recurring value, rather than the database int
    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    try:
        return esc(Invoice.RECURRING[int(esc(value))][1])
    except ValueError:
        return esc(Invoice.RECURRING[0][1])


@register.filter(needs_autoescape=True)
def get_img_url(value, autoescape=True):
    """
    This filter returns the public url for an image resource url
    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    return esc('{}{}/{}'.format(settings.MEDIA_URL, LOGO_DIR, str(value).split('/')[-1]))


@register.filter(needs_autoescape=True)
def client_account(value, autoescape=True):
    """
    This filter returns True if the passed account type is a 'client' account, False if not
    """
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x
    if value in [a[1] for a in Account.ACCOUNT_TYPE[0:1]]:
        return True
    return False

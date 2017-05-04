import random
from django.conf import settings


# function for generating new invoice IDS for invoicing.Invoice
def generate_invoice_random_id():
    r = random.randint(100, 999)
    return '{}-{}'.format(settings.INVOICING.get('DEFAULT_INVOICE_PREPEND', None), r)

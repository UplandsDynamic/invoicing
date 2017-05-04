from haystack import indexes
from invoicing.models import Account, Invoice, InvoiceItem
from django.utils import timezone as utc


class AccountIndex(indexes.SearchIndex, indexes.Indexable):
    """
    Always call primary (document=True) field "text".
    the 'text' field picks up the data defined in the TEMPLATE at:

    PROJECT_ROOT/templates/search/indexes/APP_NAME/APPNAME_text.txt

    Additional fields are added to allow separate filtering options on those fields.
    """
    text = indexes.CharField(document=True, use_template=True)
    # add other fields to be indexed separately from fields defined in template (to allow enhanced filtering options)
    date_added = indexes.DateTimeField(model_attr='date_added')

    def get_model(self):
        return Account

    def index_queryset(self, using=None):
        """Used when the entire index for model is updated."""
        return self.get_model().objects.filter(date_added__lte=utc.now())


class InvoiceIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return Invoice

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(datetime_issued__lte=utc.now())


class InvoiceItemIndex(indexes.SearchIndex, indexes.Indexable):
    text = indexes.CharField(document=True, use_template=True)

    def get_model(self):
        return InvoiceItem

    def index_queryset(self, using=None):
        return self.get_model().objects.filter(datetime_created__lte=utc.now())

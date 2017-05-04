from django.apps import AppConfig


class InvoicingConfig(AppConfig):
    name = 'invoicing'
    verbose_name = 'Aninstance Invoicing'

    def ready(self):
        import invoicing.signals
from django.conf import settings
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect
from haystack.generic_views import SearchView
from django.utils.translation import ugettext_lazy as _
from .search_forms import AninstanceSearchForm
from aninstance_framework import helpers, auth


class AninstanceSearchView(AccessMixin, SearchView):
    """ NOTES
    Search:
        Django-haystock search files are located thus:
            - aninstance/whoosh_index (auto gen)
            - aninstance/templates/search/indexes/<AN_APP>/<MODEL>_text.txt
            - aninstance/templates/search/indexes/search.html
            - aninstance/search_forms.py
            - aninstance/<AN_APP>/search_indexes.py
            - aninstance/urls.py
        - Don't forget to add the model(s) to  be searched in the CBV's "MODELS_TO_SEARCH[]" attribute,
          AND ALSO for granularity, add specific models to the "get" method of CBV to restrict model to search further,
          e.g.

            self.MODELS_TO_SEARCH = {
            'view_accounts': ['invoicing.client'],  # if url param is "view_accounts", search model invoicing.client
            }
            if 'q' in request.GET:  # if request via the search button, 'q' will be in request.GET, so go to search url
                return redirect(self.search_url)  #  search_url is constructed in AninstanceGenericView & passed to CBVs

        - Certainly don't forget to query request.GET for 'q' (as above) and redirect to the search URL if present, as
          the request to the view was therefore coming in after the search button had been clicked.

        - Don't forget to set the results_url in AninstanceSearchView "model_search_conf" method (below)

        - Update index with: ./manage.py rebuild_index
    Auth:
        Auth in the same way as AninstanceGenericView & it's child CBVs.
        AccessMixin included here to provide self.handle_no_permission() method
        for use when auth fails. AninstanceGenericView does auth by overriding dispatch method,
        but here it's done in get(), to keep it simple.
    """

    RESULTS_HEADING = 'Matching search results'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.models = []
        self.result_url = None
        self.auth_required = False  # false as default

    def get_queryset(self):
        queryset = super(AninstanceSearchView, self).get_queryset()
        ## further filter queryset based on some set of criteria
        return queryset

    def get_context_data(self, *args, **kwargs):
        context = super(AninstanceSearchView, self).get_context_data(**kwargs)
        context.update({'panel_heading': _('Search'),
                        'form': AninstanceSearchForm({'models': self.models}),
                        'result_url': self.result_url,
                        'results_heading': self.RESULTS_HEADING})
        # return the context
        return context

    def get(self, request, *args, **kwargs):
        """
        Handles GET requests and instantiates a blank version of the form.
        """
        # define specifics for model searches, including authorization if necessary
        # return redirect('search_view')
        if self.model_search_conf(request):  # if authenticated or authentication not required
            form_class = self.get_form_class()
            form = self.get_form(form_class)
            # update any session data (as this view not subclassing AninstanceGenericView, like normal)
            helpers.set_session_data(request)
            if form.is_valid():
                return self.form_valid(form)
            else:
                return self.form_invalid(form)
        else:  # authentication was required but user not authenticated
            return self.handle_no_permission()

    def model_search_conf(self, request):
        # configs specific to each model search
        if 'models' in request.GET and 'q' in request.GET and not settings.DEMO:
            # # # CLIENT MODEL
            if helpers.phrase_check('invoicing.account')(request.GET.get('models')):
                self.result_url = '/invoicing/?action=view_account&id='
                return auth.Authenticate(request, level=auth.USER_LEVEL.get('staff')).auth()
            # # # INVOICE MODEL
            elif helpers.phrase_check('invoicing.invoice')(request.GET.get('models')):
                self.result_url = '/invoicing/?action=view_invoice&invoice_number='
                return auth.Authenticate(request, level=auth.USER_LEVEL.get('staff')).auth()
            # # # INVOICE ITEM MODEL
            elif helpers.phrase_check('invoicing.invoiceitem')(request.GET.get('models')):
                self.result_url = '/invoicing/?action=view_invoice_item&invoice_item_number='
                return auth.Authenticate(request, level=auth.USER_LEVEL.get('staff')).auth()
            # # # ANY OTHER MODEL NOT DEFINED ABOVE AS REQUIRING AUTHENTICATION TO SEARCH
            else:
                return True  # authenticate request for anyone by default
        # if NO model chosen but a search query is being run, DO NOT authenticate
        elif 'q' in request.GET and 'models' not in request.GET:
            return False
        return True  # authenticate requests as default where there are NO search queries (just display form)

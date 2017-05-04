from django import forms
from haystack.forms import ModelSearchForm, SearchForm, model_choices
from django.utils.translation import ugettext_lazy as _


class AninstanceSearchForm(ModelSearchForm):
    # override elements of default SearchForm to add styling classes to fields

    def __init__(self, *args, **kwargs):
        super(AninstanceSearchForm, self).__init__(*args, **kwargs)

        # Only used if inheriting from ModelSearchForm (not SearchForm)
        self.fields['models'] = forms.MultipleChoiceField(choices=model_choices(),
                                                          required=False,
                                                          label=_('Search in'),
                                                          widget=forms.CheckboxSelectMultiple(attrs={
                                                              'class': 'form-control'
                                                          }),
                                                          )

    q = forms.CharField(required=False,
                        label=_('Search for'),
                        widget=forms.TextInput(attrs={'type': 'search',
                                                      'class': 'form-control',
                                                      'size': '20',
                                                      }))

    def get_models(self):
        return self.models

    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(AninstanceSearchForm, self).search()
        if not self.is_valid():
            return self.no_query_found()
        return sqs


class RightSidebarSearchForm(SearchForm):
    # override elements of default SearchForm to add styling classes to fields

    def __init__(self, *args, **kwargs):
        super(RightSidebarSearchForm, self).__init__()
        self.placeholder = kwargs.get('placeholder') if 'placeholder' in kwargs else _('Search')
        self.fields['q'] = forms.CharField(required=False,
                                           label=_('Search for'),
                                           widget=forms.TextInput(attrs={'type': 'search',
                                                                         'class': 'form-control',
                                                                         'size': '15',
                                                                         'placeholder': self.placeholder,
                                                                         }))

    def get_models(self):
        return self.models

    def search(self):
        # First, store the SearchQuerySet received from other processing.
        sqs = super(RightSidebarSearchForm, self).search()
        if not self.is_valid():
            return self.no_query_found()
        return sqs

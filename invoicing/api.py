from rest_framework import viewsets

from invoicing.models import Account
from invoicing.serializers import ClientSerializer

"""
Note:
* Remember to register all API routes with API router in main urls.py
* Remember to add add the model to app's serializers.py
* Authorization set to Token in settings.py (token can be created via API call with
appropriate headers, and/or auto created through signal call to a creation method when user model created).
"""


class ClientViewSet(viewsets.ModelViewSet):
    # API endpoint for creation, editing or viewing of Client model
    queryset = Account.objects.all().order_by('account_name')
    serializer_class = ClientSerializer


    # # REFERENCE METHOD TO SHOW MODEL VIA API
    #
    #
    # def get_view_clients(self, request):
    #     api_resource = 'client'
    #     api_request_url = '{}://{}/{}'.format(
    #         self.API_PROTO,
    #         self.API_BASE_URL,
    #         api_resource
    #     )
    #     try:
    #         data = requests.get(api_request_url,
    #                             headers={'User-Agent': 'Magic Browser',
    #                                      'Authorization': 'Token {}'.format(
    #                                          Token.objects.get_or_create(user=request.user)[0])
    #                                      })
    #         doc = data.json()
    #     except Exception as e:
    #         return http.HttpResponseNotFound(self.RESPONSE_INFO_API_CLIENT_ERROR)
    #     # format for display
    #     clients = []
    #     try:
    #         for client in doc.get('results'):
    #             clients.append([{field[1]: client[field[0]]} for field in Client.CLIENT_VERBOSE_FIELDNAMES])
    #     except TypeError:
    #         self.context.update({'no_results': self.NO_CLIENTS_BLURB})
    #     self.context.update({'clients': clients})
    #     return render(request, self.TEMPLATE_NAME, self.context)

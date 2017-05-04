from rest_framework import serializers
from invoicing.models import *


class ClientSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Account

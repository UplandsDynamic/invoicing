import pytz
from django.shortcuts import render, redirect
from django.views import generic


class SetTimeZone(generic.View):
    SUBMITTED_TEMPLATE = 'timezone.html'
    SUBMITTED_HEADING = 'Set your timezone'

    def get(self, request):
        context = {'timezones': pytz.common_timezones}
        return render(request, self.SUBMITTED_TEMPLATE, context)

    @staticmethod
    def post(request):
        request.session['django_timezone'] = request.POST['timezone']
        return redirect('/')

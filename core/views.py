"""Compatibility aggregator for project views."""

from django.http import HttpResponse

from .view_modules import *  # noqa: F401,F403
def ping(request):
    return HttpResponse("pong")

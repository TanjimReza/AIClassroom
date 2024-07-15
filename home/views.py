from django.shortcuts import render
from django.contrib.auth import logout, authenticate
from django.shortcuts import redirect, get_object_or_404, render
from django.http import HttpResponse
# Create your views here.


def home(request):
    return HttpResponse("Hello, world. You're at the home page.")

def logout_view(request):
    logout(request)
    return redirect('home')

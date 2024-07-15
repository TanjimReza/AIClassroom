from django.shortcuts import render
from django.contrib.auth import logout, authenticate
from django.shortcuts import redirect, get_object_or_404, render
# Create your views here.


def logout_view(request):
    logout(request)
    return redirect('home')

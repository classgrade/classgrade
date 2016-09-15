from django.shortcuts import render


def index(request):
    context = {'main_info': 'oh yeah'}
    return render(request, 'gradapp/index.html', context)

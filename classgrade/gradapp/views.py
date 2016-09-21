from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from gradapp.forms import AssignmentypeForm
from gradapp.models import Assignmentype


def index(request):
    context = {'main_info': 'oh yeah'}
    return render(request, 'gradapp/index.html', context)


@login_required
def create_assignmentype(request):
    context = {}
    if request.method == 'POST':
        form = AssignmentypeForm(request.POST)
        if form.is_valid():
            if not Assignmentype.objects.filter(title=form.
                                                cleaned_data['title']):
                new_assignmentype =\
                    Assignmentype(title=form.cleaned_data['title'],
                                  description=form.cleaned_data['description'],
                                  nb_graders=form.cleaned_data['nb_graders'],
                                  file_type=form.cleaned_data['file_type'],
                                  deadline_submission=form.
                                  cleaned_data['deadline_submission'],
                                  deadline_grading=form.
                                  cleaned_data['deadline_grading'],
                                  prof=request.user)
                new_assignmentype.save()
                # get list students from csv file

                return redirect("gradapp:index")
            else:
                context['error'] = 'Oups, this assignment title has, \
                                    already been used, change it!'
    else:
        form = AssignmentypeForm()
    context['form'] = form
    return render(request, 'gradapp/create_assignmentype.html', context)

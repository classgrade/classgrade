import csv
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from gradapp.forms import AssignmentypeForm
from gradapp.models import Assignmentype


logger = logging.getLogger(__name__)


def _make_error_message(e):
    if hasattr(e, 'traceback'):
        return str(e.traceback)
    else:
        return repr(e)


def get_students(csv_file):
    """
    :param csv_file: csv file with list of students.\
        Each row contains: first_name, last_name, email
    :type csv_file: str
    :rtype: 2 lists existing_students and new_students [[username, email], ..]
    """

    with open(csv_file) as ff:
        reader = csv.reader(ff, delimiter=',')
        existing_students = []
        new_students = []
        for i, row in enumerate(reader):
            row = [x.strip() for x in row[:3]]
            username = "_".join(row[:2])
            username = username.replace(" ", "_")
            email = row[2]
            try:
                u = User.objects.get(username=username)
                existing_students.append([u.username, u.email])
            except ObjectDoesNotExist:
                new_students.append([username, email])
    return existing_students, new_students


def index(request):
    context = {'main_info': 'oh yeah'}
    return render(request, 'gradapp/index.html', context)


@login_required
def create_assignmentype(request):
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    context = {}
    if request.method == 'POST':
        form = AssignmentypeForm(request.POST, request.FILES)
        if form.is_valid():
            if not Assignmentype.objects.filter(title=form.
                                                cleaned_data['title']):
                new_assignmentype = form.save(commit=False)
                new_assignmentype.prof = prof
                new_assignmentype.save()
                # get list students from csv file
                try:
                    existing_students, new_students =\
                        get_students(new_assignmentype.list_students.path)
                    # return page asking for agreement for creation of students
                    return redirect("gradapp:index")
                except Exception as e:
                    logger.error(_make_error_message(e))
                    new_assignmentype.list_students = None
                    new_assignmentype.save()
                    # return details page of assignmentype
                    return redirect('/assignmentype/%s' %
                                    new_assignmentype.pk)
            else:
                context['error'] = 'Oups, this assignment title has \
                                    already been used, change it!'
    else:
        form = AssignmentypeForm()
    context['form'] = form
    return render(request, 'gradapp/create_assignmentype.html', context)

import csv
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from gradapp.forms import AssignmentypeForm
from gradapp.models import Assignment, Assignmentype, Student


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
                Student.objects.get(user=u)
                existing_students.append([u.username, u.email])
            except ObjectDoesNotExist:
                new_students.append([username, email])
    return existing_students, new_students


def index(request):
    context = {'main_info': 'oh yeah'}
    return render(request, 'gradapp/index.html', context)


@login_required
def create_assignmentype(request, assignmentype_id=None):
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    if assignmentype_id:
        assignmentype = Assignmentype.objects.get(id=assignmentype_id)
        context = {'message': 'Update your assignment'}
    else:
        assignmentype = None
        context = {'message': 'Create a new assignment!'}
    print(assignmentype)
    if request.method == 'POST':
        form = AssignmentypeForm(request.POST, request.FILES,
                                 instance=assignmentype)
        if form.is_valid():
            if (not assignmentype) and (Assignmentype.objects.filter(
                                            title=form.cleaned_data['title'])):
                context['error'] = 'Oups, this assignment title has \
                                    already been used, change it!'
            else:
                new_assignmentype = form.save(commit=False)
                new_assignmentype.prof = prof
                new_assignmentype.save()
                # get list students from csv file
                try:
                    existing_students, new_students =\
                        get_students(new_assignmentype.list_students.path)
                    # return page asking for agreement for creation of students
                    request.session['existing_students'] = existing_students
                    request.session['new_students'] = new_students
                    request.session['assignmentype_pk'] = new_assignmentype.pk
                    return redirect("gradapp:validate_assignmentype_students")
                except Exception as e:
                    logger.error(_make_error_message(e))
                    new_assignmentype.list_students = None
                    new_assignmentype.save()
                    # return details page of assignmentype
                    return redirect('/update_assignmentype/%s/' %
                                    new_assignmentype.pk)
    else:
        form = AssignmentypeForm(instance=assignmentype)
    context['form'] = form
    context['assignmentype'] = assignmentype
    return render(request, 'gradapp/assignmentype_form.html', context)


@login_required
def validate_assignmentype_students(request):
    """
    When creating an assignment, shows students that will be associated to
    (existing students and new students). If validated, new students are created
    and new+existing students are associated to the assignment.
    """
    existing_students = request.session.get('existing_students', False)
    new_students = request.session.get('new_students', False)
    assignmentype_pk = request.session.get('assignmentype_pk', False)
    if assignmentype_pk:
        assignmentype = Assignmentype.objects.get(id=assignmentype_pk)
        return render(request, 'gradapp/validate_assignmentype_students.html',
                      {'existing_students': existing_students,
                       'new_students': new_students,
                       'assignmentype': assignmentype})
    else:
        return redirect('gradapp:index')


def create_assignmentype_students(request):
    """
    After validate_assignmentype_students, create new students and associate
    new+existing students to the assigment
    """
    existing_students = request.session.get('existing_students', False)
    new_students = request.session.get('new_students', False)
    assignmentype_pk = request.session.get('assignmentype_pk', False)
    if assignmentype_pk:
        assignmentype = Assignmentype.objects.get(id=assignmentype_pk)
        for st in existing_students:
            u = User.objects.get(username=st[0])
            student = Student.objects.get(user=u)
            Assignment.objects.get_or_create(student=student,
                                             assignmentype=assignmentype)
        for st in new_students:
            password = 'aaa'
            u = User.objects.create_user(st[0], st[1], password)
            student = Student.objects.create(user=u)
            Assignment.objects.create(student=student,
                                      assignmentype=assignmentype)
    return redirect('gradapp:index')

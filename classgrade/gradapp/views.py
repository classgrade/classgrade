# coding=utf-8
import logging
import os
import csv
import zipfile
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from xkcdpass import xkcd_password as xp
from unidecode import unidecode
from classgrade import settings
from gradapp.forms import AssignmentypeForm, AssignmentForm, EvalassignmentForm
from gradapp.forms import LightAssignmentypeForm
from gradapp.models import Assignment, Assignmentype, Student, Evalassignment
from gradapp import tasks

logger = logging.getLogger(__name__)


def make_error_message(e):
    """
    Get error message
    """
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
            row = [unidecode(x.strip()) for x in row[:3]]
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


def is_evaluated(evalassignment):
    """
    Check state of evalassignment.
    :param evalassignment: evalassignment instance
    :type evalassignment: gradapp.models.Evalassignment
    :rtype: -30 if document to be evaluated has not be uploaded or
    if it is before the submission deadline,
    -20 if uploaded, -10 if uploaded and evaluated
    """
    if evalassignment.assignment.document.name == '' or evalassignment.\
            assignment.assignmentype.deadline_submission > timezone.now():
        return -30
    else:
        if evalassignment.grade_assignment:
            if evalassignment.grade_evaluation:
                return evalassignment.grade_evaluation
            else:
                return -10
        else:
            return -20


def index(request):
    if request.user.is_authenticated:
        try:
            request.user.prof
            return redirect('gradapp:list_assignmentypes_running')
        except ObjectDoesNotExist:
            return redirect('gradapp:dashboard_student')
    else:
        return redirect('accounts:login')


@login_required
def dashboard_student(request):
    """
    Student dashboard: list all due assignments (to do and to evaluate)
    """
    try:
        student = request.user.student
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    context = {'student_name': student.user.username}
    list_assignments = []
    assignments = student.assignment_set.all().\
        order_by('assignmentype__deadline_submission')
    for assignment in assignments:
        # check if too late to submit or if assignment has already been uploaded
        if assignment.document.name is '' and\
                assignment.assignmentype.deadline_submission >= timezone.now():
            todo = 0  # submit
        elif assignment.assignmentype.deadline_submission < timezone.now():
            if assignment.document.name is '':
                todo = -2  # too late
            else:
                todo = -1  # too late, but see your file
        else:
            todo = 1  # resubmit
        # get assignments to be evaluated by the student
        to_be_evaluated = Evalassignment.objects.\
            filter(evaluator=student,
                   assignment__assignmentype=assignment.assignmentype)
        to_be_evaluated = [(i, is_evaluated(evalassignment),
                            evalassignment.id) for i, evalassignment in
                           enumerate(to_be_evaluated)]
        # get evaluations given to the student assignment
        if assignment.assignmentype.deadline_grading < timezone.now():
            evaluations = [(e.id, e.grade_evaluation, e.grade_assignment,
                            e.grade_assignment_comments)
                           for e in assignment.evalassignment_set.all()]
        else:
            evaluations = [(None, None, None, None)] * assignment.\
                assignmentype.nb_grading
        list_assignments.append([assignment.assignmentype.title,
                                 assignment.assignmentype.description,
                                 assignment.assignmentype.deadline_submission,
                                 assignment.assignmentype.deadline_grading,
                                 assignment.id, todo,
                                 to_be_evaluated, evaluations])
    context['list_assignments'] = list_assignments
    return render(request, 'gradapp/dashboard_student.html', context)


@login_required
def upload_assignment(request, pk):
    """
    Upload assignment
    """
    try:
        student = request.user.student
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignment = Assignment.objects.filter(pk=pk, student=student).first()
    if assignment:
        if request.method == 'POST':
            form = AssignmentForm(request.POST, request.FILES,
                                  instance=assignment)
            if form.is_valid():
                form.save()
                return redirect('gradapp:dashboard_student')
        else:
            form = AssignmentForm(instance=assignment)
        context = {'form': form, 'title': assignment.assignmentype.title,
                   'description': assignment.assignmentype.description,
                   'deadline': assignment.assignmentype.deadline_submission,
                   'assignment_id': assignment.id}
        return render(request, 'gradapp/assignment_form.html', context)
    else:
        return redirect('gradapp:index')


@login_required
def eval_assignment(request, pk):
    """
    Evaluate the assignment (Evalassignment(pk=pk))
    """
    try:
        student = request.user.student
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    evalassignment = Evalassignment.objects.filter(pk=pk, evaluator=student).\
        first()
    if evalassignment and evalassignment.assignment.assignmentype.\
            deadline_submission < timezone.now():
        error = ''
        if request.method == 'POST' and evalassignment.assignment.\
                assignmentype.deadline_grading >= timezone.now():
            form = EvalassignmentForm(request.POST, instance=evalassignment)
            if form.is_valid():
                new_eval = form.save(commit=False)
                # if evaluation is modified, evaluation grade is reset
                new_eval.grade_evaluation = None
                new_eval.save()
                return redirect('gradapp:dashboard_student')
        else:
            form = EvalassignmentForm(instance=evalassignment)
            if evalassignment.assignment.assignmentype.\
                    deadline_grading < timezone.now():
                error = 'Too late to grade or to modify your grading...'
        context = {'form': form,
                   'title': evalassignment.assignment.assignmentype.title,
                   'description': evalassignment.assignment.
                   assignmentype.description,
                   'assignment_doc': evalassignment.assignment.document.url,
                   'evalassignment_id': evalassignment.id,
                   'deadline': evalassignment.assignment.assignmentype.
                   deadline_grading,
                   'error': error}
        return render(request, 'gradapp/evalassignment_form.html', context)
    else:
        if evalassignment:
            redirect_item = '#assignment%s' % evalassignment.assignment.id
        else:
            redirect_item = ''
        return redirect('/dashboard_student/' + redirect_item)


@login_required
def eval_evalassignment(request, pk, pts):
    """
    Evaluate the assignment evaluation (Evalassignment(pk=pk)).
    evalassignment.grade_evaluation = pts (-1, 0, +1)
    """
    try:
        student = request.user.student
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    evalassignment = Evalassignment.objects.\
        filter(pk=pk, assignment__student=student).first()
    if evalassignment:
        evalassignment.grade_evaluation = pts
        evalassignment.save()
        redirect_item = '#assignment%s' % evalassignment.assignment.id
    else:
        redirect_item = ''
    return redirect('/dashboard_student/' + redirect_item)


@login_required
def create_assignmentype(request, assignmentype_id=None):
    """
    Create an assignmentype or modify it (with new student list).
    Caution: when modified with this function assignmentype.assignment_set.all()
    are reset... Do not do it after students have already done something!
    """
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    context = {}
    if assignmentype_id:
        assignmentype = Assignmentype.objects.get(id=assignmentype_id)
        message = 'Reset your assignment. You can upload a new student list, '\
            'but be aware that it will reset the assignment (all former work '\
            'will be lost!)'
        type_post = 'reset'  # reset the assignmentype
        context['assignmentype_id'] = assignmentype.id
    else:
        assignmentype = None
        message = 'Create a new assignment!'
        type_post = 'create'  # new assignmentype
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
                # create folder where to upload assignments
                try:
                    os.mkdir(os.path.join(settings.BASE_DIR,
                                          settings.MEDIA_ROOT, 'assignment_%s' %
                                          new_assignmentype.id))
                except FileExistsError:
                    pass
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
                    logger.error(make_error_message(e))
                    new_assignmentype.list_students = None
                    new_assignmentype.save()
                    # return update page of assignmentype
                    return redirect('/reset_assignmentype/%s/' %
                                    new_assignmentype.pk)
    else:
        form = AssignmentypeForm(instance=assignmentype)
    context['message'] = message
    context['form'] = form
    context['type_post'] = type_post
    return render(request, 'gradapp/assignmentype_form.html', context)


@login_required
def modify_assignmentype(request, pk):
    """
    Modify assignmentype fields, except student list.
    """
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignmentype = Assignmentype.objects.filter(id=pk, prof=prof).first()
    if assignmentype:
        if request.method == 'POST':
            form = LightAssignmentypeForm(request.POST, instance=assignmentype)
            if form.is_valid():
                form.save()
                return redirect('/detail_assignmentype/%s/' % assignmentype.pk)
        else:
            form = LightAssignmentypeForm(instance=assignmentype)
            context = {}
            context['assignmentype_id'] = assignmentype.id
            context['message'] = 'Modify details of your assignment '\
                '(keep current student list)'
            context['form'] = form
            context['type_post'] = 'modify'
            return render(request, 'gradapp/assignmentype_form.html', context)
    else:
        return redirect('gradapp:index')


@login_required
def delete_assignmentype(request, pk, type_list):
    """
    Delete assignmentype with id=pk and redirect to list of running
    assignmentype if type_list=='1', and to list of archived assignmentype
    if type_list=='0'
    """
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignmentype = Assignmentype.objects.filter(id=pk, prof=prof).first()
    if assignmentype:
        assignmentype.delete()
        if type_list == '1':
            return redirect('gradapp:list_assignmentypes_running')
        elif type_list == '0':
            return redirect('gradapp:list_assignmentypes_archived')
    else:
        return redirect('gradapp:index')


@login_required
def archive_assignmentype(request, pk):
    """
    Update assignmentype with id=pk and redirect to list of running
    assignmentype
    """
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignmentype = Assignmentype.objects.filter(id=pk, prof=prof).first()
    if assignmentype:
        assignmentype.archived = True
        assignmentype.save()
        return redirect('gradapp:list_assignmentypes_archived')
    else:
        return redirect('gradapp:index')


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
    new+existing students to an assignmentype.assignment.
    """
    existing_students = request.session.get('existing_students', False)
    new_students = request.session.get('new_students', False)
    assignmentype_pk = request.session.get('assignmentype_pk', False)
    if assignmentype_pk:
        words = xp.locate_wordfile()
        mywords = xp.generate_wordlist(wordfile=words, min_length=4,
                                       max_length=6)
        assignmentype = Assignmentype.objects.get(id=assignmentype_pk)
        for assignment in assignmentype.assignment_set.all():
            assignment.delete()
        for st in existing_students:
            student = Student.objects.get(user__username=st[0])
            # Get an existing assignment or create it
            Assignment.objects.get_or_create(student=student,
                                             assignmentype=assignmentype)

        for st in new_students:
            password = xp.generate_xkcdpassword(mywords, numwords=4)
            u = User.objects.create_user(st[0], st[1], password)
            student = Student.objects.create(user=u)
            # Send email
            tasks.email_new_student(u.email, u.username, password)
            # Create the assignment
            Assignment.objects.create(student=student,
                                      assignmentype=assignmentype)
        # The line below could be in a new function to separate shuffling from
        # assignment
        log = tasks.create_evalassignment(assignmentype.title)
        logger.info(log)
        return redirect('/detail_assignmentype/%s/' % assignmentype_pk)
    else:
        # TODO return error message
        return redirect('gradapp:index')


@login_required
def list_assignmentypes_running(request):
    """
    List all running (archived=False) assignmentype
    """
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    context = {'type_assignmentype': 'running', 'prof': prof}
    context['list_assignmentypes'] = Assignmentype.objects.\
        filter(archived=False, prof=prof).order_by('deadline_submission')
    return render(request, 'gradapp/list_assignmentype.html',
                  context)


@login_required
def list_assignmentypes_archived(request):
    """
    List all archived assignmentype
    """
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    context = {'type_assignmentype': 'archived', 'prof': prof}
    context['list_assignmentypes'] = Assignmentype.objects.\
        filter(archived=True, prof=prof)
    return render(request, 'gradapp/list_assignmentype.html',
                  context)


@login_required
def detail_assignmentype(request, pk):
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    context = {'prof': prof}
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    if assignmentype:
        context['assignmentype'] = assignmentype
        context['range_grades'] = range(assignmentype.nb_grading)
        return render(request, 'gradapp/detail_assignmentype.html',
                      context)
    else:
        return redirect('gradapp:index')


@login_required
def generate_csv_grades(request, pk):
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grades.csv"'
    writer = csv.writer(response)
    if assignmentype:
        for assignment in assignmentype.assignment_set.all():
            list_as = [assignment.student.user.username]
            for evaluation in assignment.evalassignment_set.all():
                list_as.extend([evaluation.evaluator.user.username,
                                evaluation.grade_assignment,
                                evaluation.grade_evaluation])
            writer.writerow(list_as)
    else:
        writer.writerow(['Oups... you might not be a prof or this assignment '
                         'might not exist'])
    return response


@login_required
def generate_txt_comments(request, pk):
    try:
        request.user.prof
        evalassignment = Evalassignment.objects.filter(pk=pk).first()
    except ObjectDoesNotExist:
        student = request.user.student
        evalassignment = Evalassignment.objects.\
            filter(pk=pk, assignment__student=student).first()
    response = HttpResponse(content_type='text/txt')
    response['Content-Disposition'] = 'attachment; filename="comments.txt"'
    writer = csv.writer(response)
    if evalassignment:
        writer.writerow([evalassignment.grade_assignment_comments])
    else:
        writer.writerow(['Oups... you might not be allowed to see this'])
    return response


@login_required
def generate_zip_assignments(request, pk):
    try:
        prof = request.user.prof
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    dir_name = 'assignment_%s' % assignmentype.id
    file_path = os.path.join(settings.BASE_DIR, settings.MEDIA_ROOT,
                             dir_name)
    zip_name = '{0}.zip'.format(file_path)
    zipf = zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(file_path):
        for filename in files:
            assignment = Assignment.objects.\
                filter(document='{0}/{1}'.format(dir_name, filename)).first()
            new_filename = '{0}_{1}.{2}'.format(dir_name, assignment.student.
                                                user.username,
                                                filename.split('.')[-1])
            zipf.write(os.path.abspath(os.path.join(root, filename)),
                       arcname=new_filename)
    zipf.close()
    fsock = open(zip_name, "rb")
    response = HttpResponse(fsock,
                            content_type="application/force_download")
    response['Content-Disposition'] = 'attachment; filename=%s.zip' % dir_name

    return response


@login_required
def get_assignment(request, pk):
    try:
        student = request.user.student
    except ObjectDoesNotExist:
        return redirect('gradapp:index')
    assignment = Assignment.objects.filter(student=student, pk=pk).first()
    if assignment:
        try:
            fsock = open(assignment.document.path, "rb")
            response = HttpResponse(fsock,
                                    content_type="application/force_download")
            response['Content-Disposition'] = 'attachment; filename=%s' %\
                assignment.document.name.split('/')[-1]
            return response
        except ValueError:
            return redirect('/dashboard_student/#assignment%s' %
                            assignment.id)
    else:
        return redirect('gradapp:dashboard_student')

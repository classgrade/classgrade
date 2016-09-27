import logging
import csv
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from xkcdpass import xkcd_password as xp
from gradapp.forms import AssignmentypeForm, AssignmentForm, EvalassignmentForm
from gradapp.models import Assignment, Assignmentype, Student, Evalassignment
from gradapp.tasks import create_evalassignment

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


def is_evaluated(evalassignment):
    """
    Check state of evalassignment.
    :param evalassignment: evalassignment instance
    :type evalassignment: gradapp.models.Evalassignment
    :rtype: -30 if document to be evaluated has not be uploaded,
    -20 if uploaded, -10 if uploaded and evaluated
    """
    if evalassignment.assignment.document.name == '':
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
    context = {'main_info': 'oh yeah'}
    return render(request, 'gradapp/index.html', context)


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
        # get assignments to be evaluated by the student
        to_be_evaluated = Evalassignment.objects.\
            filter(evaluator=student,
                   assignment__assignmentype=assignment.assignmentype)
        to_be_evaluated = [(i, is_evaluated(evalassignment),
                            evalassignment.id) for i, evalassignment in
                           enumerate(to_be_evaluated)]
        # get evaluations given to the student assignment
        evaluations = [(e.id, e.grade_evaluation, e.grade_assignment,
                        e.grade_assignment_comments)
                       for e in assignment.evalassignment_set.all()]
        print(evaluations)
        list_assignments.append([assignment.assignmentype.title,
                                 assignment.assignmentype.description,
                                 assignment.assignmentype.deadline_submission,
                                 assignment.assignmentype.deadline_grading,
                                 assignment.id,
                                 (assignment.document.name is ''),
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
    if evalassignment:
        if request.method == 'POST':
            form = EvalassignmentForm(request.POST, instance=evalassignment)
            if form.is_valid():
                new_eval = form.save(commit=False)
                # if evaluation is modified, evaluation grade is reset
                new_eval.grade_evaluation = None
                new_eval.save()
                return redirect('gradapp:dashboard_student')
        else:
            form = EvalassignmentForm(instance=evalassignment)
        context = {'form': form,
                   'title': evalassignment.assignment.assignmentype.title,
                   'description': evalassignment.assignment.
                   assignmentype.description,
                   'assignment_doc': evalassignment.assignment.document.url,
                   'evalassignment_id': evalassignment.id,
                   'deadline': evalassignment.assignment.assignmentype.
                   deadline_grading}
        return render(request, 'gradapp/evalassignment_form.html', context)
    else:
        return redirect('gradapp:index')


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
                    logger.error(make_error_message(e))
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
    new+existing students to the assignment
    """
    existing_students = request.session.get('existing_students', False)
    new_students = request.session.get('new_students', False)
    assignmentype_pk = request.session.get('assignmentype_pk', False)
    if assignmentype_pk:
        words = xp.locate_wordfile()
        mywords = xp.generate_wordlist(wordfile=words, min_length=4,
                                       max_length=6)
        assignmentype = Assignmentype.objects.get(id=assignmentype_pk)
        for st in existing_students:
            student = Student.objects.get(user__username=st[0])
            Assignment.objects.get_or_create(student=student,
                                             assignmentype=assignmentype)

        for st in new_students:
            password = xp.generate_xkcdpassword(mywords, numwords=4)
            u = User.objects.create_user(st[0], st[1], password)
            student = Student.objects.create(user=u)
            # TODO Send email
            Assignment.objects.create(student=student,
                                      assignmentype=assignmentype)
        log = create_evalassignment(assignmentype.title)
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
        return render(request, 'gradapp/detail_assignmentype.html',
                      context)

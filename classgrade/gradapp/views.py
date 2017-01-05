# coding=utf-8
import logging
import os
from functools import wraps
import csv
import zipfile
import django.forms as forms
from django.db.models import F, Avg, StdDev
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from django.utils.decorators import available_attrs
from django.forms import modelformset_factory
from xkcdpass import xkcd_password as xp
from unidecode import unidecode
from classgrade import settings
from gradapp.forms import AssignmentypeForm, AssignmentForm
from gradapp.forms import LightAssignmentypeForm, CoeffForm
from gradapp.forms import AddQuestionForm, RemoveQuestionForm
from gradapp.models import Assignment, Assignmentype, Student, Evalassignment
from gradapp.models import Evalquestion
from gradapp import tasks

logger = logging.getLogger(__name__)


def login_prof(func):
    """
    Decorator which checks the user is a prof before executing a view
    Redirect to the index page if not
    """
    @wraps(func, assigned=available_attrs(func))
    def wrapper(request, *args, **kwargs):
        try:
            request.user.prof
        except ObjectDoesNotExist:
            return redirect('gradapp:dashboard_student')
        res = func(request, *args, **kwargs)
        return res
    return wrapper


def login_student(func):
    """
    Decorator which checks the user is a student before executing a view
    Redirect to the index page if not
    """
    @wraps(func, assigned=available_attrs(func))
    def wrapper(request, *args, **kwargs):
        try:
            request.user.student
        except ObjectDoesNotExist:
            return redirect('gradapp:list_assignmentypes_running')
        res = func(request, *args, **kwargs)
        return res
    return wrapper


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
        if evalassignment.is_questions_graded:
            if evalassignment.grade_evaluation:
                return evalassignment.grade_evaluation
            else:
                return -10
        else:
            return -20


def base_eval_assignment(request, evalassignment, url_action, url_cancel):
    """
    Generate/Postprocess a form to evaluate an assigment
    """
    error = ''
    EvalquestionFormSet =\
        modelformset_factory(Evalquestion, extra=0,
                             fields=['grade', 'comments'],
                             widgets={'grade':
                                      forms.NumberInput(attrs={'min': 0,
                                                               'max': 2}),
                                      'comments':
                                      forms.Textarea(attrs={'cols': 80,
                                                            'rows': 10})})
    qs = Evalquestion.objects.filter(evalassignment=evalassignment).\
        order_by('question')
    if request.method == 'POST' and (evalassignment.assignment.assignmentype.
                                     deadline_grading >= timezone.now() or
                                     evalassignment.is_supereval):
        formset = EvalquestionFormSet(request.POST, queryset=qs)
        if formset.is_valid():
            formset.save()
            # if evaluation is modified, evaluation grade is reset
            evalassignment.grade_evaluation = 0
            evalassignment.is_questions_graded =\
                (None not in [q.grade for q
                              in evalassignment.evalquestion_set.all()])
            evalassignment.save()
            # set evalassignment.grade_assignment if question coeff exist
            log = tasks.compute_grade_evalassignment(evalassignment.id)
            logger.error(log)
            return None
    else:
        formset = EvalquestionFormSet(queryset=qs)
        if evalassignment.assignment.assignmentype.\
                deadline_grading < timezone.now():
            error = 'Too late to grade or to modify your grading...'
    assignmentype = evalassignment.assignment.assignmentype
    list_questions = [i for i in range(1, assignmentype.nb_questions + 1)]
    context = {'formset': zip(formset, list_questions),
               'title': assignmentype.title,
               'description': assignmentype.description,
               'evalassignment_id': evalassignment.id,
               'deadline': assignmentype.deadline_grading,
               'error': error,
               'url_action': url_action,
               'url_cancel': url_cancel}
    return context


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
@login_student
def dashboard_student(request):
    """
    Student dashboard: list all due assignments (to do and to evaluate)
    """
    student = request.user.student
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
            filter(evaluator=student.user,
                   assignment__assignmentype=assignment.assignmentype).\
            order_by('pk')
        to_be_evaluated = [(i, is_evaluated(evalassignment),
                            evalassignment.id) for i, evalassignment in
                           enumerate(to_be_evaluated)]
        # get evaluations given to the student assignment
        if assignment.assignmentype.deadline_grading < timezone.now():
            if assignment.get_super_eval():
                full_evaluations = [assignment.get_super_eval()]
            else:
                full_evaluations = assignment.get_normal_eval().order_by('pk')
            evaluations = [(e.id, e.is_questions_graded, e.is_supereval,
                            e.grade_evaluation, e.grade_assignment,
                            [(qq.question, qq.grade, qq.comments)
                             for qq in e.evalquestion_set.all().
                             order_by('question')])
                           for e in full_evaluations]
        else:
            evaluations = [(None, None, None, None, None, None)] * assignment.\
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
@login_student
def upload_assignment(request, pk):
    """
    Upload assignment
    """
    student = request.user.student
    assignment = Assignment.objects.filter(pk=pk, student=student).first()
    if assignment:
        if request.method == 'POST':
            form = AssignmentForm(request.POST, request.FILES,
                                  instance=assignment)
            if form.is_valid():
                form.save()
                # Send confirmation email to student
                assignmentype_title = assignment.assignmentype.title
                try:
                    tasks.email_confirm_upload_assignment(
                        student.user.email, assignmentype_title,
                        request.FILES['document'].name,
                        assignment.assignmentype.deadline_submission)
                except Exception as e:
                    logger.error('Not possible to send confirmation email to '
                                 '%s for assignment %s: %s' %
                                 (student.user.username, assignmentype_title,
                                  make_error_message(e)))
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
@login_student
def eval_assignment(request, pk):
    """
    Evaluate the assignment (Evalassignment(pk=pk))
    """
    evalassignment = Evalassignment.objects.filter(evaluator=request.user,
                                                   pk=pk).first()
    if evalassignment and evalassignment.assignment.assignmentype.\
            deadline_submission < timezone.now():
        # if evalassignment exists and if it is after the submission deadline
        context = base_eval_assignment(
            request, evalassignment,
            '/eval_assignment/%s/' % evalassignment.id, '/dashboard_student/')
        if context:
            return render(request, 'gradapp/evalassignment_form.html', context)
        else:
            return redirect('/dashboard_student/#assignment%s' %
                            evalassignment.assignment.id)
    else:
        # if evalassignment does not exist or before submission deadline
        if evalassignment:
            redirect_item = '#assignment%s' % evalassignment.assignment.id
        else:
            redirect_item = ''
        return redirect('/dashboard_student/' + redirect_item)


@login_required
@login_prof
def supereval_assignment(request, assignment_pk):
    """
    Evaluate the assignment (pk=assignment_pk) and makes your evaluation a
    superevaluation
    """
    assignment = Assignment.objects.get(id=assignment_pk)
    evalassignment = Evalassignment.objects.filter(assignment=assignment,
                                                   is_supereval=True).first()
    redirect_url = ('/detail_assignmentype/%s/#assignment_%s' %
                    (assignment.assignmentype.id, assignment.id))
    if not evalassignment:
        evalassignment = Evalassignment(evaluator=request.user,
                                        assignment=assignment)
        evalassignment.is_supereval = True
        evalassignment.save()
        for iq in range(assignment.assignmentype.nb_questions):
            Evalquestion.objects.create(evalassignment=evalassignment,
                                        question=(iq + 1))
    context = base_eval_assignment(request, evalassignment,
                                   '/supereval_assignment/%s/' % assignment_pk,
                                   redirect_url)
    if context:
        return render(request, 'gradapp/evalassignment_form.html', context)
    else:
        return redirect(redirect_url)


@login_required
@login_prof
def download_assignment_prof(request, pk):
    """
    Get assignment for a prof
    """
    assignment = Assignment.objects.\
        filter(pk=pk, assignmentype__prof__user=request.user).first()
    if assignment:
        filename = 'assign_%s.%s' % (assignment.student.user.username,
                                     assignment.document.name.split('.')[-1])
        response = HttpResponse(assignment.document,
                                content_type='application/force_download')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response
    else:
        return redirect('gradapp:list_assignmentypes_running')


@login_required
def download_assignment_student(request, pk):
    """
    Get assignment to be evaluated by student
    """
    evalassignment = Evalassignment.objects.\
        filter(pk=pk, evaluator=request.user).first()
    if evalassignment:
        filename = 'assign_%s.%s' % (pk, evalassignment.assignment.
                                     document.name.split('.')[-1])
        response = HttpResponse(evalassignment.assignment.document,
                                content_type='application/force_download')
        response['Content-Disposition'] = 'attachment; filename=%s' % filename
        return response
    else:
        return redirect('gradapp:dashboard_student')


@login_required
@login_student
def eval_evalassignment(request, pk, pts):
    """
    Evaluate the assignment evaluation (Evalassignment(pk=pk)).
    evalassignment.grade_evaluation = pts (-1, 0, +1)
    """
    student = request.user.student
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
@login_prof
def create_assignmentype(request, assignmentype_id=None):
    """
    Create an assignmentype or modify it (with new student list).
    Caution: when modified with this function assignmentype.assignment_set.all()
    are reset... Do not do it after students have already done something!
    """
    prof = request.user.prof
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
@login_prof
def insert_question_assignmentype(request, pk, cd):
    """
    Insert a question for an assignmentype (pk=pk). The user enters in a form a
    question to be created (cd=1) or a question to be deleted (cd=-1)
    """
    prof = request.user.prof
    assignmentype = Assignmentype.objects.filter(id=pk, prof=prof).first()
    cd = int(cd)
    if cd == 1:
        classForm = AddQuestionForm
        info = 'Add'
    elif cd == -1:
        classForm = RemoveQuestionForm
        info = 'Remove'
    if assignmentype:
        if request.method == 'POST':
            form = classForm(request.POST,
                             nb_questions=assignmentype.nb_questions)
            if form.is_valid():
                question = form.cleaned_data['question']
                # Modify attribute question of all associated evalquestion
                if cd == -1:
                    evalquestions = Evalquestion.objects.filter(
                        evalassignment__assignment__assignmentype=assignmentype,
                        question=question)
                    evalquestions.delete()
                evalquestions = Evalquestion.objects.filter(
                    evalassignment__assignment__assignmentype=assignmentype,
                    question__gte=question)
                evalquestions.update(question=F('question') + cd)
                # Create a new evalquestion for each evalassignment (if cd=1)
                # and inform that it has to be graded
                for evalassignment in Evalassignment.objects.filter(
                        assignment__assignmentype=assignmentype):
                    if cd == 1:
                        Evalquestion.objects.create(
                            evalassignment=evalassignment, question=question)
                        evalassignment.reset_grade()
                    elif cd == -1:
                        evalassignment.grade_assignment = None
                    evalassignment.save()
                # Add a question to the assignmentype
                assignmentype.nb_questions += cd
                if cd == 1:
                    if assignmentype.questions_coeff:
                        assignmentype.questions_coeff.insert(question - 1, None)
                    assignmentype.save()
                elif cd == -1:
                    if assignmentype.questions_coeff:
                        del assignmentype.questions_coeff[question - 1]
                    assignmentype.save()
                    log = tasks.compute_grades_assignmentype(assignmentype.pk)
                    logger.info(log)
                return redirect('/detail_assignmentype/%s/' % assignmentype.pk)
        form = classForm(nb_questions=assignmentype.nb_questions)
        context = {'assignmentype': assignmentype, 'form': form, 'info': info,
                   'cd': cd}
        return render(request, 'gradapp/insert_question.html', context)
    else:
        return redirect('gradapp:index')


@login_required
@login_prof
def modify_assignmentype(request, pk):
    """
    Modify assignmentype fields, except student list.
    """
    prof = request.user.prof
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
@login_prof
def delete_assignmentype(request, pk, type_list):
    """
    Delete assignmentype with id=pk and redirect to list of running
    assignmentype if type_list=='1', and to list of archived assignmentype
    if type_list=='0'
    """
    prof = request.user.prof
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
@login_prof
def archive_assignmentype(request, pk):
    """
    Update assignmentype with id=pk and redirect to list of running
    assignmentype
    """
    prof = request.user.prof
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
            try:
                tasks.email_new_student(u.email, u.username, password)
            except Exception as e:
                logger.error('Not possible to email new student %s: %s' %
                             (u.username, make_error_message(e)))
            # Create the assignment
            Assignment.objects.create(student=student,
                                      assignmentype=assignmentype)
        # Create associated Evalassignment
        # This could be in a new function to separate shuffling from assignment
        log = tasks.create_evalassignment(assignmentype.title)
        logger.info(log)
        return redirect('/detail_assignmentype/%s/' % assignmentype_pk)
    else:
        # TODO return error message
        return redirect('gradapp:index')


@login_required
@login_prof
def list_assignmentypes_running(request):
    """
    List all running (archived=False) assignmentype
    """
    prof = request.user.prof
    context = {'type_assignmentype': 'running', 'prof': prof}
    context['list_assignmentypes'] = Assignmentype.objects.\
        filter(archived=False, prof=prof).order_by('deadline_submission')
    return render(request, 'gradapp/list_assignmentype.html',
                  context)


@login_required
@login_prof
def list_assignmentypes_archived(request):
    """
    List all archived assignmentype
    """
    prof = request.user.prof
    context = {'type_assignmentype': 'archived', 'prof': prof}
    context['list_assignmentypes'] = Assignmentype.objects.\
        filter(archived=True, prof=prof)
    return render(request, 'gradapp/list_assignmentype.html',
                  context)


@login_required
@login_prof
def detail_assignmentype(request, pk):
    """
    Dashboard of an assignmentype (id=pk)
    """
    prof = request.user.prof
    context = {'prof': prof}
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    assignments = assignmentype.assignment_set.\
        annotate(std=StdDev('evalassignment__grade_assignment'),
                 mean=Avg('evalassignment__grade_assignment'))
    if assignmentype:
        context['assignmentype'] = assignmentype
        context['assignments'] = assignments
        context['range_grades'] = range(assignmentype.nb_grading)
        return render(request, 'gradapp/detail_assignmentype.html',
                      context)
    else:
        return redirect('gradapp:list_assignmentypes_running')


@login_required
@login_prof
def show_eval_distrib(request, pk):
    prof = request.user.prof
    context = {'prof': prof}
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    if assignmentype:
        context['assignmentype'] = assignmentype
        context['stat_questions'] = []
        for question in range(1, assignmentype.nb_questions + 1):
            questions_stat = [Evalquestion.objects.filter(
                question=question, grade=igrade,
                evalassignment__assignment__assignmentype=assignmentype).count()
                              for igrade in range(3)]
            try:
                questions_stat = [100. * i / sum(questions_stat)
                                  for i in questions_stat]
            except ZeroDivisionError:
                questions_stat = [0, 0, 0]
            context['stat_questions'].append([question, questions_stat])
        return render(request, 'gradapp/plot_assignmentype.html',
                      context)
    else:
        return redirect('gradapp:list_assignmentypes_running')


@login_required
@login_prof
def coeff_assignmentype(request, pk):
    """
    Set up coefficients of an assignmentype (id=pk)
    """
    prof = request.user.prof
    context = {'prof': prof}
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    if assignmentype:
        nb_questions = assignmentype.nb_questions
        if request.method == 'POST':
            form = CoeffForm(request.POST,
                             nb_questions=nb_questions)
            if form.is_valid():
                assignmentype.questions_coeff = [form.cleaned_data['coeff_%s'
                                                                   % i] for i
                                                 in range(1, assignmentype.
                                                          nb_questions + 1)]
                assignmentype.save()
                # Compute all grades
                log = tasks.compute_grades_assignmentype(assignmentype.id)
                logger.error(log)
                return redirect('/detail_assignmentype/%s/' % pk)
        else:
            questions_coeff = assignmentype.questions_coeff
            coeff = {}
            if questions_coeff:
                for i in range(1, nb_questions + 1):
                    coeff['coeff_%s' % i] = assignmentype.questions_coeff[i - 1]
            else:
                coeff = dict.fromkeys(['coeff_%s' % i
                                       for i in range(1, nb_questions + 1)],
                                      None)
            form = CoeffForm(nb_questions=nb_questions,
                             initial=coeff)
        context['form'] = form
        context['assignmentype'] = assignmentype
        return render(request, 'gradapp/coeff_assignmentype.html',
                      context)
    return redirect('gradapp:list_assignmentypes_running')


@login_required
@login_prof
def generate_csv_grades(request, pk):
    prof = request.user.prof
    assignmentype = Assignmentype.objects.filter(pk=pk, prof=prof).first()
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="grades.csv"'
    writer = csv.writer(response)
    # write coefficients as 1st row
    writer.writerow(['Coeff:'] + assignmentype.questions_coeff)
    # write global mean and std
    grade_stat = assignmentype.assignment_set.\
        aggregate(std=StdDev('evalassignment__grade_assignment'),
                  mean=Avg('evalassignment__grade_assignment'))
    writer.writerow(list(grade_stat.items()))
    # write column names
    col_names = ['Name', 'Mean']
    l = [['R%sName' % i_rev, 'R%sGrade' % i_rev] +
         ['R%sQ%s' % (i_rev, i_ques)
          for i_ques in range(1, 1 + assignmentype.nb_questions)] +
         ['R%sFeedback' % i_rev]
         for i_rev in range(1, 1 + assignmentype.nb_grading)] +\
        [['SuperGrader', 'SuperGrade']] +\
        [['SuperGradeQ%s' % i_ques]
         for i_ques in range(1, 1 + assignmentype.nb_questions)]
    writer.writerow(col_names + [item for sublist in l for item in sublist])
    if assignmentype:
        for assignment in assignmentype.assignment_set.all():
            list_as = [assignment.student.user.username]
            if assignment.get_super_eval():
                mean_grade = assignment.get_super_eval().grade_assignment
            else:
                mean_grade = assignment.evalassignment_set.\
                    aggregate(Avg('grade_assignment'))['grade_assignment__avg']
            list_as.append(mean_grade)
            for evaluation in assignment.get_normal_eval():
                list_grades = [eq.grade for eq in evaluation.
                               order_question_set()]
                list_evaluation = [evaluation.evaluator.username,
                                   evaluation.grade_assignment] + list_grades +\
                                  [evaluation.grade_evaluation]
                list_as.extend(list_evaluation)
            supereval = assignment.get_super_eval()
            if supereval:
                list_supereval = [supereval.evaluator.username,
                                  supereval.grade_assignment] +\
                                 [eq.grade
                                  for eq in supereval.order_question_set()]
            else:
                list_supereval = [None] * (assignmentype.nb_questions + 2)
            list_as.extend(list_supereval)
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
        # writer.writerow([evalassignment.grade_assignment_comments])
        for evalquestion in evalassignment.evalquestion_set.all().\
                order_by('question'):
            writer.writerow(['****************************************'])
            writer.writerow(['****************************************'])
            writer.writerow(['Question %s' % evalquestion.question,
                             ' Grade %s' % evalquestion.grade])
            writer.writerow(['****************************************'])
            writer.writerow([evalquestion.comments])
    else:
        writer.writerow(['Oups... you might not be allowed to see this'])
    return response


@login_required
@login_prof
def generate_zip_assignments(request, pk):
    prof = request.user.prof
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
            if assignment:
                new_filename = '{0}_{1}.{2}'.format(dir_name,
                                                    assignment.student.user.
                                                    username,
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
@login_student
def get_assignment(request, pk):
    student = request.user.student
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

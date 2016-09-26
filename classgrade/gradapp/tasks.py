from random import shuffle
from gradapp.models import Assignmentype, Evalassignment


def create_evalassignment(assignmentype_title):
    """
    Create gradapp.models.evalassignment for a assignmentype (given its title)
    """
    try:
        assignmentype = Assignmentype.objects.\
            filter(title=assignmentype_title).first()
        nb_grading = assignmentype.nb_grading
        assignments = [a for a in assignmentype.assignment_set.all()]
        shuffle(assignments)
        nb_assignments = len(assignments)
        for i, assignment in enumerate(assignments):
            for igrade in range(nb_grading):
                to_be_evaluated = assignments[(i + 1 + igrade) % nb_assignments]
                Evalassignment.objects.create(assignment=to_be_evaluated,
                                              evaluator=assignment.student)
        return 'Evalassignments create for assignment %s' % assignmentype_title
    except Exception as e:
        return 'Oups... ' + str(e)

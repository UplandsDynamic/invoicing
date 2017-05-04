import logging
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from django_q.tasks import schedule, Schedule
from invoicing.models import Units
from invoicing import views as invoicing_view
from invoicing.models import Invoice

# note: now = timezone.now()

# Get an instance of a logger
logger = logging.getLogger(__name__)


def recurring_invoice_scheduler(instance=None):
        # see if recurring schedule already exists for this invoice
        try:
            existing_schedule = Schedule.objects.get(kwargs="{'args': '%s'}" % (instance.invoice_number))
            already_exists = True
        except Schedule.DoesNotExist:
            already_exists = False
        # set schedule
        try:
            # first, if recurring set to no but a schedule exists, stop the thing (delete the schedule)
            if int(instance.recurring) == Invoice.RECURRING[0][0]:
                if already_exists:
                    existing_schedule.delete()
                    return True
                else:
                    return None
            if not already_exists:
                # if daily
                if int(instance.recurring) == Invoice.RECURRING[1][0]:
                    period = Schedule.DAILY
                    first_run = timezone.now() + relativedelta(days=1)
                # if monthly
                elif int(instance.recurring) == Invoice.RECURRING[2][0]:
                    period = Schedule.MONTHLY
                    first_run = timezone.now() + relativedelta(months=1)
                # if annual
                elif int(instance.recurring) == Invoice.RECURRING[3][0]:
                    period = Schedule.YEARLY
                    first_run = timezone.now() + relativedelta(years=1)
                else:
                    return None
                schedule(
                    func='invoicing.schedules.generate_child_invoice',
                    args=instance.invoice_number,
                    hook='invoicing.schedules.generate_child_invoice_hook',
                    schedule_type=period,
                    minutes=30,
                    repeats=-1,  # -1 = carry on indefinitely
                    next_run=first_run
                )
        except ValueError:
            pass
        return None


def generate_child_invoice(**kwargs):
    """
    function to generate a new child invoice based upon the parent
    """
    try:
        parent = Invoice.objects.get(invoice_number=kwargs['args'])  # invoice instance
        child = Invoice()
        child.client = parent.client
        child.tax = parent.tax
        child.discount_rate = parent.discount_rate
        child.issued_by = parent.issued_by
        child.invoice_status = Invoice.INVOICE_STATUS[1][0]
        child.recurring = Invoice.RECURRING[0][0]
        child.parent_invoice = parent
        child.date_due = timezone.now().date()
        child.save()
        # save the new m2m intermediary model
        parent_units = Units.objects.filter(invoice=parent)
        for item in parent_units.iterator():
            new = Units()
            new.invoice = child
            new.item = item.item
            new.quantity = item.quantity
            new.save()
        # generate pdf and send email (note: email=False, as already being dispatched due to creation of new PDF)
        invoicing_view.pdf_gen_or_fetch_or_email(invoice_number=child.invoice_number,
                                                 type=invoicing_view.PDF_TYPES.get('invoice'),
                                                 email=False,
                                                 regenerate=False)
        return True
    except Invoice.DoesNotExist:
        return None


def generate_child_invoice_hook(task):
    if task.success and task.result:
        print('Success! A new child invoice has been issued!!')
    else:
        print('Issuing child invoice failed!')

from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save
from invoicing.models import *
from haystack.management.commands import update_index
from django.utils import timezone
import invoicing.views as invoicing
from invoicing import schedules
from django.forms import ValidationError
from django.utils.translation import ugettext_lazy as _

"""
Note: if doing a save in post_save ensure signal is disconnected to avoid an infinite loop of saving:

    e.g.:

    post_save.disconnect(my_method, sender=sender)
    instance.save()
    post_save.connect(my_method, sender=Invoice)
"""


@receiver(post_save, sender=Invoice)
def invoice_post_save(sender, instance, created, **kwargs):
    """
    post save receiver for Invoice model
    """
    save_updated = False
    post_save.disconnect(invoice_post_save, sender=sender)
    if created:
        invoice_id = model_functions.generate_invoice_random_id()  # generate random id
        instance.invoice_number = '{}-{}'.format(invoice_id, instance.id)
        save_updated = True
    # recurring invoice stuff
    if not getattr(instance, 'save_pdf', False):  # if save not being called again just to update DB after gen of PDF
        # set the invoice as start/stop recurring
        recurring(instance=instance)
    # dispatch email if client email notifications set to true and the save is being called when saving a new PDF
    if instance.client.email_notifications and getattr(instance, 'save_pdf', False):
        if instance.invoice_status == Invoice.INVOICE_STATUS[5][0]:  # receipt (paid in full)
            # send email
            if not getattr(instance, 'receipt_emailed', False):  # if hasn't already been sent
                invoicing.pdf_gen_or_fetch_or_email(invoice_number=instance.invoice_number,
                                                    type=invoicing.PDF_TYPES.get('receipt'),
                                                    email=True, regenerate=False)
                # mark as sent
                setattr(instance, 'receipt_emailed', True)
                save_updated = True
        elif instance.invoice_status == Invoice.INVOICE_STATUS[1][0]:  # invoice (unpaid)
            # send email
            if not getattr(instance, 'invoice_emailed', False):  # if hasn't already been sent
                invoicing.pdf_gen_or_fetch_or_email(invoice_number=instance.invoice_number,
                                                    type=invoicing.PDF_TYPES.get('invoice'),
                                                    email=True, regenerate=False)
                # mark as sent
                setattr(instance, 'invoice_emailed', True)
                # change status from issued to sent
                setattr(instance, 'invoice_status', Invoice.INVOICE_STATUS[2][0])
                save_updated = True
        elif instance.invoice_status == Invoice.INVOICE_STATUS[4][0]:  # invoice (partially paid)
            # send email
            invoicing.pdf_gen_or_fetch_or_email(invoice_number=instance.invoice_number,
                                                type=invoicing.PDF_TYPES.get('invoice_update'), email=True)
    # save the instance if something's been called ...
    if save_updated:
        # disable pre_save signal, as not required to be run again for the second save!
        pre_save.disconnect(invoice_pre_save, sender=Invoice)
        # save the instance
        instance.save()
        # re-enable pre_save signal
        pre_save.connect(invoice_pre_save, sender=Invoice)
    # re-enable post_save signal
    post_save.connect(invoice_post_save, sender=Invoice)


@receiver(pre_save, sender=Invoice)
def invoice_pre_save(sender, instance, **kwargs):
    """
    Also to populate mark_as_paid field with datetime when a status is changed to 'PAID_IN_FULL'
    Also populates the "amount_paid" field with total.
    Also updates the invoice status to partially paid when an amount is paid
    """
    try:  # existing invoice to be modified
        inv = Invoice.objects.get(invoice_number=instance.invoice_number)
    except Invoice.DoesNotExist:  # new invoice
        inv = Invoice()  # generate an empty reference Invoice instance if no existing (i.e. A NEW INVOICE)
    # IF NOT SAVING PDF (Most stuff goes in here!)
    if not getattr(instance, 'save_pdf',
                   False):  # avoid running this pre_save if 'save_pdf' param added to instance
        # PRE-SAVE AMENDMENT STUFF
        instance_dict = invoicing.invoice_instance_to_dict(instance)  # get instance as dict + sums
        # if invoice issued, save the time
        if getattr(instance, 'invoice_status') in dict(Invoice.INVOICE_STATUS[1:6]) and \
                not getattr(inv, 'datetime_issued'):
            setattr(instance, 'datetime_issued', timezone.now())
        # ensure invoice_status is upper case
        setattr(instance, 'invoice_status', instance.invoice_status.upper())
        # # enter marked_as_paid datetime into database if status changed to marked as paid
        if instance.invoice_status == Invoice.INVOICE_STATUS[5][0]:
            if not inv.marked_as_paid:  # if not originally marked as paid
                instance.marked_as_paid = timezone.now()  # set as marked as paid
            # set paid_amount to total owed if status is set to paid in full
            instance.paid_amount = Decimal(instance_dict.get('Total after tax'))
        # change status if paid_amount is submitted
        if inv.paid_amount or instance.paid_amount:
            # if total paid >= total owed, set status to paid in full
            if inv.paid_amount >= Decimal(instance_dict.get('Total after tax')) or instance.paid_amount >= \
                    Decimal(instance_dict.get('Total after tax')):
                instance.invoice_status = Invoice.INVOICE_STATUS[5][0]
                # enter marked_as_paid datetime into database
                instance.marked_as_paid = timezone.now()
            else:  # else set status to partially paid
                instance.invoice_status = Invoice.INVOICE_STATUS[4][0]
        # check for overdue status todo: move this to an automated django-q later
        date_due = getattr(instance, 'date_due', None) or getattr(inv, 'date_due')
        if date_due < timezone.now().date() and \
                        instance.invoice_status in dict(Invoice.INVOICE_STATUS[:5]):
            instance.overdue = True  # set overdue to True if date_due < now
        else:
            instance.overdue = False  # ensure set back to False if paid
            # todo: new feature - if amount paid exceeds amount owed, store client credit note ...


@receiver(post_save, sender=Account)
def change_uploaded_file_permissions(sender, instance, **kwargs):
    """
    Changes the file permissions of uploaded media files to something sensible
    """
    if getattr(instance, 'logo', False):
        os.chmod('{}'.format(instance.logo.file.name), 0o664)


@receiver(post_save)  # don't specify sender, so it is fired on all model saves
def update_search_index(sender, instance, created, **kwargs):
    """
    receiver to update the search index whenever a model is saved
    """
    watched_models = [Invoice, Account]
    # if sender in watched but do NOT trigger when saving the model when saving PDF (no point)
    if sender in watched_models and not getattr(instance, 'save_pdf', False):
        update_index.Command().handle(interactive=False)


def recurring(instance=None):
    """
    Function to handle the creation of child invoices
    """
    if instance.invoice_number:
        # ensure child recurring invoice does not produce its own child
        if int(getattr(instance, 'recurring', False)) not in dict(Invoice.RECURRING[:1]) and getattr(instance,
                                                                                                'parent_invoice',
                                                                                                False):
            raise ValidationError(_('A child invoice cannot itself be recurring'))
        # ensure invoice is not its own parent
        try:
            if getattr(instance, 'invoice_number', False) == getattr(instance, 'parent_invoice', False).invoice_number:
                raise ValidationError(_('An invoice cannot be it\'s own parent ... stop messing around!'))
        except AttributeError:
            pass  # thrown if no invoice_number for parent, so can discard as if no parent, no worries!
        # if status >= ISSUED, call the scheduler to start/stop recurring
        if getattr(instance, 'invoice_status', False) in dict(Invoice.INVOICE_STATUS[1:]):
            schedules.recurring_invoice_scheduler(instance=instance)
            return True
    return None

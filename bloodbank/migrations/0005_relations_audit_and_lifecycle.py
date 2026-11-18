"""
Structural clean-up:

1. Data repair (runs first, on the old text-ID schema):
   - hash any plain-text passwords
   - create parent records that existing rows point to but that do not exist
     (e.g. inventory units whose donation was never recorded), so every
     reference is valid before foreign keys are enforced
   - mark units that already have a disposal record as Discarded
2. Remove the unused System_Admin and Hospital_Admin tables (User covers both).
3. Give every model the inherited UpdatedAt audit field.
4. Turn text ID references into real foreign keys, keeping the same columns.
"""

from datetime import timedelta

import django.db.models.deletion
from django.contrib.auth.hashers import identify_hasher, make_password
from django.db import migrations, models
from django.utils import timezone


BLOOD_GROUPS = [('O+', 'O+'), ('O-', 'O-'), ('A+', 'A+'), ('A-', 'A-'),
                ('B+', 'B+'), ('B-', 'B-'), ('AB+', 'AB+'), ('AB-', 'AB-')]
PLACEHOLDER_PHONE = '0000000000'


def _is_hashed(value):
    try:
        identify_hasher(value)
        return True
    except (ValueError, TypeError):
        return False


def repair_data(apps, schema_editor):
    User = apps.get_model('bloodbank', 'User')
    Donor = apps.get_model('bloodbank', 'Donor')
    Patient = apps.get_model('bloodbank', 'Patient')
    Donation = apps.get_model('bloodbank', 'Donation')
    Inventory = apps.get_model('bloodbank', 'Inventory')
    BloodRequest = apps.get_model('bloodbank', 'BloodRequest')
    Verification = apps.get_model('bloodbank', 'Verification')
    Disposal = apps.get_model('bloodbank', 'Disposal')

    # Passwords: never keep plain text
    for user in User.objects.all():
        if user.Password and not _is_hashed(user.Password):
            user.Password = make_password(user.Password)
            user.save(update_fields=['Password'])

    def ensure_donor(donor_id, blood_group='O+'):
        if donor_id and not Donor.objects.filter(DonorID=donor_id).exists():
            Donor.objects.create(
                DonorID=donor_id, Name=f"Unregistered donor {donor_id}",
                BloodGroup=blood_group, Phone=PLACEHOLDER_PHONE, Status='Not Eligible',
            )

    def ensure_donation(donation_id, donor_id, blood_group, comp_type, qty, bank_id, when):
        if not Donation.objects.filter(DonationID=donation_id).exists():
            Donation.objects.create(
                DonationID=donation_id, DonorID=donor_id, Date=when,
                BloodGroup=blood_group, Type=comp_type, Quantity=qty,
                BloodBankID=bank_id, Status='Processed',
            )

    # Donors referenced anywhere
    for row in Donation.objects.all():
        ensure_donor(row.DonorID, row.BloodGroup)
    for row in Inventory.objects.all():
        ensure_donor(row.DonorID, row.BloodGroup)
    for row in Verification.objects.all():
        ensure_donor(row.DonorID)

    # Donations referenced by stored units (shelf life: blood ~35 days, plasma ~1 year)
    today = timezone.now().date()
    for unit in Inventory.objects.all():
        shelf = 365 if unit.Type == 'Plasma' else 35
        collected = min(unit.ExpiryDate - timedelta(days=shelf), today)
        ensure_donation(unit.DonationID, unit.DonorID, unit.BloodGroup, unit.Type,
                        unit.Quantity, unit.BloodBankID, collected)

    # Units referenced by screening or disposal records
    def ensure_unit(unit_id, donor_id, when):
        if Inventory.objects.filter(UnitID=unit_id).exists():
            return
        donor_id = donor_id or 'D-UNKNOWN'
        ensure_donor(donor_id)
        donation_id = f"MIG-{unit_id}"[:20]
        ensure_donation(donation_id, donor_id, 'O+', 'Blood', 1, 1, when)
        Inventory.objects.create(
            UnitID=unit_id, DonationID=donation_id, DonorID=donor_id, BloodBankID=1,
            BloodGroup='O+', Type='Blood', Quantity=1, BatchNo='MIGRATED',
            ExpiryDate=when, Status='Discarded',
        )

    for v in Verification.objects.all():
        ensure_unit(v.UnitID, v.DonorID, v.Date)
    for d in Disposal.objects.all():
        ensure_unit(d.UnitID, None, d.DisposalDate)

    # Patients referenced by requests
    for r in BloodRequest.objects.all():
        if not Patient.objects.filter(PatientID=r.PatientID).exists():
            Patient.objects.create(
                PatientID=r.PatientID, Name=f"Unregistered patient {r.PatientID}",
                HospitalID=r.HospitalID, BloodGroup=r.BloodGroup, Type=r.Type,
                Urgency=r.Urgency, Contact=PLACEHOLDER_PHONE,
            )

    # A disposed unit is out of use
    disposed_ids = Disposal.objects.values_list('UnitID', flat=True)
    Inventory.objects.filter(UnitID__in=list(disposed_ids)).exclude(Status='Issued').update(Status='Discarded')


def _fk(model, column, related_name):
    return models.ForeignKey(
        db_column=column, on_delete=django.db.models.deletion.PROTECT,
        related_name=related_name, to=f'bloodbank.{model}',
    )


class Migration(migrations.Migration):

    dependencies = [
        ('bloodbank', '0004_user_status'),
    ]

    operations = [
        migrations.RunPython(repair_data, migrations.RunPython.noop),

        migrations.DeleteModel(name='System_Admin'),
        migrations.DeleteModel(name='Hospital_Admin'),

        # Inherited audit field on every model
        *[
            migrations.AddField(
                model_name=name, name='UpdatedAt',
                field=models.DateTimeField(auto_now=True, default=timezone.now),
                preserve_default=False,
            )
            for name in ('user', 'donation', 'verification', 'disposal')
        ],

        # Lifecycle and shared choice lists
        migrations.AlterField(
            model_name='inventory', name='Status',
            field=models.CharField(choices=[('Available', 'Available'), ('Reserved', 'Reserved'), ('Issued', 'Issued'), ('Expired', 'Expired'), ('Discarded', 'Discarded')], default='Available', max_length=20),
        ),
        migrations.AlterField(
            model_name='inventory', name='BloodGroup',
            field=models.CharField(choices=BLOOD_GROUPS, max_length=5),
        ),
        migrations.AlterField(
            model_name='bloodrequest', name='BloodGroup',
            field=models.CharField(choices=BLOOD_GROUPS, max_length=5),
        ),

        # Text IDs -> foreign keys (same database columns)
        migrations.RenameField(model_name='bloodrequest', old_name='PatientID', new_name='patient'),
        migrations.AlterField(model_name='bloodrequest', name='patient', field=_fk('patient', 'PatientID', 'requests')),

        migrations.RenameField(model_name='donation', old_name='DonorID', new_name='donor'),
        migrations.AlterField(model_name='donation', name='donor', field=_fk('donor', 'DonorID', 'donations')),

        migrations.RenameField(model_name='inventory', old_name='DonationID', new_name='donation'),
        migrations.AlterField(model_name='inventory', name='donation', field=_fk('donation', 'DonationID', 'units')),
        migrations.RenameField(model_name='inventory', old_name='DonorID', new_name='donor'),
        migrations.AlterField(model_name='inventory', name='donor', field=_fk('donor', 'DonorID', 'units')),

        migrations.RenameField(model_name='verification', old_name='UnitID', new_name='unit'),
        migrations.AlterField(model_name='verification', name='unit', field=_fk('inventory', 'UnitID', 'verifications')),
        migrations.RenameField(model_name='verification', old_name='DonorID', new_name='donor'),
        migrations.AlterField(model_name='verification', name='donor', field=_fk('donor', 'DonorID', 'verifications')),

        migrations.RenameField(model_name='disposal', old_name='UnitID', new_name='unit'),
        migrations.AlterField(model_name='disposal', name='unit', field=_fk('inventory', 'UnitID', 'disposals')),
    ]

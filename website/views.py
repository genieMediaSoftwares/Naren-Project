from datetime import datetime
import hashlib

from django.conf import settings
from django.core.mail import send_mail
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render

from .forms import AppointmentForm
from .models import BlogPost, ContactMessage, DoctorProfile, PatientBooking, Service



def home(request):
    return render(request, 'home.html', {'home': home})


def about(request):
    return render(request, 'about.html')


def services(request):
    services = Service.objects.all()
    return render(request, 'services.html', {'services': services})


def doctors(request):
    return render(request, 'doctors.html')


def gallery(request):
    return render(request, 'gallery.html')

def contact(request):

    if request.method == 'POST':

        contact = ContactMessage.objects.create(

            name=request.POST.get('name'),

            phone=request.POST.get('phone'),

            email=request.POST.get('email'),

            message=request.POST.get('message'),
        )

        # SEND EMAIL
        send_mail(
            subject='New Contact Form Submission',

            message=f'''
New Appointment Request

Name: {contact.name}

Phone: {contact.phone}

Email: {contact.email}

Message:
{contact.message}
            ''',

            from_email=settings.EMAIL_HOST_USER,

            recipient_list=['narenultrasound@gmail.com'],

            fail_silently=False,
        )

        return redirect('contact_success')

    return render(request, 'contact.html')

def contact_success(request):
    return render(request, 'contact_success.html')


def booked_slots_api(request):
    """Return JSON list of booked, non-cancelled appointment time slots for a given date."""
    date_str = request.GET.get('date', '').strip()
    if not date_str:
        return JsonResponse({'booked_slots': []})

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Expected YYYY-MM-DD.'}, status=400)

    booked_slots = list(
        PatientBooking.objects.filter(
            preferred_date=query_date,
            is_cancelled=False
        ).values_list('preferred_time', flat=True).distinct()
    )
    return JsonResponse({'booked_slots': booked_slots})


def appointment_success(request):
    return render(request, 'appointment_success.html')

def patient_info(request):

    if request.method == "POST":

        all_selected_scans = (
            request.POST.getlist('scan_antenatal') +
            request.POST.getlist('scan_routine') +
            request.POST.getlist('scan_paediatric') +
            request.POST.getlist('scan_doppler') +
            request.POST.getlist('scan_usg_guided') +
            request.POST.getlist('scan_usg_small')
        )
        form_context = {
            'form_data': request.POST,
            'selected_scans': all_selected_scans,
        }

        # 1. Personal Information Validation (Mandatory)
        full_name = request.POST.get('full_name', '').strip()
        if not full_name:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please enter your Full Name.'})

        age_val = request.POST.get('age', '').strip()
        if not age_val:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please enter your Age.'})
        try:
            age = int(age_val)
        except ValueError:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please enter a valid numeric Age.'})

        gender = request.POST.get('gender', '').strip()
        if not gender:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please select your Gender.'})

        phone = request.POST.get('phone', '').strip()
        if not phone:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please enter your Mobile Number.'})

        # 2. Appointment Preference Validation (Mandatory)
        preferred_date_raw = request.POST.get('preferred_date', '').strip()
        if not preferred_date_raw:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please select a Preferred Date.'})

        try:
            preferred_date = datetime.strptime(preferred_date_raw, '%Y-%m-%d').date()
        except ValueError:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Invalid date format. Please select a valid appointment date.'}
            )

        preferred_time = request.POST.get('preferred_time', '').strip()
        if not preferred_time:
            return render(request, 'patient_info.html', {**form_context, 'error': 'Please select a Preferred Time Slot.'})

        # 3. Preferred Service / Scan – Mandatory Antenatal Selection
        antenatal_scans = request.POST.getlist('scan_antenatal')
        if not antenatal_scans:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please select at least one scan from Antenatal & Gynecological Scans.'}
            )

        # 4. Confirmation Checkbox Validation (Mandatory)
        confirmation = request.POST.get('confirmation')
        if not confirmation:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please confirm that the above information is correct.'}
            )

        # Optional Medical Information
        referred_doctor = request.POST.get('referred_doctor', '').strip()
        hospital_name = request.POST.get('hospital_name', '').strip()

        # Collect scans by category
        scan_categories = [
            ('1. ANTENATAL & GYNECOLOGICAL SCANS', antenatal_scans),
            ('2. ROUTINE SCANS', request.POST.getlist('scan_routine')),
            ('3. PAEDIATRIC SCANS', request.POST.getlist('scan_paediatric')),
            ('4. DOPPLER SCANS', request.POST.getlist('scan_doppler')),
            ('5. USG GUIDED PROCEDURES', request.POST.getlist('scan_usg_guided')),
            ('6. USG SMALL PARTS', request.POST.getlist('scan_usg_small')),
        ]

        # Build formatted services text for DB storage and notification
        category_blocks = []
        for category_name, selected in scan_categories:
            if selected:
                block_lines = [category_name]
                for scan in selected:
                    block_lines.append(f"- {scan}")
                category_blocks.append("\n".join(block_lines))

        services_text = "\n\n".join(category_blocks).strip()

        # Database-level concurrency lock & duplicate check
        with transaction.atomic():
            if connection.vendor == 'postgresql':
                with connection.cursor() as cursor:
                    slot_key = f"{preferred_date}_{preferred_time}"
                    lock_id = int(hashlib.md5(slot_key.encode('utf-8')).hexdigest()[:15], 16)
                    cursor.execute("SELECT pg_advisory_xact_lock(%s);", [lock_id])

            if PatientBooking.objects.filter(
                preferred_date=preferred_date,
                preferred_time=preferred_time,
                is_cancelled=False
            ).exists():
                return render(
                    request,
                    'patient_info.html',
                    {
                        **form_context,
                        'error': f'The time slot "{preferred_time}" on {preferred_date} is already booked. Please choose another time slot.'
                    }
                )

            booking = PatientBooking.objects.create(

                full_name=full_name,

                age=age,

                gender=gender,

                phone=phone,

                referred_doctor=referred_doctor or None,

                hospital_name=hospital_name or None,

                ldd_date=request.POST.get('ldd_date') or None,

                preferred_date=preferred_date,

                preferred_time=preferred_time,

                services=services_text,

                is_cancelled=False,

                message=request.POST.get('message'),

            )

        subject = "New Patient Appointment Booking"

        scan_section = f"\n\n{services_text}" if services_text else "\nNone selected"

        message = f"""NEW PATIENT APPOINTMENT

PERSONAL INFORMATION
Full Name: {booking.full_name}
Age: {booking.age}
Gender: {booking.gender}
Mobile Number: {booking.phone}

MEDICAL INFORMATION
Referred Doctor: {booking.referred_doctor or 'N/A'}
Hospital / Clinic: {booking.hospital_name or 'N/A'}

APPOINTMENT PREFERENCE
Preferred Date: {booking.preferred_date}
Preferred Time: {booking.preferred_time}

SELECTED SERVICES / SCANS{scan_section}
"""

        send_mail(

            subject,

            message,

            settings.EMAIL_HOST_USER,

            ['narenultrasound@gmail.com'],

            fail_silently=False,

        )

        return redirect('appointment_success')

    return render(request, 'patient_info.html')

from django.http import HttpResponse


def robots_txt(request):

    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        "Sitemap: https://narenultrasound.in/sitemap.xml",
    ]

    return HttpResponse(
        "\n".join(lines),
        content_type="text/plain"
    )

def sitemap_index(request):

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>

<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">

<sitemap>
<loc>https://narenultrasound.in/pages.xml</loc>
</sitemap>

<sitemap>
<loc>https://narenultrasound.in/services.xml</loc>
</sitemap>

</sitemapindex>
"""

    return HttpResponse(
        xml,
        content_type="application/xml"
    )


def blog_list(request):

    posts = BlogPost.objects.filter(
        is_published=True
    ).order_by('-created_at')

    print("POST COUNT:", posts.count())

    return render(
        request,
        'blog_list.html',
        {
            'posts': posts
        }
    )


def blog_detail(request, slug):

    post = BlogPost.objects.get(
        slug=slug,
        is_published=True
    )

    return render(
        request,
        'blog_detail.html',
        {
            'post': post,

            # Site-wide doctor card appended to every post. None when the
            # client has not configured one yet - the template skips it.
            'doctor': DoctorProfile.get_active(),
        }
    )
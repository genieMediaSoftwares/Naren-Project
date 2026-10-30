from django.shortcuts import render, redirect
from .models import Service, PatientBooking, ContactMessage, BlogPost, DoctorProfile
from .forms import AppointmentForm
from django.core.mail import send_mail
from django.conf import settings



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


def appointment_success(request):
    return render(request, 'appointment_success.html')

def patient_info(request):

    if request.method == "POST":

        required_fields = [

            'full_name',

            'age',

            'gender',

            'phone',

            'preferred_date',

            'preferred_time'

        ]

        for field in required_fields:

            if not request.POST.get(field):

                return render(

                    request,

                    'patient_info.html',

                    {

                        'error': 'Please fill all required fields.'

                    }

                )

        # Collect scans by category
        scan_categories = [
            ('1. ANTENATAL & GYNECOLOGICAL SCANS', request.POST.getlist('scan_antenatal')),
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

        booking = PatientBooking.objects.create(

            full_name=request.POST.get('full_name'),

            age=int(request.POST.get('age')) if request.POST.get('age') else None,

            gender=request.POST.get('gender'),

            phone=request.POST.get('phone'),

            referred_doctor=request.POST.get('referred_doctor'),

            hospital_name=request.POST.get('hospital_name'),

            ldd_date=request.POST.get('ldd_date') or None,

            preferred_date=request.POST.get('preferred_date'),

            preferred_time=request.POST.get('preferred_time'),

            services=services_text,

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
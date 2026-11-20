
from datetime import datetime
import hashlib

from django.conf import settings
from django.core.mail import send_mail
from django.db import connection, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import AppointmentForm
from .models import BlogPost, ContactMessage, DoctorProfile, PatientBooking, Service
from .seo import ORIGIN, SERVICE_GUIDES, related_article_slugs
from .slots import (
    APPOINTMENT_TIME_SLOTS,
    get_clinic_now,
    get_past_slots_for_date,
    get_slot_db_variants,
    is_clinic_closed_day,
    normalize_booked_slots,
    validate_appointment_date_and_slot,
)
from .whatsapp import (
    get_contact_whatsapp_url,
    get_patient_booking_whatsapp_url,
)

def home(request):
    return render(request, 'home.html', {'home': home})


def about(request):
    return render(request, 'about.html')


def services(request):
    services = Service.objects.all()
    slugs = {slug for guide in SERVICE_GUIDES for slug in guide['slugs']}
    posts = {post.slug: post for post in BlogPost.objects.filter(is_published=True, slug__in=slugs).only('title', 'slug')}
    guides = [{**guide, 'posts': [posts[slug] for slug in guide['slugs'] if slug in posts]} for guide in SERVICE_GUIDES]
    return render(request, 'services.html', {'services': services, 'service_guides': guides})


def doctors(request):
    return render(request, 'doctors.html')


def gallery(request):
    return render(request, 'gallery.html')


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip() or 'Appointment Booking / Enquiry'
        message_text = request.POST.get('message', '').strip()

        contact = ContactMessage.objects.create(
            name=name,
            phone=phone,
            email=email,
            subject=subject,
            message=message_text,
        )

        # SEND EMAIL
        send_mail(
            subject='New Contact Form Submission',
            message=f'''
New Appointment Request

Name: {contact.name}

Phone: {contact.phone}

Email: {contact.email}

Subject: {contact.subject}

Message:
{contact.message}
            ''',
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=['narenultrasound@gmail.com'],
            fail_silently=False,
        )


        # Store WhatsApp link in session for the confirmation page
        wa_url = get_contact_whatsapp_url(contact, subject=subject)
        request.session['whatsapp_url'] = wa_url

        return redirect('contact_success')

    return render(request, 'contact.html')


def contact_success(request):
    whatsapp_url = request.session.pop('whatsapp_url', None)
    return render(request, 'contact_success.html', {'whatsapp_url': whatsapp_url})


def booked_slots_api(request):
    """Return JSON availability details for a given date in clinic IST."""
    clinic_now = get_clinic_now()
    clinic_today = clinic_now.date()
    date_str = request.GET.get('date', '').strip()

    if not date_str:
        return JsonResponse({
            'booked_slots': [],
            'past_slots': [],
            'unavailable_slots': [],
            'is_closed': False,
            'is_past_date': False,
            'closed_reason': None,
            'clinic_today': clinic_today.isoformat(),
        })

    try:
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse(
            {'error': 'Invalid date format. Expected YYYY-MM-DD.'},
            status=400
        )

    is_past_date = query_date < clinic_today
    is_closed = is_clinic_closed_day(query_date)

    raw_booked = list(
        PatientBooking.objects.filter(
            preferred_date=query_date,
            is_cancelled=False
        ).values_list('preferred_time', flat=True).distinct()
    )
    booked_slots = normalize_booked_slots(raw_booked)
    past_slots = get_past_slots_for_date(query_date, now=clinic_now)

    if is_closed or is_past_date:
        unavailable_slots = list(APPOINTMENT_TIME_SLOTS)
    else:
        unavailable_set = set(booked_slots) | set(past_slots)
        unavailable_slots = [s for s in APPOINTMENT_TIME_SLOTS if s in unavailable_set]

    closed_reason = None
    if is_past_date:
        closed_reason = 'Past dates cannot be booked. Please select today or a future date.'
    elif is_closed:
        closed_reason = (
            'The clinic is closed on Sundays (Holiday). '
            'Please choose Monday to Saturday (8:00 AM - 8:00 PM).'
        )

    return JsonResponse({
        'booked_slots': booked_slots,
        'past_slots': past_slots,
        'unavailable_slots': unavailable_slots,
        'is_closed': is_closed,
        'is_past_date': is_past_date,
        'closed_reason': closed_reason,
        'clinic_today': clinic_today.isoformat(),
    })


def appointment_success(request):
    whatsapp_url = request.session.pop('whatsapp_url', None)
    return render(request, 'appointment_success.html', {'whatsapp_url': whatsapp_url})


def patient_info(request):
    clinic_now = get_clinic_now()
    base_context = {
        'time_slots': APPOINTMENT_TIME_SLOTS,
        'min_booking_date': clinic_now.date().isoformat(),
    }

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
            **base_context,
            'form_data': request.POST,
            'selected_scans': all_selected_scans,
        }

        # 1. Personal Information Validation (Mandatory)
        full_name = request.POST.get('full_name', '').strip()
        if not full_name:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please enter your Full Name.'}
            )

        age_val = request.POST.get('age', '').strip()
        if not age_val:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please enter your Age.'}
            )

        try:
            age = int(age_val)
        except ValueError:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please enter a valid numeric Age.'}
            )

        gender = request.POST.get('gender', '').strip()
        if not gender:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please select your Gender.'}
            )

        phone = request.POST.get('phone', '').strip()
        if not phone:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please enter your Mobile Number.'}
            )

        # 2. Appointment Preference Validation (Mandatory)
        preferred_date_raw = request.POST.get('preferred_date', '').strip()
        if not preferred_date_raw:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please select a Preferred Date.'}
            )

        try:
            preferred_date = datetime.strptime(
                preferred_date_raw, '%Y-%m-%d'
            ).date()
        except ValueError:
            return render(
                request,
                'patient_info.html',
                {
                    **form_context,
                    'error': 'Invalid date format. Please select a valid appointment date.'
                }
            )

        preferred_time = request.POST.get('preferred_time', '').strip()
        if not preferred_time:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': 'Please select a Preferred Time Slot.'}
            )

        slot_error = validate_appointment_date_and_slot(
            preferred_date,
            preferred_time,
            now=clinic_now,
        )
        if slot_error:
            return render(
                request,
                'patient_info.html',
                {**form_context, 'error': slot_error}
            )

        # Collect antenatal scans (optional)
        antenatal_scans = request.POST.getlist('scan_antenatal')

        # 3. Confirmation Checkbox Validation (Mandatory)
        confirmation = request.POST.get('confirmation')
        if not confirmation:
            return render(
                request,
                'patient_info.html',
                {
                    **form_context,
                    'error': 'Please confirm that the above information is correct.'
                }
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
                    lock_id = int(
                        hashlib.md5(slot_key.encode('utf-8')).hexdigest()[:15],
                        16
                    )
                    cursor.execute(
                        "SELECT pg_advisory_xact_lock(%s);",
                        [lock_id]
                    )

            if PatientBooking.objects.filter(
                preferred_date=preferred_date,
                preferred_time__in=get_slot_db_variants(preferred_time),
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

        scan_section = (
            f"\n\n{services_text}" if services_text else "\nNone selected"
        )

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

        # Store WhatsApp link in session for the confirmation page
        wa_url = get_patient_booking_whatsapp_url(booking)
        request.session['whatsapp_url'] = wa_url

        return redirect('appointment_success')

    return render(request, 'patient_info.html', base_context)


def robots_txt(request):
    lines = [
        f"# robots.txt for {ORIGIN}/",
        "#",
        "# All public website pages are open to search engine crawlers,",
        "# including Googlebot, Bingbot, and AI/LLM crawlers",
        "# (GPTBot, OAI-SearchBot, ClaudeBot, PerplexityBot, CCBot).",
        "#",
        "# Public pages include:",
        "# Home, About, Services, Doctor, Gallery, Patient Info,",
        "# Contact Us, and published Blog articles.",
        "#",
        "# Administrative pages are excluded from crawling.",
        "# These rules do not replace authentication or access controls.",
        "",
        "User-agent: *",
        "Allow: /",
        "",
        "# Restrict crawling of Django administration",
        "Disallow: /admin/",
        "",
        "# Official XML sitemap",
        f"Sitemap: {ORIGIN}/sitemap.xml",
        "",
        "# AI/LLM website information",
        f"# {ORIGIN}/llms.txt",
    ]

    return HttpResponse(
        "\n".join(lines) + "\n",
        content_type="text/plain; charset=utf-8"
    )


def llms_txt(request):
    """Public clinic information and current published article links only."""
    return render(
        request,
        'llms.txt',
        {
            'origin': ORIGIN,
            'published_slugs': set(BlogPost.objects.filter(is_published=True).values_list('slug', flat=True)),
        },
        content_type='text/plain; charset=utf-8',
    )


def sitemap_index(request):
    xml = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <sitemap>
        <loc>https://www.narenultrasound.in/pages.xml</loc>
    </sitemap>
    <sitemap>
        <loc>https://www.narenultrasound.in/services.xml</loc>
    </sitemap>
    <sitemap>
        <loc>https://www.narenultrasound.in/posts.xml</loc>
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

    return render(
        request,
        'blog_list.html',
        {
            'posts': posts
        }
    )


def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost,
        slug=slug,
        is_published=True
    )

    canonical_path = reverse('blog_detail', args=[post.slug])
    if request.path != canonical_path:
        query = request.META.get('QUERY_STRING', '')
        target = canonical_path + ('?' + query if query else '')
        return redirect(target, permanent=True, preserve_request=request.method not in ('GET', 'HEAD'))

    featured_image_url = ""
    if post.featured_image:
        img_url = post.featured_image.url
        if img_url.startswith("https://"):
            featured_image_url = img_url
        elif img_url.startswith("http://"):
            featured_image_url = "https://" + img_url[len("http://"):]
        else:
            featured_image_url = f"https://www.narenultrasound.in{img_url}"

    return render(
        request,
        'blog_detail.html',
        {
            'post': post,
            'featured_image_url': featured_image_url,

            # Site-wide doctor card appended to every post. None when the
            # client has not configured one yet - the template skips it.
            'doctor': DoctorProfile.get_active(),
            'related_posts': BlogPost.objects.filter(
                is_published=True, slug__in=related_article_slugs(post.slug),
            ).exclude(pk=post.pk).only('title', 'slug').order_by('title', 'pk')[:4],
        }
    )

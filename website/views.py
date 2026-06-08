from django.shortcuts import render, redirect
from .models import Service, PatientBooking, ContactMessage
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

            services=', '.join(request.POST.getlist('services')),

            message=request.POST.get('message'),

        )

        subject = "New Patient Appointment Booking"

        message = f"""

New patient booking received.

Full Name: {booking.full_name}

Age: {booking.age}

Gender: {booking.gender}

Phone: {booking.phone}

Preferred Date: {booking.preferred_date}

Preferred Time: {booking.preferred_time}

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
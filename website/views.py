from django.shortcuts import render, redirect
from .models import Service, Gallery, PatientBooking
from .forms import AppointmentForm


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
    gallery = Gallery.objects.all()
    return render(request, 'gallery.html', {'gallery': gallery})


def contact(request):

    if request.method == 'POST':

        form = AppointmentForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('appointment_success')

    else:
        form = AppointmentForm()

    return render(request, 'contact.html', {'form': form})


def appointment_success(request):
    return render(request, 'appointment_success.html')

def patient_info(request):

    if request.method == "POST":

        full_name = request.POST.get('full_name')
        phone = request.POST.get('phone')
        email = request.POST.get('email')

        city = request.POST.get('city')
        state = request.POST.get('state')
        pincode = request.POST.get('pincode')

        preferred_date = request.POST.get('preferred_date')
        preferred_time = request.POST.get('preferred_time')

        services = request.POST.getlist('services')

        message = request.POST.get('message')

        PatientBooking.objects.create(

            full_name=full_name,
            phone=phone,
            email=email,

            city=city,
            state=state,
            pincode=pincode,

            preferred_date=preferred_date,
            preferred_time=preferred_time,

            services=", ".join(services),

            message=message

        )

        return redirect('appointment_success')

    return render(request, 'patient_info.html')
from django.shortcuts import render, redirect
from .models import Service, Gallery
from .forms import AppointmentForm


def home(request):
    return render(request, 'home.html')


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
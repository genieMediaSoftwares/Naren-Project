from django.urls import path
from . import views

urlpatterns = [

    path('', views.home, name='home'),

    path('about/', views.about, name='about'),

    path('services/', views.services, name='services'),

    path('doctors/', views.doctors, name='doctors'),

    path('gallery/', views.gallery, name='gallery'),

    path('contact/', views.contact, name='contact'),

    path(
        'appointment-success/',
        views.appointment_success,
        name='appointment_success'
    ),
]
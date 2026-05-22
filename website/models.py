from django.db import models


class Service(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField()
    image = models.ImageField(upload_to='services/')

    def __str__(self):
        return self.title


class Gallery(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='gallery/')

    def __str__(self):
        return self.title


class Appointment(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    email = models.EmailField()
    date = models.DateField()
    message = models.TextField()

    def __str__(self):
        return self.name
    
class PatientBooking(models.Model):

    SERVICE_CHOICES = [
        ('Pregnancy Scans', 'Pregnancy Scans'),
        ('3D / 4D Baby Scan', '3D / 4D Baby Scan'),
        ('Doppler Scans', 'Doppler Scans'),
        ('Abdomen Scan', 'Abdomen Scan'),
        ('Pelvic Scan', 'Pelvic Scan'),
        ('Thyroid Scan', 'Thyroid Scan'),
        ('Kidney & Urinary Scan', 'Kidney & Urinary Scan'),
        ('Breast Ultrasound', 'Breast Ultrasound'),
        ('Interventional Procedures', 'Interventional Procedures'),
        ('Vascular Scan', 'Vascular Scan'),
        ('Scrotal Scan', 'Scrotal Scan'),
        ('Follicular Study', 'Follicular Study'),
    ]

    TIME_SLOTS = [
        ('9:00 AM - 10:00 AM', '9:00 AM - 10:00 AM'),
        ('10:00 AM - 11:00 AM', '10:00 AM - 11:00 AM'),
        ('11:00 AM - 12:00 PM', '11:00 AM - 12:00 PM'),
        ('12:00 PM - 1:00 PM', '12:00 PM - 1:00 PM'),
        ('1:00 PM - 2:00 PM', '1:00 PM - 2:00 PM'),
        ('2:00 PM - 3:00 PM', '2:00 PM - 3:00 PM'),
        ('3:00 PM - 4:00 PM', '3:00 PM - 4:00 PM'),
        ('4:00 PM - 5:00 PM', '4:00 PM - 5:00 PM'),
        ('5:00 PM - 6:00 PM', '5:00 PM - 6:00 PM'),
        ('6:00 PM - 7:00 PM', '6:00 PM - 7:00 PM'),
        ('7:00 PM - 8:00 PM', '7:00 PM - 8:00 PM'),
        ('8:00 PM - 9:00 PM', '8:00 PM - 9:00 PM'),
        ('9:00 PM - 9:30 PM', '9:00 PM - 9:30 PM'),
    ]

    full_name = models.CharField(max_length=200)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)

    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    preferred_date = models.DateField()

    preferred_time = models.CharField(
        max_length=50,
        choices=TIME_SLOTS
    )

    services = models.TextField()

    message = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} - {self.preferred_date}"
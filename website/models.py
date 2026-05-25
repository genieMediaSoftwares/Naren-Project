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

    full_name = models.CharField(max_length=200)

    age = models.IntegerField(null=True, blank=True)

    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True
    )

    phone = models.CharField(max_length=15)

    referred_doctor = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    hospital_name = models.CharField(
        max_length=200,
        null=True,
        blank=True
    )

    ldd_date = models.DateField(
        null=True,
        blank=True
    )

    preferred_date = models.DateField()

    preferred_time = models.CharField(max_length=50)

    services = models.TextField()

    message = models.TextField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.full_name
    
class ContactMessage(models.Model):

    name = models.CharField(max_length=200)

    phone = models.CharField(max_length=15)

    email = models.EmailField()

    subject = models.CharField(max_length=200)

    message = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
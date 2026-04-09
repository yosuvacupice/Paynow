from django.db import models

class UserAccount(models.Model):
    name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=50, blank=True)
    last_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    gender = models.CharField(max_length=20, blank=True)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.email

class ContactMessage(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    message = models.TextField()

from django.db import models

# Create your models here.
class CsvFile(models.Model):
    csv_file = models.FileField(upload_to='../tmp')
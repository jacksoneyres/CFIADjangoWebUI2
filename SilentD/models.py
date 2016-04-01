from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
import datetime
import os


def create_profile(**kwargs):
    """Creates a Profile automatically when User created

    :param kwargs: contains the created signal
    """
    print kwargs
    user = kwargs["instance"]
    if kwargs["created"]:
        profile = Profile(user=user)
        profile.save()

post_save.connect(create_profile, sender=User)


class Profile(models.Model):
    """Extends Django User Profile.

    Certain features of the website check this model access priviledges. Any kind of field can be added to further
    store information on user. Defaults are created whenever a new user is created
    """
    user = models.OneToOneField(User)

    rank_choices = (
        ('Diagnostic', 'Diagnostic'),
        ('Research', 'Research'),
        ('Manager', 'Manager'),
        ('Quality', 'Quality'),
        ('Super', 'Super'),
    )
    rank = models.CharField(max_length=100, choices=rank_choices, default='Diagnostic')
    cfia_access = models.BooleanField(default=False)
    lab_choices = (
        (1, 'St-Johns'),
        (2, 'Dartmouth'),
        (3, 'Charlottetown'),
        (4, 'St-Hyacinthe'),
        (5, 'Longeuil'),
        (6, 'Fallowfield'),
        (7, 'Carling'),
        (8, 'Greater Toronto Area'),
        (9, 'Winnipeg'),
        (10, 'Saskatoon'),
        (11, 'Calgary'),
        (12, 'Lethbridge'),
        (13, 'Burnaby'),
        (14, 'Sidney'),
        (15, 'Other')
    )
    lab = models.CharField(max_length=100, choices=lab_choices, blank=True)

    # Override the __unicode__() method to return out something meaningful!
    def __unicode__(self):

        s = "%s : %s : %s" % (self.user.username, self.rank, self.lab)
        return s


class Base(models.Model):
    """Abstract model defining common fields for files and project models"""
    date = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=200, default=" ")
    description = models.CharField(max_length=200, blank=True)

    # This makes the class abstract and not instantiate a model of BASE
    class Meta:
        abstract = True


class BaseJob(models.Model):
    """Abstract model defining common fields for all web app models"""
    date = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=200, default=" ")
    job_id = models.CharField(max_length=200, blank=True)
    tag = models.CharField(max_length=200, blank=True)
    type = models.CharField(max_length=50, default=False)
    organism = models.CharField(max_length=200, default=False)
    error = models.CharField(max_length=200, blank=True)

    # This makes the class abstract and not instantiate a model of BaseJob
    class Meta:
        abstract = True


def generate_path(self, filename):
    """Function for file uploads,

    Path can only be generated after the model has been created and saved. Every file is uploaded to a unique folder to
    prevent file name collisions rather than allow Django to rename the files itself which it will do

    Args:
        self: Django object model
        filename: Name of the file. Path contains
    """
    object_type = self.__class__.__name__
    path = "documents/Files/tmp"
    today = datetime.datetime.now()
    unique_path = today.strftime("%Y%m%d") + "/" + str(self.id)
    if 'Data' in object_type:
        path = "documents/Files/%s/%s/%s" % (self.user, unique_path, filename)
    elif 'MiSeq' in object_type:
        path = "documents/MiSeq/%s/%s/%s" % (self.user, self.id, filename)
    elif 'MLST' in object_type:
        path = "documents/MLST/%s/%s/%s" % (self.user, self.id, filename)
    elif 'AMR' in object_type:
        path = "documents/AMR/%s/%s/%s" % (self.user, self.id, filename)
    elif 'SNP' in object_type:
        path = "documents/SNP/%s/%s" % (self.id, filename)
    elif 'Galaxy' in object_type:
        path = "documents/TEST/%s/%s" % (self.id, filename)
    return path


class Data(Base):
    """Every uploaded file from File Upload view uses this model"""
    file = models.FileField(upload_to=generate_path, blank=True)
    name = models.CharField(max_length=200, blank=True)
    type = models.CharField(max_length=20, blank=True)


class MiSeq(Base):
    files = models.ManyToManyField(Data)  # List of FastQ (Data) files
    type = models.CharField(max_length=20, blank=True)
    missing = models.BooleanField(default=False)
    run_info = models.BooleanField(default=False)
    sample_sheet = models.BooleanField(default=False)
    run_stats = models.BooleanField(default=False)
    job_id = models.CharField(max_length=20, blank=True)
    assemblies = models.FileField(blank=True)
    reports = models.FileField(blank=True)
    error = models.CharField(max_length=200, blank=True)


class PrimerV(BaseJob):
    result = models.FileField(blank=True)
    forward = models.CharField(max_length=50, default=False)
    reverse = models.CharField(max_length=50, default=False)
    forward_gc = models.CharField(max_length=50, default=False)
    reverse_gc = models.CharField(max_length=50, default=False)
    target = models.CharField(max_length=50, default=False)
    mism = models.CharField(max_length=50, default=False)
    hits = models.CharField(max_length=50, default=False)
    misses = models.FileField(blank=True)


def generate_targetpath(self, filename):
    path = "documents/GeneSeeker/%s/%s/targets/%s" % (self.user, self.id, filename)
    return path


def generate_genomepath(self, filename):
    path = "documents/GeneSeeker/genomes/%s/%s/%s" % (self.user, self.id, filename)
    return path


class GeneS(BaseJob):
    result = models.FileField(blank=True)
    genes = models.CharField(max_length=50, default=False)
    targets = models.FileField(upload_to=generate_targetpath, blank=True)
    cutoff = models.CharField(max_length=50, default=0.8)


class SNP(BaseJob):
    result = models.FileField(blank=True, default=False)
    tree = models.FileField(blank=True, default=False)
    upload = models.FileField(upload_to=generate_path, blank=True)
    snps = models.IntegerField(null=True, blank=True)
    data_id = models.CharField(max_length=100, default=False)


class Project(Base):
    """Projects are a collection of FastQ files for analysis"""
    files = models.ManyToManyField(Data)  # List of FastQ (Data) files
    num_files = models.IntegerField(default=0)
    organism = models.CharField(max_length=200, blank=True)
    type = models.CharField(max_length=20, blank=True)
    mlst_results = models.CharField(max_length=50, blank=True)
    amr_results = models.CharField(max_length=50, blank=True)
    geneseekr_results = models.CharField(max_length=50, blank=True)
    spades_results = models.CharField(max_length=50, blank=True)
    spades_results_file = models.FileField(blank=True)
    spades_log_file = models.FileField(blank=True)


class MLST(BaseJob):
    result = models.FileField(blank=True)
    rmlst_result = models.FileField(blank=True)
    project = models.ForeignKey(Project)
    reference = models.FileField(blank=True)


class AMR(BaseJob):
    result = models.FileField(blank=True)
    result2 = models.FileField(blank=True)
    result3 = models.FileField(blank=True)
    result4 = models.FileField(blank=True)
    result5 = models.FileField(blank=True)
    gene_count = models.CharField(max_length=200, blank=True)
    data_id = models.CharField(max_length=100, default=False)
    genome = models.FileField(blank=True)
    identity = models.IntegerField(default=80)
    project = models.ForeignKey(Project)


class Galaxy(BaseJob):
    result = models.FileField(blank=True, default=False)
    profile = models.CharField(max_length=200, blank=True)
    data_id = models.CharField(max_length=100, default=False)
    genome = models.FileField(upload_to=generate_path, blank=True)

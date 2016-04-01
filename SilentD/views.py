import csv
import os
from collections import defaultdict
# Django Related Imports
from django.shortcuts import render
from django.contrib.auth import authenticate
from django.contrib.auth import login
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .forms import UserForm
# Database Models
from .models import Data
from .models import PrimerV
from .models import GeneS
from .models import SNP
from .models import MLST
from .models import AMR
from .models import Project
from .models import Profile
from .models import MiSeq
# Celery Tasks
from .tasks import app
from .tasks import primer_validator_task
from .tasks import ksnpfastq_task
from .tasks import gene_seeker_task
from .tasks import mmlst_task
from .tasks import amr_fasta_task
from .tasks import amr_fastq_task
from .tasks import gene_seeker_fastq_task
from .tasks import miseq_task
from .tasks import pipeline_task
from .tasks import spades_task
# Other Functions
from Bio.SeqUtils import MeltingTemp
from functions import armi_rarity
from functions import determine_organism


# Create your views here.
def register(request):
    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        print request.POST
        user_form = UserForm(data=request.POST)

        if user_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            print user
            user_info = Profile(rank='Research')
            user_info.user = user
            user_info.save()

            print user.profile

            # Auto Log in the new user into system
            new_user = authenticate(username=request.POST['username'],
                                    password=request.POST['password'])
            login(request, new_user)

            # Redirect to main index page
            return HttpResponseRedirect('/bio/index/')
        # Invalid form or forms - mistakes or something else?
        # Print problems to the terminal.
        # They'll also be shown to the user.
        else:
            print user_form.errors

    # Something went wrong, redirect back to login page

    messages.add_message(request, messages.INFO, 'Form Errors or User Already Exists')
    return render(request, 'SilentD/login.html', {})


def user_login(request):
    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        # We use request.POST.get('<variable>') as opposed to request.POST['<variable>'],
        # because the request.POST.get('<variable>') returns None, if the value does not exist,
        # while the request.POST['<variable>'] will raise key error exception
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None (Python's way of representing the absence of a value), no user
        # with matching credentials was found.
        if user:
            # Is the account active? It could have been disabled.
            if user.is_active:
                # If the account is valid and active, we can log the user in.
                # We'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect('/bio/index/')
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your CFIA BioTools account is disabled.")
        else:
            # Bad login details were provided. So we can't log the user in.
            error_message = "Invalid Login Details Provided"
            messages.add_message(request, messages.ERROR, error_message)

            print "Invalid login details: {0}, {1}".format(username, password)
            return render(request, "SilentD/login.html", {})

    # The request is not a HTTP POST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variables to pass to the template system, hence the
        # blank dictionary object...
        return render(request, 'SilentD/login.html', {})


# Use the login_required() decorator to ensure only those logged in can access the view.
@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)

    # Take the user back to the homepage.
    return HttpResponseRedirect('/')


# csrf_exempt decorator allowing easier Dropzone.js compatibility.
@csrf_exempt
@login_required
def file_upload(request):
    username = None
    if request.user.is_authenticated():
        username = request.user.username

    if request.method == 'POST':
        print "User %s uploading %s " % (username, request.FILES)
        # Create a new database entry for the file
        file_name = str(request.FILES['file'])
        # Save model first to generate ID, then upload the file to the folder with ID
        if 'fastq.gz' in file_name:
            newdoc = Data(user=username, type='FastQ')
            newdoc.save()
            newdoc.file = request.FILES['file']
            newdoc.save()
            newdoc.name = newdoc.file.name.split('/')[-1]
            newdoc.save()

            '''# Try to find a matching fastq in database to merge the pair into a project. This is done by comparing the
            # file name with the corresponding R1 and R2 values so see if they match. The most recently uploaded files
            # will be matched and script will exit loop and proceed
            fastq_list = Data.objects.filter(user=username, type='FastQ').order_by('-date')

            file_name_split = newdoc.name.split('_')
            if len(file_name_split) < 2:
                return render(request, 'SilentD/file_upload.html', {})
            else:
                file_name_1 = file_name_split[0]
                if '_R1' in newdoc.name:
                    r_value_1 = 'R1'
                elif 'R2' in newdoc.name:
                    r_value_1 = 'R2'
                else:
                    pass
                    # Improperly named file, error error

                # Search for a corresponding file that matches
                for fastq in fastq_list:
                    file_name_2 = fastq.name.split('_')[0]
                    if '_R1' in fastq.name:
                        r_value_2 = 'R1'
                    elif '_R2' in fastq.name:
                        r_value_2 = 'R2'

                    if file_name_1 == file_name_2:
                        if (r_value_1 == 'R1' and r_value_2 == 'R2') or (r_value_1 == 'R2' and r_value_2 == 'R1'):
                            print "Found A Match!"
                            # Create a new project database entry with the two matched files, organism to be determined
                            # using S16 methods.

                            # # Only create a project if another one of same name not created within 10 seconds
                            # existing_project = Project.objects.filter(user=username, description=file_name_1)
                            # if len(existing_project) > 0:
                            #     td = (datetime.datetime.now() - existing_project[0].date).total_seconds()
                            #     if td < 10:
                            #         return render(request, 'SilentD/file_upload.html', {})
                            # else:
                            new_project = Project(user=username, description=file_name_1)
                            new_project.save()
                            new_project.files.add(newdoc)
                            new_project.files.add(fastq)
                            new_project.num_files = 2
                            new_project.description = file_name_1
                            new_project.type = 'Individual'
                            new_project.save()
                            # Start the automatic analysis now that a match has been found
                            # pipeline_task.delay(new_project.id)
                            return render(request, 'SilentD/file_upload.html', {})

            print 'No Match Found'
            '''

        elif '.fa' in file_name:
            # Database entry must be saved first to generate unique ID
            newdoc = Data(user=username, type='Fasta')
            newdoc.save()
            # Upload the file to database entry and corresponding unique folder
            newdoc.file = request.FILES['file']
            newdoc.save()
            newdoc.name = newdoc.file.name.split('/')[-1]
            newdoc.save()
        else:
            if 'GenerateFASTQRunStatistics.xml' in file_name:
                newdoc = Data(user=username, type='RunStatistics')
                newdoc.save()
                newdoc.file = request.FILES['file']
                newdoc.save()
                newdoc.name = newdoc.file.name.split('/')[-1]
                newdoc.save()
            elif 'RunInfo.xml' in file_name:
                newdoc = Data(user=username, type='RunInfo')
                newdoc.save()
                newdoc.file = request.FILES['file']
                newdoc.save()
                newdoc.name = newdoc.file.name.split('/')[-1]
                newdoc.save()

            elif 'SampleSheet.csv' in file_name:
                newdoc = Data(user=username, type='SampleSheet')
                newdoc.save()
                newdoc.file = request.FILES['file']
                newdoc.save()
                newdoc.name = newdoc.file.name.split('/')[-1]
                newdoc.save()
                # Create a MiSeq Task and Begin Automatic Analysis here
                # miseq_task.delay(newdoc.id, "Create")
            else:
                pass
    return render(request, 'SilentD/file_upload.html', {})


@login_required
def primer_validator(request):

    # Check User for name, and Any Privilegdes (CFIA Access)
    username = ""
    if request.user.is_authenticated():
        username = request.user.username

    if request.method == 'POST':
        print request.POST

        # Stop, Delete or View Results
        if 'id' in request.POST:

            # Retrieve AMR Object
            obj_id = request.POST['id']
            obj = PrimerV.objects.get(id=obj_id)

            # Job Status, either the job is running with unique ID, or its stopped with ""
            job_id = obj.job_id

            if 'stop' in request.POST:
                obj.job_id = 0
                obj.save()

                documents = PrimerV.objects.filter(user=username)
                return render(request, 'SilentD/primer_validator.html', {'documents': documents})

            # Deletes an entry in the PrimerV database on previous jobs
            elif 'delete' in request.POST:
                print "Killing Task"
                app.control.revoke(job_id, terminate=True)
                print "Deleting Object"
                obj.delete()

                # Sends updated list back to client
                documents = PrimerV.objects.filter(user=username)
                return render(request, 'SilentD/primer_validator.html', {'documents': documents})

            else:
                # Retrieves dictionary file associated with the job_id generated at job initialization
                results_list = []
                with open(obj.result.name, 'r') as f:
                    results = csv.DictReader(f)
                    for row in results:
                        results_list.append(row)

                with open(obj.misses.name, 'r') as f:
                    misses_list = f.readlines()

                documents = PrimerV.objects.filter(user=username)
                return render(request, 'SilentD/primer_validator.html',
                              {'documents': documents, 'results': results_list, 'misses': misses_list})

        # Input variables for ePCR
        target = request.POST['target']
        # Really inefficient line to convert ecoli_ncbi.hash into Ecoli NCBI
        organism = str(target).replace('.hash', "").replace('_', " ").title().replace('Ncbi', 'NCBI')\
            .replace('Cfia', 'CFIA')
        forward_text = request.POST['forwardPrimer']
        reverse_text = request.POST['reversePrimer']
        mism = request.POST['mism']
        tag = ''
        if 'tag' in request.POST:
            tag = request.POST['tag']

        forward_split = forward_text.splitlines()
        reverse_split = reverse_text.splitlines()

        # Batch Processing logic, compares each forward primer against respective reverse primer
        for i in range(len(forward_split)):
            # Remove any formatting from user input text
            forward = forward_split[i]
            forward = forward.upper()
            forward = forward.replace(" ", "")
            forward_gc = round(MeltingTemp.Tm_GC(forward, strict=False), 2)

            reverse = reverse_split[i]
            reverse = reverse.upper()
            reverse = reverse.replace(" ", "")
            reverse_gc = round(MeltingTemp.Tm_GC(reverse, strict=False), 2)

            # Create a database model for each primer pair
            task_model = PrimerV(forward=forward, reverse=reverse, forward_gc=forward_gc, reverse_gc=reverse_gc,
                                 user=username, target=target, organism=organism, tag=tag, mism=mism, job_id='1')
            task_model.save()

            obj_id = task_model.id

            # Celery task that performs the actual analysis and saves results to a <id>.csv file
            primer_validator_task.delay(obj_id)

    # Retrieve all past analysis from database
    documents = PrimerV.objects.filter(user=username)

    return render(request, 'SilentD/primer_validator.html', {'documents': documents})


@login_required
def gene_seeker(request):
    # GeneS.objects.all().delete()
    username = ''
    if request.user.is_authenticated():
        username = request.user.username

    # Retrieve projects, sort by date descending, keep only 15 most recent
    projects = Project.objects.filter(user=username).order_by('-date')

    # Handle Genome Upload
    if request.method == 'POST':
        print request.POST

        # Result input variables
        if 'id' in request.POST:
            obj_id = request.POST['id']
            obj = GeneS.objects.get(id=obj_id)

            # Delete Object from Database
            if 'delete' in request.POST:
                GeneS.objects.get(id=obj_id).delete()

            # Stop currently running job
            elif 'stop' in request.POST:
                obj.job_id = ''
                obj.save()
            else:
                documents = GeneS.objects.filter(user=username)
                for d in documents:
                    if d.targets != '':
                        d.uname = d.targets.name.split('/')[-1]

                data_list = []
                path = obj.result.name
                print path
                with open(path, 'r') as f:
                    lines = f.readlines()
                    if obj.type == 'fastq' or obj.type == 'Individual':
                        keys = lines[0].split('\t')
                        lines.pop(0)
                        for line in lines:
                            data_list.append(line.split('\t'))

                    else:
                        keys = lines[0].rstrip().split(',')
                        keys = filter(None, keys)

                        lines.pop(0)
                        for line in lines:
                            data_list.append(line.rstrip().split(','))

                return render(request, 'SilentD/gene_seeker.html',
                              {'documents': documents, 'projects': projects, 'results': data_list, 'keys': keys})

        else:  # Input variables for Gene Seeker
            data = request.POST.get('database')
            genes = request.POST.get('query')
            cutoff = (request.POST.get('cutoff'))

            # Target is a Project ID
            if str(data).isdigit():
                proj_obj = Project.objects.get(id=data)
                organism = proj_obj.organism
                project_type = proj_obj.type
                geneseeker_object = GeneS(user=username, organism=proj_obj.description, genes=genes,
                                          job_id=str(data), type=project_type, cutoff=cutoff)
                geneseeker_object.save()

                # Check for user uploaded targets and add to database object
                if request.FILES:
                    print request.FILES
                    if 'usertargets' in request.FILES:
                        geneseeker_object.targets = request.FILES['usertargets']
                        geneseeker_object.save()

                if str(project_type) == 'fastq' or str(project_type) == 'Individual':
                    gene_seeker_task.delay(geneseeker_object.id)
                elif str(project_type) == 'fasta':
                    gene_seeker_task.delay(geneseeker_object.id)

            else:
                geneseeker_object = GeneS(user=username, organism=data, genes=genes, job_id='0', type='fasta',
                                          cutoff=cutoff)
                geneseeker_object.save()

                if request.FILES:
                    print request.FILES
                    if 'usertargets' in request.FILES:
                        geneseeker_object.targets = request.FILES['usertargets']

                geneseeker_object.save()
                # Run Gene Seeker in background
                gene_seeker_task.delay(geneseeker_object.id)

    # retrieve all documents stored in database matching user

    documents = GeneS.objects.filter(user=username)
    for d in documents:
        if d.targets != '':
            d.uname = d.targets.name.split('/')[-1]


    return render(request, 'SilentD/gene_seeker.html', {'documents': documents, 'projects': projects})


@login_required
def miseq(request):
    # MiSeq.objects.all().delete()
    username = ''
    if request.user.is_authenticated():
        username = request.user.username
    projects = MiSeq.objects.filter(user=username)

    file_list = []
    fastq_list = []


    if request.method == 'POST':
        print request.POST

        if request.POST.get('proceed'):
            print "Starting MiSeq Task"
            miseq_task.delay(request.POST['proceed'])
            return render(request, 'SilentD/miseq.html', {'documents': file_list, 'projects': projects})

        if request.POST.get('MiSeq'):
            print "Handling MiSeq Creation"
            runinfo = request.FILES.get('runinfo')
            runstats = request.FILES.get('FASTQRun')
            samplesheet = request.FILES.get('SampleSheet')
            description = request.POST.get('name')

            # Generate MiSeq Database Entry and ID
            new_miseq = MiSeq(description=description, user=username)
            new_miseq.save()

            # Save uploaded files to database entry after ID created
            new_miseq.RunInfo = runinfo
            new_miseq.SampleSheet = samplesheet
            new_miseq.RunStats = runstats
            new_miseq.save()

        elif request.POST.get('missing'):
            new_miseq = MiSeq.objects.get(id=request.POST['missing'])

        else:
            return render(request, 'SilentD/miseq.html', {'documents': file_list, 'projects': projects})

        # Extract all the required filenames from the SampleSheet
        with open(new_miseq.SampleSheet.name) as f:
            lines = f.readlines()
            found_sampleid = False

            for line in lines:
                if line.startswith('Sample_ID'):
                    found_sampleid = True
                    continue

                if found_sampleid:
                    fastq_list.append(line.split(',')[0])

        # Find and add all pairs of FastQ files
        for fastq in fastq_list:
            # Retrieve first two most recent matching files found to FastQ name
            object_list = Data.objects.filter(user=new_miseq.user, name__contains=fastq).order_by('-date')
            paired_files = ["Not Found", "Not Found"]
            # Add first R1 file found, then add first R2 file found
            for obj in object_list:
                if 'R1_001.fastq.gz' in obj.name:
                    paired_files[0] = obj
                    break
            for obj in object_list:
                if 'R2_001.fastq.gz' in obj.name:
                    paired_files[1] = obj
                    break

            # Only add 2 paired files to database model and start task!
            if paired_files[0] != "Not Found" and paired_files[1] != "Not Found":
                new_miseq.files.add(paired_files[0])
                new_miseq.files.add(paired_files[1])
                file_list.append([fastq, paired_files[0].name, paired_files[1].name, 'True'])
                print "Found 2 Paired Files Matching " + fastq
            else:
                new_miseq.missing = True
                missing_files = True
                if paired_files[0] == "Not Found" and paired_files[1] == "Not Found":
                    file_list.append([fastq, paired_files[0], paired_files[1], 'False'])
                elif paired_files[0] == "Not Found":
                    file_list.append([fastq, paired_files[0], paired_files[1].name, 'False'])
                else:
                    file_list.append([fastq, paired_files[0].name, paired_files[1], 'False'])

        new_miseq.save()
        return render(request, 'SilentD/miseq.html', {'documents': file_list, 'projects': projects, 'post': True,
                                                      'missing_files': missing_files, 'miseq': new_miseq})

    return render(request, 'SilentD/miseq.html', {'documents': file_list, 'projects': projects})


@login_required
def data(request):
    # AMR.objects.all().delete()
    # GeneS.objects.all().delete()
    # Project.objects.all().delete()
    # MiSeq.objects.all().delete()
    # Data.objects.all().delete()
    username = ''
    if request.user.is_authenticated():
        username = request.user.username

    project_creation_fail = False

    if request.method == 'POST':
        print request.POST
        spades_id = request.POST.get('spades')

        # Handle a new assignment of an organism, or 16S Typing
        if "assign_organism" in request.POST and "select_organism" in request.POST:
            assign_organism = request.POST.get('assign_organism')
            pro_obj = Project.objects.get(id=assign_organism)
            if request.POST.get('select_organism') == '16S':
                pro_obj.organism = request.POST.get('select_organism')
                pro_obj.save()
                pipeline_task.delay(assign_organism)
            else:
                pro_obj.organism = request.POST.get('select_organism')
                pro_obj.save()

            print "Assigned Organism"
        # Request to view SPAdes results from a previous run

        # Perform analysis of a project, a variety of jobs available
        elif "job" in request.POST:
            job = request.POST.get('job')
            proj_id = request.POST.get('project_id')
            pro_obj = Project.objects.get(id=proj_id)

            if job == 'spades_start':
                # Turn on Spades Running Flag for Template and run SPAdes task
                pro_obj.spades_results = "Running"
                pro_obj.save()
                spades_task.delay(proj_id)

            elif job == 'amr_start':
                pro_obj.amr_results = "Running"
                pro_obj.save()
                if pro_obj.type == 'fasta':
                    amr_fasta_task.delay(proj_id)
                elif pro_obj.type == 'fastq' or pro_obj.type == 'Individual':
                    amr_fastq_task.delay(proj_id)

            elif job == 'mlst_start':
                # Verify the organism is one of the limited supporting ones
                organism = determine_organism(pro_obj.organism, 'MLST')
                if organism:
                    pro_obj.mlst_results = "Running"
                    pro_obj.save()
                    mmlst_task.delay(proj_id)
                else:
                    error_message = "Error! No Matching MLST Profile for Organism: %s" % pro_obj.organism
                    messages.add_message(request, messages.ERROR, error_message)

        elif "spades_results" in request.POST:
            proj_id = request.POST.get('spades_results')
            pro_obj = Project.objects.get(id=proj_id)
            return render(request, 'SilentD/spades_results.html', {'document': pro_obj})

        elif "amr_results" in request.POST:
            proj_id = request.POST.get('amr_results')
            pro_obj = Project.objects.get(id=proj_id)

            documents = AMR.objects.filter(user=username, project=pro_obj)
            return render(request, 'SilentD/amr.html', {'documents': documents})

        elif "mlst_results" in request.POST:
            proj_id = request.POST.get('mlst_results')
            pro_obj = Project.objects.get(id=proj_id)

            documents = MLST.objects.filter(user=username, project=pro_obj)
            return render(request, 'SilentD/mlst.html', {'documents': documents})

    # Retrieve all uploaded files relating to the user
    indiv_projects = Project.objects.filter(user=username, type='Individual')
    fastq_projects = Project.objects.filter(user=username, type='fastq')
    fasta_projects = Project.objects.filter(user=username, type='fasta')
    miseq_projects = MiSeq.objects.filter(user=username)
    return render(request, 'SilentD/data.html', {'indiv_projects': indiv_projects,
                                                 'fastq_projects': fastq_projects,
                                                 'fasta_projects': fasta_projects,
                                                 'miseq_projects': miseq_projects})


@login_required
def create_project(request):

    # AMR.objects.all().delete()
    # GeneS.objects.all().delete()
    # Project.objects.all().delete()
    # Data.objects.all().delete()
    username = ''
    if request.user.is_authenticated():
        username = request.user.username

    project_creation_fail = False

    if request.method == 'POST':
        print request.POST

        description = request.POST.get('name')
        organism = request.POST.get('organism')
        if request.POST.get('ids'):
            # FastQ
            data_file_list = request.POST.get('ids')
        else:
            #Fasta
            data_file_list = request.POST.get('ids2')

        project_type = request.POST.get('type')

        if data_file_list and organism and description and project_type:
            data_file_list2 = data_file_list.replace('id=', '')
            data_list = data_file_list2.split('&')

            data_obj_list = []
            filename_list = []
            failed_list = []
            for item in data_list:
                    data_obj = Data.objects.get(id=item)
                    data_obj_list.append(data_obj)
                    filename_list.append(str(data_obj.name))

            if project_type == 'fastq':
                # Conditions below are tested in order for files to be added to a project
                # File count is an even number
                # Files have proper formatted _R1 or _R2 in file name
                # Each file is paired with its other R value

                if len(data_list) % 2 != 0:
                    # List has uneven number of files due retrieval error
                    project_creation_fail = True
                else:
                    # Create a dictionary of strain names, and populate with found R values
                    file_dict = defaultdict(list)
                    for filename in filename_list:
                        name = filename.split("_")[0]
                        if '_R1' in filename:
                            rvalue = 'R1'
                            file_dict[name].append(rvalue)
                        elif '_R2' in filename:
                            rvalue = 'R2'
                            file_dict[name].append(rvalue)
                        else:
                            error_message = "Error! File %s does not have a correct RValue in the format _R1 or _R2" \
                                             % name
                            messages.add_message(request, messages.ERROR, error_message)

                    # Verify all files are paired and have a match of R1 and R2, not R1,R1, R2,R2 or only 1 R value

                    for key, value in file_dict.items():
                        if len(value) == 2:
                            if (value[0] == "R1" and value[1] == "R2") or (value[0] == "R2" and value[1] == "R1"):
                                print "Match!"
                            else:
                                project_creation_fail = True
                                failed_list.append(key)
                                error_message = "Error! %s has two R1 or two R2 values" % key
                                messages.add_message(request, messages.ERROR, error_message)
                        else:
                            project_creation_fail = True
                            failed_list.append(key)
                            error_message = "Error! 2 Files must be associated with %s" % key
                            messages.add_message(request, messages.ERROR, error_message)

            if project_creation_fail:
                    error_message = "Error! No paired match found for the Following:  " + ", ".join(failed_list) + \
                                    ", Ensure each pair of files contains *_R1_001.fastq.gz and *_R2_001.fastq.gz"
                    messages.add_message(request, messages.ERROR, error_message)
            else:
                # Create a Fasta or Fastq Project
                new_project = Project(user=username, description=description, organism=organism)
                new_project.save()
                for obj in data_list:
                    new_project.files.add(obj)
                new_project.num_files = len(data_list)
                new_project.type = request.POST.get('type')
                new_project.save()

                success_message = description + " created succesully"
                messages.add_message(request, messages.SUCCESS, success_message)

                # Send user to the Projects main page
                indiv_projects = Project.objects.filter(user=username, type='Individual')
                fastq_projects = Project.objects.filter(user=username, type='fastq')
                fasta_projects = Project.objects.filter(user=username, type='fasta')
                return render(request, 'SilentD/data.html', {'indiv_projects': indiv_projects,
                                                             'fastq_projects': fastq_projects,
                                                             'fasta_projects': fasta_projects})
        else:
            print "No Chosen Items"

    # Retrieve all uploaded files relating to the user
    documents = Data.objects.filter(user=username).exclude(file__isnull=True).exclude(file="")
    fastqs = Data.objects.filter(user=username, type='FastQ').exclude(file__isnull=True).exclude(file="")
    fastas = Data.objects.filter(user=username, type='Fasta').exclude(file__isnull=True).exclude(file="")
    # Convert file size to megabytes
    for d in fastqs:
        if d.file:
            if os.path.isfile(d.file.name):
                d.size = d.file.size/1000/1000
            else:
                # For some reason the file has been deleted, update the databases to remove this entry
                Data.objects.get(id=d.id).delete()
        else:
            d.size = 0
    for d in fastas:
        if d.file:
            if os.path.isfile(d.file.name):
                d.size = float(d.file.size)/1000.0/1000.0
            else:
                # For some reason the file has been deleted, update the databases to remove this entry
                Data.objects.get(id=d.id).delete()
        else:
            d.size = 0
    return render(request, 'SilentD/create_project.html', {'documents': documents, 'fastqs': fastqs, 'fastas': fastas})


@login_required
def snp(request):

    username = ''
    if request.user.is_authenticated():
        username = request.user.username

    # Retrieve projects, sort by date descending, keep only 10 most recent
    projects = Project.objects.filter(user=username).order_by('-date')
    projects = projects[:10]

    # Handle Genomes Upload
    if request.method == 'POST':
        print request.POST

        # Result input variables
        if 'id' in request.POST:
            obj_id = request.POST['id']
            obj = SNP.objects.get(id=obj_id)

            # Delete Object from Database
            if 'delete' in request.POST:
                SNP.objects.get(id=obj_id).delete()

            # Stop currently running job
            elif 'stop' in request.POST:
                obj.job_id = ''
                obj.save()

            else:
                documents = SNP.objects.filter(user=username)
                for d in documents:
                    if d.genome != '':
                        d.gname = d.genome.name.split('/')[-1]

                data_list = []
                path = obj.result.name
                with open(path, 'rt') as f:
                    lines = f.readlines()
                    keys = lines[0].split(',')
                    lines.pop(0)
                    for line in lines:
                        data_list.append(line.split(','))

                return render(request, 'SilentD/gene_seeker.html',
                              {'documents': documents, 'results': data_list, 'keys': keys})

        else:  # Input variables SNP Programs

            # Create job model
            model = SNP(user=username)
            if 'tag' in request.POST:
                model.tag = request.POST['tag']
            model.save()

            if 'kSNP' in request.POST:
                print "kSNP"
                model.type = 'kSNP'
                model.upload = request.FILES['genome']
                model.job_id = '1'
                model.save()

                # ksnp_task.delay(model.id)

            elif 'kFastQ' in request.POST:
                print 'kFastQ'
                project_id = request.POST['project']
                project_obj = Project.objects.get(id=project_id)
                model.type = 'kSNP FastQ'
                model.tag = project_obj.description
                model.job_id = '1'
                model.data_id = project_id
                model.save()
                ksnpfastq_task.delay(model.id)

            elif 'CFSAN' in request.POST:
                print 'CFSAN'
                project_id = request.POST['project']
                project_obj = Project.objects.get(id=project_id)
                model.type = 'CFSAN'
                model.tag = project_obj.description
                model.data_id = project_id
                model.upload = request.FILES['reference']
                model.job_id = '1'
                model.save()

                # CFSAN_task.delay(model.id)

            '''
            print "new kSNP"
            print request.FILES
            results = kSNP_model(user=username)

            if 'tag' in request.POST:
                results.tag = request.POST['tag']

            # Turn on job running notifier and save to database
            results.save()

            # Save File to newly updated ID folder
            results.genome = request.FILES['genome']
            results.job_id = '1'
            results.save()
            # Retrieves the ID of the just saved object
            obj_id = results.id

            # Run Gene Seeker in background
            ksnp_task.delay(obj_id)'''

    # retrieve all documents stored in database matching user
    documents = SNP.objects.filter(user=username)
    for d in documents:
        if d.upload != '':
            d.name = d.upload.name.split('/')[-1]

    return render(request, 'SilentD/snp.html', {'documents': documents, 'projects': projects})


@login_required
def mlst(request):

    # MLST.objects.all().delete()
    username = ''
    if request.user.is_authenticated():
        username = request.user.username

    if request.POST:
        print request.POST

        # Result input variables
        if 'rMLST' in request.POST:
            obj_id = request.POST['rMLST']
            obj = MLST.objects.get(id=obj_id)
            project_type = obj.type
            path = obj.rmlst_result.name
        elif 'MLST' in request.POST:
            obj_id = request.POST['MLST']
            obj = MLST.objects.get(id=obj_id)
            path = obj.result.name
            project_type = obj.type
        elif 'reference' in request.POST:
            obj_id = request.POST['reference']
            obj = MLST.objects.get(id=obj_id)
            project_type = obj.type
            path = obj.reference.name
        else:
            path = ""
        print project_type
        # Retrieve data to display
        data_list = []
        with open(path, 'rt') as f:
            lines = f.readlines()
            if project_type == 'fasta':
                keys = lines[0].replace(",\n","").split(',')
                lines.pop(0)
                for line in lines:
                    line_split = line.split(',')
                    line_split.pop()    # Removes the trailing empty string after splitting
                    if line_split[0] != 'Strain':
                        data_list.append(line_split)
            elif project_type == 'fastq':
                '''print "Here"
                result_dict = csv.reader(f, delimiter='\t')
                keys = []
                for row in result_dict:
                    print row
                    keys = row.keys()
                    data_list.append(row.values())
                print keys
                print data_list

                '''
                keys = lines[0].replace('\n', "").split('\t')
                lines.pop(0)
                for line in lines:
                    line_split = line.split('\t')
                    if line_split[0] != 'Sample':
                        data_list.append(line_split)

            documents = MLST.objects.filter(user=username)
            return render(request, 'SilentD/mlst.html', {'documents': documents,
                                                         'results': data_list, 'keys': keys})

    documents = MLST.objects.filter(user=username)
    return render(request, 'SilentD/mlst.html', {'documents': documents})


@login_required
def amr(request):
    # AMR.objects.all().delete()
    username = ''
    if request.user.is_authenticated():
        username = request.user.username

    # Retrieve projects, sort by date descending, keep only 10 most recent
    projects = Project.objects.filter(user=username).order_by('-date')
    projects = projects[:10]

    if request.POST:
        # Send back the result file in a table, either ARG-ANNOT or ResFinder
        if 'result' in request.POST:
            # Retrieve all past jobs to send to page
            documents = AMR.objects.filter(user=username)

            data_list = []
            chart_data = {'aminoglycosides': 0, 'beta-lactamases': 0, 'fosfomycin': 0, 'fluoroquinolones': 0,
                          'glycopeptides': 0, 'macrolide-lincosamide-streptogramin': 0, 'phenicol': 0, 'rifampicin': 0,
                          'sulfonamides': 0, 'tetracyclines': 0, 'trimethoprim': 0}

            # Form data is the path to result file
            path = request.POST['result']
            if '_results.txt' in path:
                with open(path, 'rt') as f:
                    lines = f.readlines()
                    print lines[0]
                    keys = lines[0].split(',')
                    lines.pop(0)
                    for line in lines:
                        print line
                        data_list.append(line.split(','))

                return render(request, 'SilentD/amr.html', {'documents': documents, 'projects': projects,
                                                            'display': True, 'results': data_list, 'keys': keys})

            elif 'ARMI' in path:
                obj = request.POST['obj']
                amr_object = AMR.objects.get(id=obj)
                organism = amr_object.organism
                armi_results = {}
                armi_categories = {}
                armi_misses = {}

                # Create list containing description, organism species, job date and type
                caption = [amr_object.tag, organism, amr_object.date, amr_object.type]

                with open(path, 'rt') as f:
                    lines = f.readlines()
                    sample_number = len(lines)-2
                    print sample_number
                    keys = lines[0].split(',')
                    keys.pop(0)
                    '''
                    # Format keys list to remove quotes and final new line character
                    for key in range(len(keys)):
                        keys[key] = keys[key].replace('\"', '')
                    keys[-1] = keys[-1].replace('\n', '')
                    '''
                    lines.pop(0)
                    lines.pop(0)

                    matches = 0
                    counts = 0
                    if amr_object.type == 'Multi Fasta':
                        for index, elem in enumerate(counts):
                            antibiotic = keys[index]
                            value = armi_rarity[antibiotic]
                            category = value[0]

                            rarity = value[1]
                            if organism == 'Escherichia':
                                rarity = value[2]
                            elif organism == 'Salmonella':
                                rarity = value[3]
                            elif organism == 'Listeria':
                                rarity = value[4]

                            # Simplify rarity scale to a 5 point scale, with 5 being most rare
                            if rarity <= 10:
                                rarity = 5
                            elif 10 < rarity <= 20:
                                rarity = 4
                            elif 20 < rarity <= 30:
                                rarity = 3
                            elif 30 < rarity <= 50:
                                rarity = 2
                            else:
                                rarity = 1
                            if elem == sample_number:
                                matches += 1
                                if category not in armi_results and category not in armi_categories:
                                    # Create new dictionary entry with a dictionary
                                    armi_results[category] = {antibiotic: rarity}
                                    armi_categories[category] = rarity

                                else:
                                    # Add another antibiotic to the category dictionary
                                    armi_results[category][antibiotic] = rarity
                                    armi_categories[category] += rarity
                            elif elem == 0:
                                if category not in armi_misses:
                                    armi_misses[category] = {antibiotic: rarity}
                                else:
                                    # Add another antibiotic to the category dictionary
                                    armi_misses[category][antibiotic] = rarity

                            print matches, "Matches"
                    else:
                        for line in lines:
                            li = line.split(',')

                            li.pop(0)
                            print li
                            # Enumerate over the list to get all the hits
                            for index, elem in enumerate(li):
                                if elem == '+':
                                    antibiotic = str(keys[index])
                                    armi_results[antibiotic] = "1"
                                if elem == '-':
                                    antibiotic = str(keys[index])
                                    armi_results[antibiotic] = "0"
                            print len(armi_results)
                print armi_misses
                return render(request, 'SilentD/amr.html', {'documents': documents, 'projects': projects,
                                                            'armi_results': armi_results, "caption": caption,
                                                            'armi_misses': armi_misses})

            else:
                obj = AMR.objects.get(id=request.POST.get('obj'))
                print path
                with open(path, 'rt') as f:
                    lines = f.readlines()
                    keys = ['Strain', 'Gene', 'Query Length', 'Subject Length', 'Alignment Length', 'Matched Bases',
                            '% Identity']
                    # Parses Blast Output into Datatables compatible dictionary
                    print len(lines)
                    for line in lines:
                        line_list = line.split(',')
                        coverage = (float(line_list[5])/float(line_list[3])*100.0)
                        print obj.identity
                        #if coverage >= obj.identity:
                        line_list.append(str(coverage))
                        data_list.append(line_list)

                        if float(coverage) > 90.0:
                            if '(AGly)' in line_list[1]:
                                chart_data['aminoglycosides'] += 1
                            if '(Bla)' in line_list[1]:
                                chart_data['beta-lactamases'] += 1
                            if '(Fos)' in line_list[1]:
                                chart_data['fosmomycin'] += 1
                            if '(Flq)' in line_list[1]:
                                chart_data['fluoroquinolones'] += 1
                            if '(Gly)' in line_list[1]:
                                chart_data['glycopeptides'] += 1
                            if '(MLS)' in line_list[1]:
                                chart_data['macrolide-lincosamide-streptogramin'] += 1
                            if '(Phe)' in line_list[1]:
                                chart_data['phenicol'] += 1
                            if '(Rif)' in line_list[1]:
                                chart_data['rifampicin'] += 1
                            if '(Sul)' in line_list[1]:
                                chart_data['sulfonamides'] += 1
                            if '(Tet)' in line_list[1]:
                                chart_data['tetracyclines'] += 1
                            if '(Tmt)' in line_list[1]:
                                chart_data['trimethoprim'] += 1

                return render(request, 'SilentD/amr.html', {'documents': documents, 'projects': projects,
                                                            'results': data_list, 'keys': keys, 'display': True})

        if 'id' in request.POST:
            # Retrievel model associated with ID to either stop job or delete
            obj_id = request.POST['id']
            obj = AMR.objects.get(id=obj_id)

            # Delete Object from Database
            if 'delete' in request.POST:
                AMR.objects.get(id=obj_id).delete()

            # Stop currently running job
            elif 'stop' in request.POST:
                obj.job_id = ''
                obj.save()

            documents = AMR.objects.filter(user=username)
            return render(request, 'SilentD/amr.html', {'documents': documents, 'projects': projects})

        # Form inputs for new job
        tag = ''
        if 'tag' in request.POST:
            tag = request.POST['tag']

        # Create model first to generate an object id
        amr_object = AMR(user=username, tag=tag, job_id='1')
        amr_object.save()

        if 'project' in request.POST:
            amr_object.job_id = request.POST['project']
            amr_object.type = 'FastQ'
            amr_object.job_status = "Running"
            amr_object.save()

            amr_fastq_task.delay(amr_object.id)
        else:
            # Save uploaded file to model after id has been generated
            amr_object.genome = request.FILES['genome']
            amr_object.type = 'Fasta'
            organism = request.POST.get('organism')
            if not organism:
                organism = 'Other'
            amr_object.organism = organism
            identity = request.POST.get('identity')
            if identity:
                amr_object.identity = identity
            amr_object.save()

            # Run celery task
            amr_fasta_task.delay(amr_object.id)

    documents = AMR.objects.filter(user=username)

    return render(request, 'SilentD/amr.html', {'documents': documents, 'projects': projects})


@login_required
def database(request):
    # username = ''
    # if request.user.is_authenticated():
        # username = request.user.username
    return render(request, 'SilentD/database.html', {})

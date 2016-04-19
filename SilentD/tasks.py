# Python Library
from __future__ import absolute_import
from celery import Celery
from celery import group
from time import sleep
from subprocess import call
import csv
import json
import zipfile
import shutil
import os
import glob
import random
# Django Model Imports
from SilentD.models import User
from SilentD.models import Profile
from SilentD.models import Data
from SilentD.models import PrimerV
from SilentD.models import GeneS
from SilentD.models import SNP
from SilentD.models import MLST
from SilentD.models import AMR
from SilentD.models import Galaxy
from SilentD.models import Project
from SilentD.models import MiSeq
# Functions
from SilentD.functions import primer_validator_function
from SilentD.functions import docker_spinner
from SilentD.functions import determine_organism
from SilentD.functions import srst2_formatter
# Other Libraries
from Bio import SeqIO

# Development Boolean
DEV = True
DOCKER_REGISTRY = "192.168.1.5:5000"
# General Settings
app = Celery('tasks',
             backend='djcelery.backends.database.DatabaseBackend',
             broker='amqp://guest:guest@localhost:5672//')


NAS_MOUNT_VOLUME = "/home/ubuntu/nas0/Genomics_Portal/documents_test/"

@app.task(bind=True)
def pipeline_task(self, obj_id):
    print self
    obj = Project.objects.get(id=obj_id)
    print obj

    # Use 16S Typing to Assign Organism, for now default is Escherichia
    description = obj.description
    username = obj.user

    # Automatically Start Analyses Tasks for FastQ Data
    """ # 16S Typing
    sleep(5)  # Replace with the actual 16S Typer!

    obj.organism = "Escherichia coli"
    obj.save()
    """
    '''
    # Set Up AMR Task
    amr_object = AMR(user=username, tag=description, job_id=obj_id, type='FastQ')
    amr_object.save()

    # Set Up GeneSeekR Task
    supported_geneseekr_organisms = ['Escherichia coli', 'Listeria monocytogenes', 'Salmonella enterica', 'stx']
    if any(organism in name for name in supported_geneseekr_organisms):
        genes = organism.split(' ')[0]
        new_genes_obj = GeneS(user=username, organism=organism, genes=genes, job_id=obj.id,
                              type='FastQ', tag=description)
        new_genes_obj.save()
        #group([gene_seeker_fastq_task.delay(new_genes_obj.id), amr_fastq_task.delay(amr_object.id)])
    else:
        obj.geneseekr_results = 'Disabled'
        obj.save()
    # Set up MLST Task
    '''
    print obj.organism
    if obj.organism == '16S':
        print "Starting 16S Typing"
        genesippr_task(obj_id)

    print obj.spades_results
    # Set up SPADES 3.6.2 Task
    if obj.spades_results == "Running":
        print "Starting SPAdes"
        spades_task(obj_id)


@app.task(bind=True)
def spades_task(self, obj_id):
    print self

    project_obj = Project.objects.get(id=obj_id)
    print project_obj.id

    data_files = project_obj.files.all()
    print data_files

    print "Starting SPADes 3.6.2 Task %s for User: %s" % (obj_id, project_obj.user)

    # Internal Folder Structure of the Website
    data_path = 'documents/Spades/%s/%s' % (project_obj.user, project_obj.id)

    # Docker Path is the location folder to mount into the docker container
    docker_path = "%s/Spades/%s/%s" % (NAS_MOUNT_VOLUME, project_obj.user, project_obj.id)

    print "Copying FastQ Files Over to SPAdes Working Dir at %s" % docker_path
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    fastq_file_names = []

    for data in data_files:
        path = data.file.name.split('/')[-1]
        fastq_file_names.append(path)
        end_path = data_path + '/' + path
        print "Copying from %s to %s" % (data.file.name, end_path)
        shutil.copyfile(data.file.name, end_path)

    right_reads = []
    left_reads = []

    var1 = var2 = ""
    for fastq in fastq_file_names:
        if 'R1' in fastq:
            right_reads.append(str(fastq))
            var1 = fastq
        if 'R2' in fastq:
            left_reads.append(str(fastq))
            var2 = fastq

    # Create the YAML file for SPAdes input
    '''data_dict = {'orentiation': "fr", "type": "paired-end", "right reads" : sorted(right_reads),
                 "left reads": sorted(left_reads)}
    with open(data_path+'/data.yml', 'w') as outfile:
        outfile.write( yaml.dump(data_dict) )'''
    print 'Running SPADes 3.6.2'
    # Spin Up Docker Container, Takes a maximum of 2 hours to finish
    docker_spinner(docker_path, obj_id, var1, var2, 0, 'spades-362', 12, 36000)

    print "Saving Results Now"

    # Check for log file and examine it
    log_file = os.path.join(data_path, 'spades.log')
    if os.path.isfile(log_file):
        project_obj.spades_log_file.name = log_file
        project_obj.save()

    result_file = os.path.join(data_path, 'contigs.fasta')
    if os.path.isfile(result_file):
        new_name = result_file.replace('contigs', project_obj.description)
        os.rename(result_file, new_name)
        project_obj.spades_results_file.name = new_name
        project_obj.spades_results = "Done"
        project_obj.save()
    else:
        print "Something went wrong, failed assembly"
        project_obj.spades_results = 'Error'
        project_obj.save()

    print "Removing Temporary Files"
    # First move files to trash folder, copy log files out, delete directory
    for root, dirs, files in os.walk(data_path, topdown=False):
        for name in files:
            fasta = project_obj.description + '.fasta'
            if fasta in str(name) or "log" in str(name):
                print "Not Going to Delete", name
            else:
                os.remove(os.path.join(root, name))
        print "--"
        for name in dirs:
            os.rmdir(os.path.join(root, name))


@app.task(bind=True)
def miseq_task(self, obj_id, job):
    print self

    if job == "Create":
        # Generate MiSeq Database Entry and ID
        samplesheet = Data.objects.get(id=obj_id)
        new_miseq = MiSeq(user=samplesheet.user, sample_sheet=True)
        new_miseq.save()

        fastq_list = []
        missing_files = False
        # Extract all the required filenames from the SampleSheet
        with open(samplesheet.file.name) as f:
            lines = f.readlines()
            found_sampleid = False

            for line in lines:
                if line.startswith('Sample_ID'):
                    found_sampleid = True
                    continue

                if found_sampleid:
                    fastq_list.append(line.split(',')[0])

        # Find and add all pairs of FastQ files
        print fastq_list
        file_list = []
        for fastq in fastq_list:
            # Retrieve first two most recent matching files found to FastQ name
            object_list = Data.objects.filter(user=samplesheet.user, name__contains=fastq).order_by('-date')
            print object_list
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

            # Only add 2 paired files to database model
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

    '''# Retrieve object from database
    miseq_obj = MiSeq.objects.get(id=obj_id)
    miseq_obj.job_id = '1'
    miseq_obj.missing = False
    miseq_obj.save()
    print miseq_obj.SampleSheet.name

    file_list = []
    data_files = miseq_obj.files.all()

    print "Copying FastQ Files Over to MiSeq Working Dir"

    data_path = 'documents/MiSeq/%s/%s' % (miseq_obj.user, miseq_obj.id)
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    for data in data_files:
        file_list.append(data.name)
        path = data.file.name.split('/')[-1]
        end_path = data_path + '/' + path
        print "Copying from %s to %s" % (data.file.name, end_path)
        shutil.copyfile(data.file.name, end_path)

    # Alter SampleSheet.csv to remove all the missing files
    # Store a copy before editing
    end_path = miseq_obj.SampleSheet.name.split('/')
    end_path[-1] = 'SampleSheet_Original.csv'
    endpath = "/".join(end_path)
    shutil.copyfile(miseq_obj.SampleSheet.name, endpath)

    # Remake SampleSheet.csv to remove all the missing files
    seq_id_reached = False
    new_csv = []
    with open(miseq_obj.SampleSheet.name) as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith('Sample_ID'):
                seq_id_reached = True
                new_csv.append(line)
                continue
            if not seq_id_reached:
                new_csv.append(line)
            if seq_id_reached:
                if any(line.split(',')[0] in f for f in file_list):
                    new_csv.append(line)

    # Prepare the new SPADes ready SampleSheet.csv
    with open(miseq_obj.SampleSheet.name, 'w') as f:
        for line in new_csv:
            f.write(line)

    # Begin Spades
    print "Starting SPAdes Docker Container"
    docker_path = '/home/ubuntu/nas0/Genomics_Portal/documents_test/MiSeq/%s/%s' % (miseq_obj.user, miseq_obj.id)
    docker_spinner(docker_path, obj_id, 0, 0, 0, 'vanillaspades', 12, 12000, '/mnt/zvolume1/WGS_Spades/')

    print "Saving Results Now"
    assembly_path = data_path + '/BestAssemblies'
    assembly_zip = data_path + '/Assemblies'
    report_path = data_path + '/reports'
    report_zip = data_path + '/report'

    if os.path.exists(assembly_path) and os.path.exists(assembly_path):
        shutil.make_archive(assembly_zip, 'zip', assembly_path)
        miseq_obj.assemblies.name = assembly_zip + ".zip"

        shutil.make_archive(report_zip, 'zip', report_path)
        miseq_obj.reports.name = report_zip + ".zip"
    else:
        miseq_obj.error = "Something Went Wrong, Sorry!"

    miseq_obj.job_id = '0'
    miseq_obj.save()'''


@app.task(bind=True)
def spades_test(self, obj_id):
    print self

    obj = Data.objects.get(id=obj_id)
    obj.job_id = '1'
    path = 'documents/Spades/%s/' % obj_id
    print path
    call(['python', '../../SPAdes/bin/spades.py', '--test', '-o', path])
    obj.spadesresults.name = path+'scaffolds.fasta'
    obj.job_id = '0'
    obj.save()


@app.task(bind=True)
def primer_validator_task(self, obj_id):
    print self

    # Retrieve the database object to give results to
    obj = PrimerV.objects.get(id=obj_id)

    # Get unique Task ID and save to obj
    job_id = primer_validator_task.request.id
    obj.job_id = job_id
    obj.save()

    # Print user details of the job
    print 'User: %s, ID: %s' % (obj.user, obj_id)

    # Retrieve variables from obj model
    target = str(obj.target)
    forward = obj.forward
    reverse = obj.reverse
    mism = obj.mism

    # Strain totals are stored in an external file that can be modified whenever hashes are modified
    with open('documents/Current_Hashes/hash_info.json') as f:
        strain_totals = json.loads(f.read())
    print strain_totals

    # Collect results of and add to the results list
    items_list = primer_validator_function(forward, reverse, target, mism)

    # Count number of unique strains
    matches = set()
    for item in items_list:
        matches.add(item['seq'])

    matches_length = str(len(matches))
    strains = "%s/%s" % (matches_length, strain_totals[target.replace(".hash", "")])

    # Adds all unmatched entries into a list of dictionaries and produces a file report
    path_dir = 'documents/primer_validator/%s' % obj.user
    path_misses = path_dir + '/%s_misses.txt' % obj_id
    path_hits = path_dir + '/%s.csv' % obj_id
    no_matches = []

    target_file = target.replace('.hash', '.txt')
    file_open = 'documents/Current_Hashes/%s' % target_file

    if not os.path.exists(path_dir):
        os.makedirs(path_dir)

    with open(file_open, 'r') as f:
        lines = [x.strip('\n') for x in f.readlines()]
        for line in lines:
            count = 0
            for item in items_list:
                if line in item['seq']:
                    count += 1
            if count == 0:
                no_matches.append(line)
        with open(path_misses, 'w+') as f2:
            for f2_item in no_matches:
                f2.write("%s\n" % f2_item)

    # Write dictionary to this file for easy retrieval
    keys = ['mism', 'from', 'seq', 'to', 'length', 'gaps', 'link',
            'alignment', 'strand']
    with open(path_hits, 'w+') as output_file:
        dict_writer = csv.DictWriter(output_file, keys)
        dict_writer.writeheader()
        dict_writer.writerows(items_list)

    obj.result.name = path_hits
    obj.misses.name = path_misses

    # Job has completed, remove the ID from the model
    obj.job_id = ''
    obj.hits = strains
    obj.save()


@app.task(bind=True)
def gene_seeker_task(self, obj_id):
    ''' GeneSeekR Performs gene detection on fastq and fasta files. It uses either SRST2 for FastQ, or GeneSeekR for
        fasta. This function is divided into a fastq path, and two fasta paths (one for custom genomes, the other for
        the premade databases
    :param self:
    :param obj_id: ID of the GeneS object
    :return: None
    '''
    print self

    # Retrieve object from database
    obj = GeneS.objects.get(id=obj_id)
    print "Starting GeneSeekR Task %s for User: %s" % (obj_id, obj.user)

    # Prepare working directory
    working_dir = 'documents/GeneSeeker/%s/%s' % (obj.user, obj.id)
    target_path = os.path.join(working_dir, 'targets')
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    if not os.path.exists(target_path):
        os.makedirs(target_path)

    genes = obj.genes
    cutoff = obj.cutoff
    organism = obj.organism

    if obj.type == 'fastq':
        # Retrieve the project object associated with GeneS object, copy over every associated file to working dir and
        # perform SRST2 via a docker container

        project_obj = Project.objects.get(id=obj.job_id)
        data_files = project_obj.files.all()
        cutoff = str(100 - int(cutoff))

        print "Copying Project Files Over to GeneSeekR Working Dir"
        for f in data_files:
            path = os.path.split(f.file.name)
            end_path = os.path.join(working_dir, path[1])
            print "Copying from %s to %s" % (f.file.name, end_path)
            shutil.copyfile(f.file.name, end_path)

        if genes == "OtherTarget":
            target_start_path = srst2_formatter(obj.targets.name)
            target_name = os.path.split(target_start_path)[1]
            target_end_path = os.path.join(working_dir, target_name)
            print "Copying Custom Target File Over to GeneSeekR Working Dir"
            shutil.copyfile(target_start_path, target_end_path)
        else:
            target_start_path = 'documents/Targets/SRST2/%s_SRST2.fasta' % genes
            target_name = os.path.split(target_start_path)[1]
            target_end_path = os.path.join(working_dir, target_name)
            print "Copying Default Target File Over to GeneSeekR Working Dir"
            shutil.copyfile(target_start_path, target_end_path)

        print 'Running Gene Seeker SRST2'
        try:
            call(['docker', 'run', '-v', os.path.abspath(working_dir)+':/app/documents',
                  '-e', 'INPUT=app/documents', '-e', 'VAR1=GeneSeekR', '-e', 'VAR2='+cutoff, 'srst2'])

            print "Saving Results Now"
            # Assign file to database entry for results if it exists, and is not empty
            results_file = glob.glob(working_dir + '/*fullgenes*.txt')
            if len(results_file) == 1 and os.path.getsize(results_file[0]) != 0:
                obj.result.name = results_file[0]
                obj.job_id = ''
                obj.save()
            else:
                print "Something went wrong, failed GeneSeekR"
                obj.error = 'No Results'
                obj.save()
        except Exception as e:
            print "***ERROR", e.__doc__, e.message
            return False

    elif obj.type == 'fasta':
        if obj.job_id == '0':   # Start Premade Genomes for GeneSeekR
            genome_path = 'documents/Current_Genomes/%s' % organism
            genome_abs = os.path.abspath(genome_path)
        else:
            project_obj = Project.objects.get(id=obj.job_id)
            data_files = project_obj.files.all()
            print "Copying Project Files Over to GeneSeekR Working Dir"
            for f in data_files:
                path = os.path.split(f.file.name)
                end_path = os.path.join(working_dir, path[1])
                print "Copying from %s to %s" % (f.file.name, end_path)
                shutil.copyfile(f.file.name, end_path)
            genome_abs = os.path.abspath(working_dir)

        # Check for User Uploaded Targets or Select Premade Ones
        if genes == "OtherTarget":
            sequences = []
            target_start_path = obj.targets.name
            # Verify correctly formatted fasta file
            target_end_path = str(target_start_path).replace(".fasta", "_v.fasta")
            output_handle = open(target_end_path, "w")
            for record in SeqIO.parse(open(target_start_path, "rU"), "fasta"):
                sequences.append(record)
            if len(sequences) > 0:
                SeqIO.write(sequences, output_handle, "fasta")
                output_handle.close()
                obj.targets.name = target_end_path
                obj.save()
                target_abs = os.path.abspath(target_end_path)
            else:
                print "ERROR: Improper Formatted Fasta"
                obj.error = "Error"
                obj.save()
                return
        else:
            target_start_path = 'documents/Targets/%s.fasta' % genes
            target_abs = os.path.abspath(target_start_path)

        results_abs = os.path.abspath(working_dir)

        print 'GeneSeekr %s -m %s -o %s -c %s' % (genome_abs, target_abs, results_abs, cutoff)

        # Notoriously unreliable program
        try:

            call(['GeneSeekr', genome_abs, '-m', target_abs, '-o', results_abs, '-c', cutoff])

            print "Saving Results Now"
            # Assign file to database entry for results if it exists, and is not empty
            results_file = glob.glob(working_dir + '/*.csv')
            if len(results_file) == 1 and os.path.getsize(results_file[0]) != 0:
                obj.result.name = results_file[0]
                obj.job_id = ''
                obj.save()
            else:
                print "Something went wrong, failed GeneSeekR"
                obj.error = 'No Results'
                obj.save()

        except Exception as e:
            print "Error, GeneSeekr Failed!", e.__doc__, e.message
            obj.error = "Error"
            obj.save()

    print "Removing Temporary Files"
    # Remove temp files, just the fasta genomes. Target folder and results remain
    if obj.targets:
        user_targets = os.path.split(obj.targets.name)[1]
        for root, dirs, files in os.walk(working_dir, topdown=False):
            for name in files:
                if 'results' in str(name) or str(name) == user_targets:
                    print "Not Going to Delete", name
                else:
                    os.remove(os.path.join(root, name))
    else:
        for root, dirs, files in os.walk(working_dir, topdown=False):
            for name in files:
                if 'results' in str(name):
                    print "Not Going to Delete", name
                else:
                    os.remove(os.path.join(root, name))


@app.task(bind=True)
def ksnp_task(self, obj_id):
    print self

    # Retrieve object from database
    obj = SNP.objects.get(id=obj_id)

    # Print user details of the job
    print "Starting kSNP Task"
    s = 'User: %s, ID: %s' % (obj.user, obj_id)
    print s

    genome_path = 'documents/kSNP/%d' % obj_id
    docker_path = "/home/ubuntu/nas0/Genomics_Portal/%s" % genome_path
    results_path = 'documents/kSNP/%d/Results/SNPs_all' % obj_id
    snps_path = 'documents/kSNP/%d/Results/COUNT_SNPs' % obj_id
    tree_path = 'documents/kSNP/%d/Results/outtree.resolved' % obj_id

    # Unzip any files
    if 'zip' in obj.genome.name:
        with zipfile.ZipFile(obj.genome.name, 'r') as myzip:
            myzip.extractall(genome_path)

    # Spin Up Docker Container, Takes a maximum of 2 hours to finish
    docker_spinner(docker_path, obj_id, 0, 0, 0, 'ksnp', 6, 6000)

    print "Saving Results Now"
    # Save generated results to database

    with open(snps_path) as f:
        line = f.readline()
        snps = line.split(':')[1]

    f = glob.glob(results_path)
    tree = glob.glob(tree_path)
    print f

    if len(f) > 0:
        obj.result.name = f[0]
    if len(tree) > 0:
        obj.tree.name = tree[0]

    obj.snps = snps
    obj.job_id = ''
    obj.save()


@app.task(bind=True)
def ksnpfastq_task(self, obj_id):
    print self

    # Retrieve object from database
    obj = SNP.objects.get(id=obj_id)
    project_obj = Project.objects.get(id=obj.data_id)

    # Print user details of the job
    print "Starting kSNP FastQ Task %s for User: %s" % (obj_id, obj.user)

    # Copy FASTQ Files to Working Directory
    data_path = 'documents/SNP/%s' % obj_id
    data_files = project_obj.files.all()

    docker_path = "/home/ubuntu/nas0/Genomics_Portal/%s" % data_path

    print "Copying FastQ Files Over to SNP Working Dir"
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    for f in data_files:
        path = f.file.name.split('/')[-1]
        end_path = data_path + '/' + path
        print "Copying from %s to %s" % (f.file.name, end_path)
        shutil.copyfile(f.file.name, end_path)

    # Spin Up Docker Container, Takes a maximum of 2 hours to finish
    docker_spinner(docker_path, obj_id, 0, 0, 0, 'ksnp', 6, 6000)

    print "Saving Results Now"

    results_path = 'documents/SNP/%d/Results/SNPs_all' % obj_id
    snps_path = 'documents/SNP/%d/Results/COUNT_SNPs' % obj_id
    tree_path = 'documents/SNP/%d/Results/outtree.resolved' % obj_id

    snps_file = glob.glob(snps_path)
    snps = "0"
    if len(snps_file) > 0:
        with open(snps_path) as f:
            line = f.readline()
            snps = line.split(':')[1]

    f = glob.glob(results_path)
    tree = glob.glob(tree_path)
    print f

    if len(f) > 0:
        obj.result.name = f[0]
    if len(tree) > 0:
        obj.tree.name = tree[0]

    obj.snps = snps
    obj.job_id = ''
    obj.save()

    print "Removing Temporary Files"
    filelist = glob.glob(data_path + '/*fastq.gz')
    for f in filelist:
        os.remove(f)


@app.task(bind=True)
def mmlst_task(self, obj_id):
    print self

    # Retrieve objects from database
    project_obj = Project.objects.get(id=obj_id)
    data_files = project_obj.files.all()
    organism = determine_organism(project_obj.organism, 'MLST')

    if not organism:
        return

    print "Starting mMLST  Task %s for User: %s" % (obj_id, project_obj.user)

    mlst_object = MLST(user=project_obj.user, tag=project_obj.description, organism=organism,
                       type=project_obj.type, job_id='1', project=project_obj)
    mlst_object.save()

    # Now that MLST object has an id, create the working dir
    working_dir = 'documents/MLST/%s/%s' % (mlst_object.user, mlst_object.id)
    if not os.path.exists(working_dir):
        os.makedirs(working_dir)
    # Create a unique MLST object for every fasta file and copy over the fasta to working dir
    error_boolean = False
    for data in data_files:
        path = data.file.name.split('/')[-1]
        end_path = os.path.join(working_dir, path)
        print "Copying from %s to %s" % (data.file.name, end_path)
        shutil.copyfile(data.file.name, end_path)

    # Run mMLST on working dir
    # Translate project description organism into one that matches name of MLST profile, or False if no match

    mlst_path = 'documents/Targets/MLST/%s' % organism
    rmlst_path = 'documents/Targets/rMLST'

    try:
        if project_obj.type == 'fastq':
            print "Copying MLST Databases Over to MLST Working Dir"

            # Folders here must match project possible formats
            source_dir = 'documents/Targets/MLST/%s/' % organism
            #source_dir = 'documents/Targets/rMLST/'
            for filename in glob.glob(os.path.join(source_dir, '*.*')):
                shutil.copy(filename, working_dir)
            call(['docker', 'run', '-v', os.path.abspath(working_dir)+':/app/documents',
                  '-e', 'INPUT=app/documents', '-e', 'VAR1=MLST', 'srst2'])

            print "Saving Results Now"
            result_file = glob.glob(os.path.join(working_dir, '*results.txt'))
            if len(result_file) == 1:
                mlst_object.job_id = ''
                mlst_object.result.name = result_file[0]
                mlst_object.save()
            else:
                raise ValueError('No Result File Generated')
        elif project_obj.type == 'fasta':
                if organism:
                    call(['python', 'mMLST.py', '-s', working_dir, '-a', mlst_path, '-r', working_dir])
                    result_file = glob.glob(os.path.join(working_dir, 'MLST*.csv'))
                    if len(result_file) == 1:
                        mlst_object.result.name = result_file[0]

                    call(['python', 'mMLST.py', '-s', working_dir, '-a', rmlst_path, '-r', working_dir,
                          '-R', 'documents/Targets/referenceGenomes', '-t', 'rMLST', '-b'])
                    result_file = glob.glob(os.path.join(working_dir, 'rMLST*.csv'))
                    if len(result_file) == 1:
                        mlst_object.rmlst_result.name = result_file[0]

                    reference_path = os.path.join(working_dir, 'referencegenomes.csv')
                    if os.path.isfile(reference_path):
                        mlst_object.reference.name = reference_path

                    # Turn off running job variable
                    mlst_object.job_id = ''
                    mlst_object.save()

                else:
                    call(['python', 'mMLST.py', '-s', working_dir, '-a', rmlst_path, '-r', working_dir,
                          '-R', './referenceGenomes', '-t', 'rMLST', '-b'])
                    result_file = glob.glob(os.path.join(working_dir, 'rMLST*.csv'))
                    if len(result_file) == 1:
                        mlst_object.rmlst_result.name = result_file[0]

                    reference_path = os.path.join(working_dir, 'referencegenomes.csv')
                    if os.path.isfile(reference_path):
                        mlst_object.reference.name = reference_path

                    mlst_object.job_id = ''
                    mlst_object.save()

    except Exception as e:
            error_boolean = True
            print "Error, mMLST Failed!", e.__doc__, e.message
            mlst_object.error = "Error, Something Went Wrong"
            mlst_object.save()

    if error_boolean:
        project_obj.mlst_results = "Error"
    else:
        project_obj.mlst_results = 'Done'
    project_obj.save()

    print "Removing Temporary Files"
    # First move files to trash folder, copy log files out, delete directory
    for root, dirs, files in os.walk(working_dir, topdown=False):
        for name in files:
            if 'csv' in str(name) or 'results' in str(name):
                print "Not Going to Delete", name
            else:
                os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


@app.task(bind=True)
def amr_fasta_task(self, obj_id):
    print self

    project_obj = Project.objects.get(id=obj_id)
    data_files = project_obj.files.all()

    print "Starting AMR  Task %s for User: %s" % (obj_id, project_obj.user)

    # Create a unique AMR object for every fasta file and copy over the fasta to working dir
    amr_object_list = []
    for data in data_files:
        print project_obj.description
        print len(project_obj.description)
        amr_object = AMR(user=project_obj.user, tag=project_obj.description, organism=project_obj.organism,
                         type=project_obj.type, job_id='1', project=project_obj)
        amr_object.save()
        amr_object_list.append(amr_object)

        path = data.file.name.split('/')[-1]
        working_dir = 'documents/AMR/%s/%s' % (amr_object.user, amr_object.id)
        end_path = os.path.join(working_dir, path)

        print "Copying from %s to %s" % (data.file.name, end_path)
        if not os.path.exists(working_dir):
            os.makedirs(working_dir)
        shutil.copyfile(data.file.name, end_path)
        amr_object.genome.name = end_path
        amr_object.save()

    error_boolean = False

    for amr_object in amr_object_list:
        working_dir = 'documents/AMR/%s/%s/' % (amr_object.user, amr_object.id)

        try:
            print "Running ARMI"
            print 'python ARMI/ARMIv2.py -i %s -m ARMI/ARMI-genes.fa -o %s -t ARMI/aro3.json' \
                  % (working_dir, os.path.join(working_dir, 'ARMI'))

            armi_dir = os.path.join(working_dir, 'ARMI')
            if not os.path.exists(armi_dir):
                os.makedirs(armi_dir)

            call(['ARMI', working_dir, '-o', os.path.join(working_dir, 'ARMI')])

            # Run blast for every unzipped genome for both ARG-ANNOT and ResFinder
            print "Running BLAST"
            p = amr_object.genome.name
            p_nofasta = p.replace(".fasta", "")
            re = p_nofasta + "_arg_results.csv"
            re2 = p_nofasta + "_arg_blast.txt"
            re3 = p_nofasta + "_res_results.csv"
            re4 = p_nofasta + "_res_blast.txt"

            # Generate the Blast Reformat 10 Output for ARG-ANNOT
            with open(re, "a") as f:
                call(['blastn', '-db', 'documents/AMR/argannot', '-query', p, '-outfmt',
                      '10 qacc sacc qlen slen length nident'], stdout=f)

            # Generate the full Blast Output for ARG-ANNOT
            with open(re2, "a") as g:
                call(['blastn', '-db', 'documents/AMR/argannot', '-query', p, '-outfmt', '0'], stdout=g)

            # Generate the Blast Reformat 10 Output for ResFinder
            with open(re3, "a") as h:
                call(['blastn', '-db', 'documents/AMR/resfinder', '-query', p, '-outfmt',
                      '10 qacc sacc qlen slen length nident'], stdout=h)

            # Generate the full Blast Output for ResFinder
            with open(re4, "a") as i:
                call(['blastn', '-db', 'documents/AMR/resfinder', '-query', p, '-outfmt', '0'], stdout=i)

            # Save BLAST result file locations to database and turn off running task integer.
            # Only add results if file not empty
            print "Saving Results to Database"
            if os.stat(re).st_size != 0:
                amr_object.result.name = re
            amr_object.result2.name = re2

            if os.stat(re3).st_size != 0:
                amr_object.result3.name = re3
            amr_object.result4.name = re4

            # Save ARMI Results, Check file exists, if so, make sure it actually contains results
            armi_result_path =  os.path.join(working_dir,'ARMI')
            print armi_result_path
            file_list = glob.glob(os.path.join(armi_result_path, 'ARMI_results*.json'))
            if len(file_list) == 1:
                contains_results = False
                #with open(file_list[0], 'rt') as f:
                #    lines = f.readlines()
                #    for line in lines:
                #        if '+' in line:
                #            contains_results = True
                            #break
                #if contains_results:
                print "Found Some ARMI Hits"
                amr_object.result5.name = file_list[0]

            amr_object.job_id = ""
            amr_object.save()

            '''print "Removing Temporary Files"
            filelist = glob.glob(working_dir + '/*')
            for name in filelist:
                # Permanently Delete all temporary files and the copied FastQ files
                if '.fasta' in name:
                    os.remove(name)
            tmp_path = os.path.join(armi_result_path, 'tmp')
            shutil.rmtree(tmp_path)'''

        except Exception as e:
             error_boolean = True
             print "Error, Blastn failed!", e.__doc__, e.message
             amr_object.error = "Error, Something Went Wrong"
             amr_object.save()

    # Wrap up Project completion indicator
    if error_boolean:
        project_obj.amr_results = "Error"
    else:
        project_obj.amr_results = "Done"
    project_obj.save()


@app.task(bind=True)
def amr_fastq_task(self, obj_id):
    print self

    # Retrieve objects from database
    project_obj = Project.objects.get(id=obj_id)
    data_files = project_obj.files.all()

    # Create the AMR database object
    amr_obj = AMR(user=project_obj.user, tag=project_obj.description, organism=project_obj.organism,
                  type=project_obj.type, job_id='1', project=project_obj)
    amr_obj.save()

    # Copy FASTQ Files to Working Directory
    data_path = 'documents/AMR/%s/%s' % (amr_obj.user, amr_obj.id)

    print "Copying FastQ Files Over to AMR Working Dir"
    if not os.path.exists(data_path):
        os.makedirs(data_path)
    for f in data_files:
        path = f.file.name.split('/')[-1]
        end_path = data_path + '/' + path
        print "Copying from %s to %s" % (f.file.name, end_path)
        shutil.copyfile(f.file.name, end_path)

    print "Copying AMR Databases Over to AMR Working Dir"
    path_arg = 'documents/Targets/ARGannot.r1.fasta'
    path_res = 'documents/Targets/ResFinder.fasta'
    end_arg = os.path.join(data_path,'ARGannot.fasta')
    end_res = os.path.join(data_path, 'ResFinder.fasta')

    shutil.copyfile(path_arg, end_arg)
    shutil.copyfile(path_res, end_res)

    '''# Spin Up Docker Container, Takes a maximum of 2 hours to finish
    docker_path = os.path.join(NAS_MOUNT_VOLUME,'AMR')
    docker_user_path = '%s/%s' % (amr_obj.user, amr_obj.id)
    print "Starting ARMI Analysis"
    docker_spinner(docker_path, obj_id, 'a', docker_user_path, 0, 'genesipprv2node', 12, 48000)



    print "Saving ARMI Results Now"
    for root, dirs, files in os.walk(data_path, topdown=False):
        for name in files:
            if 'results.tsv' in str(name):
                shutil.move(os.path.join(root,name),data_path)
                amr_obj.result.name = os.path.join(data_path, name)
                amr_obj.save()

    print "Starting SRST2 AMR Analysis"
    docker_path = NAS_MOUNT_VOLUME + 'AMR/%s/%s' % (amr_obj.user, amr_obj.id)
    docker_spinner(docker_path, obj_id, 'AMR', 0, 0, 'srst2', 12, 12000)
    '''

    call(['docker', 'run', '-v', os.path.abspath(data_path)+':/app/documents', '-e', 'INPUT=app/documents', '-e',
          'VAR1=AMR', '-e', 'VAR2=10', 'srst2'])

    print "Saving SRST2 Results Now"
    result_file = glob.glob(os.path.join(data_path, '*fullgenes*.txt'))
    if len(result_file) > 0:
        for result in result_file:
            if "ARGannot" in result:
                amr_obj.result.name = os.path.join(data_path, 'AMR__fullgenes__ARGannot__results.txt')
            elif "ResFinder" in result:
                amr_obj.result3.name = os.path.join(data_path, 'AMR__fullgenes__ResFinder__results.txt')

        project_obj.amr_results = 'Done'
        project_obj.save()

    else:
        print "No Results Found :("
        project_obj.amr_results = 'Error'
        project_obj.save()
        amr_obj.error = "No Results"
        amr_obj.save()

    amr_obj.job_id = ''
    amr_obj.save()

    print "Removing Temporary Files"
    for root, dirs, files in os.walk(data_path, topdown=False):
        for name in files:
            if 'results' in str(name):
                print "Not Going to Delete", name
            else:
                os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


@app.task(bind=True)
def gene_seeker_fastq_task(self, obj_id):
    print self

    # Retrieve objects and their respective files from database
    gene_obj = GeneS.objects.get(id=obj_id)
    print "Starting GeneSeekR FastQ Task %s for User: %s" % (obj_id, gene_obj.user)

    project_obj = Project.objects.get(id=gene_obj.job_id)
    data_files = project_obj.files.all()

    # Internal Folder Structure of the Website
    data_path = 'documents/GeneSeeker/%s/%s' % (gene_obj.user, gene_obj.id)
    target_path = 'documents/GeneSeeker/%s/%s/targets/' % (gene_obj.user, gene_obj.id)

    # Docker Path is the location folder to mount into the docker container
    docker_path = "%s/GeneSeeker/%s/%s" % (NAS_MOUNT_VOLUME, gene_obj.user, gene_obj.id)

    print "Copying FastQ Files Over to GeneSeeker Working Dir at %s" % docker_path
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    for data in data_files:
        path = data.file.name.split('/')[-1]
        end_path = data_path + '/' + path
        print "Copying from %s to %s" % (data.file.name, end_path)
        shutil.copyfile(data.file.name, end_path)

    print "Copying Fasta Databases Over to GeneSeeker Working Dir"
    if gene_obj.genes == 'OtherTarget':
        path_targets = gene_obj.usertargets.name

        # Unzip any files
        print "Unzipping Files"
        if 'zip' in path_targets:
            with zipfile.ZipFile(path_targets, 'r') as myzip:
                myzip.extractall(target_path)

        # Reformat Fasta Files to Accomodate SRST2
        print "Formatting Fasta Files"
        filelist = glob.glob(target_path + '/*.fasta')
        count = 0
        for f in filelist:
            genomename = f.split("/")[-1].split(".")[0]
            handle = open(f)
            records = SeqIO.parse(handle, 'fasta')
            for record in records:
                record.id = record.id.replace("__", "")
                record.id = str(count) + "__" + genomename + "__" + str(count) + "__" + "1" + "__" + record.id
                count += 1
                SeqIO.write(record, f, 'fasta')
            handle.close()

        # Add all fasta files together into 1 file
        print "Merging Files"
        file_name = gene_obj.usertargets.name
        file_name = file_name.split("/")[-1].split(".")[0]
        outfilename = target_path + '/%s_DB.fasta' % file_name
        filelist = glob.glob(target_path + '/*.fasta')
        if len(filelist) > 0:
            with open(outfilename, 'w') as outfile:
                for fname in filelist:
                    with open(fname) as infile:
                        for line in infile:
                            outfile.write(line)
        else:
            print 'No Fasta Files Present!'

        end_path = data_path + '/%s_DB.fasta' % file_name
        shutil.copyfile(outfilename, end_path)

    # Otherwise use the preformatted virulence databases (EColi, Salmonella, Listeria) only
    else:
        path_targets = 'documents/Targets/SRST2/%s_SRST2.fasta' % gene_obj.genes
        end_path = data_path + '/%s_SRST2.fasta' % gene_obj.genes
        shutil.copyfile(path_targets, end_path)

    print 'Running SRST2 Gene Detection'
    # Spin Up Docker Container, Takes a maximum of 2 hours to finish
    #docker_spinner(docker_path, obj_id, 'GeneSeekR', 0, 0, 'srst2', 6, 6000)
    call(['docker', 'run', '-e', 'VAR1=GeneSeekR', '-e', 'INPUT=/app/documents', '-v', os.path.abspath(data_path)+':/app/documents', '--rm=True', '192.168.1.5:5000/srst2'])

    print "Saving Results Now"
    result_file = glob.glob(os.path.join(data_path, '*fullgenes*.txt'))
    if len(result_file) > 0:
        gene_obj.result.name = result_file[0]

        # If this is the first time Project has been made, assign first results here
        if project_obj.geneseekr_results == "False":
            print "Saving Results For the First Time"
            project_obj.geneseekr_results = gene_obj.id
            project_obj.save()
    else:
        print "No Results Found :("
        project_obj.geneseekr_results = 'None'
        project_obj.save()

    gene_obj.job_id = ''
    gene_obj.save()

    print "Removing Temporary Files"
    filelist = glob.glob(data_path + '/*')
    for name in filelist:
        # Permanently Delete all temporary files and the copied FastQ files
        if 'results' not in name:
            os.remove(name)


@app.task(bind=True)
def genesippr_task(self, obj_id):
    print self

    proj_obj = Project.objects.get(id=obj_id)
    print proj_obj.id
    # Retrieve objects and their respective files from database
    #gene_obj = GeneS.objects.get(id=obj_id)
    print "Starting GeneSipprV2 Task %s for User: %s" % (obj_id, proj_obj.user)

    data_files = proj_obj.files.all()
    print data_files

    # Internal Folder Structure of the Website
    data_path = 'documents/GeneSippR/%s/%s' % (proj_obj.user, proj_obj.id)
    docker_user_path = '/%s/%s' % (proj_obj.user, proj_obj.id)

    # Docker Path is the location folder to mount into the docker container
    docker_path = "%s/GeneSippR/" % (NAS_MOUNT_VOLUME)

    print "Copying FastQ Files Over to GeneSeeker Working Dir at %s" % docker_path
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    for data in data_files:
        path = data.file.name.split('/')[-1]
        end_path = data_path + '/' + path
        print "Copying from %s to %s" % (data.file.name, end_path)
        shutil.copyfile(data.file.name, end_path)

    print 'Running GeneSippR'
    # Spin Up Docker Container, Takes a maximum of 2 hours to finish
    call(['python', '/home/eyresj/Programs/geneSipprV2/geneSipprV2.py', '-p', os.path.abspath(data_path), '-t', os.path.abspath('documents/Targets'), '-s', os.path.abspath(data_path), '-16S'])
    #docker_spinner(docker_path, obj_id, '16S', docker_user_path, 0, 'genesipprv2node', 12, 24000)

    print "Saving Results Now"
    for root, dirs, files in os.walk(data_path, topdown=False):
        for name in files:
            sixteen_s = '16S_results.tsv'
            if sixteen_s in str(name):
                shutil.move(os.path.join(root, name),data_path)

    # Check for that file  and examine it
    result_file = os.path.join(data_path, sixteen_s)
    if os.path.isfile(result_file):
        with open(result_file) as f:
            lines = f.readlines()
            if len(lines) == 2:
                species = lines[1].split(',')[1]
                proj_obj.organism = species
                proj_obj.save()
    else:
        print "No Results Found :("
        proj_obj.organism = 'Unknown'
        proj_obj.save()

    print "Removing Temporary Files"
    for root, dirs, files in os.walk(data_path, topdown=False):
        for name in files:
            sixteen_s = '16S_results.tsv'
            if sixteen_s in str(name):
                print "Not Going to Delete", name
            else:
                os.remove(os.path.join(root, name))

        for name in dirs:
            os.rmdir(os.path.join(root, name))


@app.task(bind=True)
def test_task(self, obj_id):
    print self

    # Retrieve objects from database
    g_obj = Galaxy.objects.get(id=obj_id)
    data_obj = Data.objects.get(id=g_obj.data_id)

    # Copy FASTQ Files to Working Directory
    data_path = 'documents/TEST/%s' % g_obj.id
    data_file = 'documents/TEST/%s/%s' % (g_obj.id, data_obj.name)
    # docker_path = "/home/ubuntu/nas0/Genomics_Portal/%s" % data_path

    print "Copying FastQ File Over to TEST Working Dir"
    if not os.path.exists(data_path):
        os.makedirs(data_path)

    shutil.copyfile(data_obj.file.name, data_file)

    # Unzip any files
    if 'zip' in data_file:
        with zipfile.ZipFile(data_file, 'r') as myzip:
            myzip.extractall(data_path)

    # Run Galaxy Test
    print 'Running Galaxy Test'
    forward = glob.glob(os.path.join(data_path, '*R1_001.fastq.gz'))
    reverse = glob.glob(os.path.join(data_path, '*R2_001.fastq.gz'))

    print 'python galaxyAPItest.py -r %s -F %s -F %s' % (g_obj.genome, forward[0], reverse[0])
    call(['python', 'galaxyAPItest.py', '-r', g_obj.genome.name, '-F', forward[0], '-R', reverse[0]])

    # Open Results file

    print "Saving Results Now"
    # Save generated results to database
    '''filelist= glob.glob(os.path.join(data_path, '*results.txt'))
    mlst_obj.result.name = filelist[0]
    mlst_obj.job_id = ''
    mlst_obj.save()'''

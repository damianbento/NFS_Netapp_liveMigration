#!/usr/bin/python3

from time import sleep
from datetime import datetime
from Subprocess import call
from sys import stdout
import paramiko


def ssh_command(cmd):

        ssh.connect(server, username=user, password=password)
        i, o, e = ssh.exec_command(cmd)
        output = o.read().decode().strip()
        error = e.read().decode().strip()

        return output, error


def select_vol(output):

        volumes = []

        for line in output.split('\n')[1:]:
                line2 = line.split(' ')

                try:
                        while True:
                                line2.remove('')
                except:
                        pass

                v = line2[0].replace('/vol/', '').replace('/', '')
                s = int(int(line2[1]) * 1.10)

                print(v, ' (%d)' % s)
                volumes.append((v, s))

        print('\nIngrese el nombre del volumen: ')
        volume = input()

        for v, s in volumes:
                if volume == v:
                        return (v, s)

        print('\n [-] volumen inexistente')


def select_aggr(output):

        aggrs = []

        for line in output.split('\n')[1:]:
                line2 = line.split(' ')
                aggrs.append(line2[0])

        print('\nIngrese el nombre del Aggr Destino: ')
        aggr = input()

        for v in aggrs:
                if aggr == v:
                        return aggr

        print('\n [-] Aggregate inexistente')


def error_exit(output, error):
        print('############### OUTPUT  ######################')
        print(output)
        print('############### ERROR  ######################')
        print(error)
        exit(1)


server = '10.120.0.103'
user = 'root'
password = 'netapp1234'


ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

output, error = ssh_command('df -x')
# print(output)

volume = None
while not volume:
        volume = select_vol(output)

print()
print()

output, error = ssh_command('df -Ahx')
print(output)

aggr = None
while not aggr:
        aggr = select_aggr(output)

print()
print()

output, error = ssh_command('exportfs -q /vol/%s/' % volume[0])
print('########### ATENCION !!!! ############\n')
print('ExportFS:')
print(output)

stdout('\nEsta seguro que desea migrar el volumen "{0}" al "{1}" con ese export de arriba"? [y/N]:'.format(
        volume[0], aggr))

r = input()

if r != 'y':
        exit()


output, error = ssh_command(
        'vol create %s_TMP -s none %s %dk' %
         (volume[0], aggr, volume[1]))
if 'has completed' not in output:
        error_exit(output, error)


output, error = ssh_command('vol restrict %s_TMP' % (volume[0]))
if 'is now restricted.' not in output:
        error_exit(output, error)


output, error = ssh_command(
    'snapmirror initialize -S {0} {0}_TMP'.format(volume[0]))
if 'Transfer started.' not in output:
        error_exit(output, error)

print('Hora de comienzo de migracion: %s' % datetime())

mirrored = False
while not mirrored:
        sleep(60)
        output, error = ssh_command(
            'snapmirror status -l {0}_TMP'.format(volume[0]))

        for line in output.split('\n'):
                if 'State' in line and 'Snapmirrored' in line:
                        mirrored = True
                        break
        call('clear')
        print(output)

# Verificar!

print('Finalizado')

output, error = ssh_command('snapmirror break {0}_TMP'.format(volume[0]))
if 'is now writable.' not in output:
        error_exit(output, error)

output, error = ssh_command('snapmirror status -l {0}_TMP'.format(volume[0]))

broken = False
for line in output.split('\n'):
        if 'State' in line and 'Broken-off' in line:
                broken = True
                break

if not broken:
        error_exit(output, error)

output, error = ssh_command('hostname'.format(volume[0]))
if 'FCORP' not in output:
        error_exit(output, error)

hostname = output

output, error = ssh_command(
        'snapmirror release {0} {1}:{0}_TMP'.format(
                volume[0], hostname))

if 'is now writable.' not in output:
        error_exit(output, error)

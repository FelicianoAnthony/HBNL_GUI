# GUI imports
from PyQt5.QtWidgets import (QMainWindow, QApplication, QPushButton, QWidget, QAction, 
                             QTabWidget,QVBoxLayout, QHBoxLayout, QInputDialog, QLineEdit, QLabel,
                             QFileDialog, QMainWindow, QPushButton, QTextEdit, QMessageBox, QCheckBox)
from PyQt5.QtGui import QIcon, QTextCursor, QFont, QPixmap
from PyQt5.QtCore import pyqtSlot, QCoreApplication, QProcess, QObject, pyqtSignal
import sys
import os

# ERP class imports
from glob import glob
from collections import defaultdict, Counter
import re
import subprocess
import shutil
from random import choice
import functools
from datetime import datetime


class erp_data:

    def __init__(self):

        # avg + ps exp names are the same
        self.avg_and_ps_exps = ['vp3', 'cpt', 'ern', 'ant', 'aod', 'anr', 'stp', 'gng']
        # number of files associated with avg extension 
        self.avg_exp_nums = [3,6,4,4,2,2,2,2]
        # cnt exp names
        self.cnt_exp_list = ['eeo', 'eec', 'vp3', 'cpt', 'ern', 'ant', 'aod', 'ans', 'stp', 'gng']
        # versions associated with erp 
        self.version_list = ['4', '4', '6', '4', '9', '6', '7', '5', '3', '3']
        # dat exp names 
        self.dat_exps = ['vp3', 'cpt', 'ern', 'ant', 'aod', 'ans', 'stp', 'gng']
        # only 1 exp for dat/cnt/ps
        self.exp_nums_single = [1] * len(self.cnt_exp_list)


    def check_erp_version(self, path, exp_name, version_num): 
        """
        returns whether ERP experiment version is correct 
        """
        self.path = path
        self.exp_name = exp_name
        self.version_num = version_num
        
        bad_version = []
        for r,d,f in os.walk(path):
            for n in f:
                split = n.split('_')
                if n.startswith((exp_name)):
                    if split[1] != version_num:
                        bad_version.append('Check version for {}'.format(n))
        return bad_version


    def iter_check_version(self, path, cnt_exp_list, version_list):
        """
        iterator version of check_erp_version()
        """
        self.path = path


        for exp, version in zip(self.cnt_exp_list, self.version_list):
            out = self.check_erp_version(path, exp, version)
            if len(out) == 0:
                pass
            else:
                return out


    def parse_site_data(self, path):
        """
        returns a nested dictionary of common/uncommon file extensions by experiment for a sub
        """
        self.path = path

        key = path.split('/')[-1]

        nested_dict = {}
        for r,d,f in os.walk(path):
            for n in f:
                if n.endswith('_32.cnt'):
                    cnts = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('cnt', []).append(cnts[0])
                if n.endswith('dat'):
                    dats = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('dat', []).append(dats[0])
                if n.endswith('_avg.ps'):
                    pss = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('ps', []).append(pss[0])
                if n.endswith('.avg'):
                    avgs = re.split(r'[_.]', n)
                    nested_dict.setdefault(key, {}).setdefault('avg', []).append(avgs[0])
                if n.endswith('_orig.cnt'):
                    origs = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('orig_cnt', []).append(origs[0])
                if n.endswith('_32_original.cnt'):
                    bad_orig = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('bad_orig', []).append(bad_orig[0])
                if n.endswith('_rr.cnt'):
                    reruns = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('rerun', []).append(reruns[0])
                if n.endswith('_cnt.h1'):
                    cnt_h1 = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('cnt_h1', []).append(cnt_h1[0])
                if n.endswith('_avg.h1'):
                    avg_h1 = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('h1', []).append(avg_h1[0])
                if n.endswith('_avg.h1.ps'):
                    h1_ps = n.split('_')
                    nested_dict.setdefault(key, {}).setdefault('h1_ps', []).append(h1_ps[0])
                # newly added -- for 2nd vp3 runs mostly
                sp = n.split('_')
                if n.endswith('_32.cnt') and sp[2][1] == '2':
                    nested_dict.setdefault(key, {}).setdefault('rerun', []).append(sp[0])

        return nested_dict


    def remove_wild_files(self, path):
        """
        prompts user to delete file extensions that don't belong in ns folders
        """
        self.path = path
        wild_files = []
        for r,d,f in os.walk(path):
            for n in f:
                if n.endswith(('_rr.cnt', '_32.cnt', '_orig.cnt', 'avg', 'avg.ps', 'dat', 'txt', 'sub')):
                    pass
                else:
                    wild_files.append(os.path.join(r,n))
                    
        return wild_files
                    


    def get_ext_count(self, path, nested_dict, ext_type, exp_name, number_files):
        """
        checks nested dictionary for number of extensions associated with each experiment
        e.g. checks that there's 6 CPT avg files or 1 EEC cnt file...
        """

        self.path = path
        self.nested_dict = nested_dict
        self.ext_type = ext_type
        self.exp_name = exp_name
        self.number_files = number_files

        missing_files = []
        for k,v in nested_dict.items():
            for k1, v1 in v.items():
                if ext_type == k1:
                    num_files = v1.count(exp_name)
                    if num_files != number_files:
                        missing_files.append('Incorrect number of {} {} files in {}'.format(exp_name, ext_type, path))
        return missing_files

    # get_ext_count()
    def iter_exps(self, path, nested_dict, exp_list, exp_list_avgs, ext_type):
        """
        iterator version of iter_exps()
        """
        self.path = path
        self.exp_list = exp_list
        self.exp_list_avgs = exp_list_avgs
        self.ext_type = ext_type
        
        new_lst = []
        for exp, avg_nums in zip(exp_list, exp_list_avgs):
            new_lst.extend(self.get_ext_count(path, nested_dict, ext_type, exp, avg_nums))
        if len(new_lst) == 0:
            pass
        else:
            return new_lst



    def check_id_and_run(self, path):
        """
        checks to see if important file extensions have same sub ID & run letter
        """
        self.path = path

        folder = path.split('/')[-1]

        sub_id_list = []
        run_letter_list = []

        for file in glob(os.path.join(path, '*.*')):
            if file.endswith(('_32.cnt', '_orig.cnt', '_avg.ps', '.avg', 'dat')):
                fname = os.path.basename(file)
                if not fname.endswith(('avg', 'dat')):
                    sub_id = fname.split('_')[3]
                    sub_id_list.append(sub_id)
                else:
                    avg_dat_ids = re.split(r'[_.A-Z]', fname)
                    sub_id_list.append(avg_dat_ids[3])

                # append run letters 
                run_letter_list.append(fname.split('_')[2][0])


        unique_ids = list(set(sub_id_list))
        unique_run_letters = list(set(run_letter_list))

        if  len(unique_ids) > 1:
            return str("Folder {} has more than one sub ID => {}".format(folder, unique_ids))

        if len(unique_run_letters) > 1:
            return str("Folder {} has more than one run letter => {}".format(folder, unique_run_letters))


    def print_erp_version(self, path, cnt_exp_list, version_list):
        """
        check erp version 
        """

        self.path = path

        print('\n\nERP VERSION CHECK:')

        iter_check = self.iter_check_version(path, self.cnt_exp_list, self.version_list)
        if  iter_check is None:
            print('All versions check out!')
        else:
            for i in iter_check:
                print(i)


    def print_file_counts(self, nested_data_dict):
        """
        returns counts of file extensions
        """

        self.nested_data_dict = nested_data_dict

        print('\n\nFILES COUNT:')
        for k,v in nested_data_dict.items():
            for k1,v1 in v.items():
                print("There are {} {} files".format(len(v1), k1.upper()))


    def print_missing_exps(self, path, nested_data_dict):
        """
        returns file type that's missing, if any 
        """
        self.path = path
        self.nested_data_dict = nested_data_dict

        print('\n\nMissing Experiments:')


        avg_counts = self.iter_exps(path, nested_data_dict, self.avg_and_ps_exps, self.avg_exp_nums, 'avg')

        if avg_counts is None:
            print('All avg files found!')
        else:
            for missing_avg in avg_counts:
                print(missing_avg)
            print('\n')


        cnt_counts = self.iter_exps(path, nested_data_dict, self.cnt_exp_list, self.exp_nums_single, 'cnt')
        if cnt_counts is None:
            print('All cnt files found!')
        else:
            for missing_cnt in cnt_counts:
                print(missing_cnt)
            print('\n')


        ps_counts = self.iter_exps(path, nested_data_dict, self.avg_and_ps_exps, self.exp_nums_single, 'ps')
        if ps_counts is None:
            print('All ps files found!')
        else:
            for missing_ps in ps_counts:
                print(missing_ps)
            print('\n')


        dat_counts = self.iter_exps(path, nested_data_dict, self.dat_exps, self.exp_nums_single, 'dat')
        if dat_counts is None:
            print('All dat files found!')
        else:
            for missing_dat in dat_counts:
                print(missing_dat)
            print('\n')


    def print_wild_files(self, path):
        """
        returns files that don't belong
        """
        self.path = path
        
        wild_files =  self.remove_wild_files(path)
        
        print("\n\nFILES THAT DON'T BELONG IN NS FOLDERS:")
        if len(wild_files) == 0:
            print('No wild files found!')
        else:
            for i in wild_files:
                print(i)


    def print_id_and_letter(self, path):
        """
        returns ID & run letter, should both be unique
        """
        self.path = path

        print('\n\nCHECK SUBJECT ID & RUN LETTER:')

        if self.check_id_and_run(path) is None:
            print('All IDs & run letters check out!')
        else:
            print(self.check_id_and_run(path))


    def run_all(self, path):
        """
        2nd to last step 
        """
        self.path = path

        nested_data_dict = self.parse_site_data(path)

        self.print_erp_version(path, self.cnt_exp_list, self.version_list)
        self.print_wild_files(path)
        self.print_file_counts(nested_data_dict)
        self.print_missing_exps(path, nested_data_dict)
        self.print_id_and_letter(path)


    def execute_all(self, path):
        """
        last step
        """

        self.path = path
        
        
        test = [os.path.join(r,n) for r,d,f in os.walk(path) for n in d]

        if len(test) == 0:
            self.run_all(path)
        else:
            fps = [os.path.join(r,n) for r,d,f in os.walk(path) for n in d]
            count=0
            for i in fps:
                print("\n\n{} || {}".format(count, i))
                self.run_all(i)
                count+=1
                

    # anything below here doesn't get executed in execute_all()
    def shell_filesize_check(self, path):
        """
        return stdout & stderr from David's ERP shell scripts 
        """
        self.path = path

        erp_check = subprocess.Popen('ERP-raw-data_check.sh {}'.format(path), shell=True, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path)
        result_erp = erp_check.communicate()[0]
        print("\nERP CHECK: {} {}".format(path, result_erp.decode('ascii')))
        
        
        size_check = subprocess.Popen('DVD-file-size_check.sh {}'.format(path), shell=True, 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=path)
        result_size = size_check.communicate()[0]
        print('FILE SIZE CHECK: {} {}\n'.format(path, result_size.decode('ascii')))


    def iter_shell_check(self, path):
        """
        iterate over directories checking with shell scripts 
        """

        self.path = path

        test = [os.path.join(r,n) for r,d,f in os.walk(path) for n in d]

        if len(test) == 0:
            self.shell_filesize_check(path)
        else:
            fps = [os.path.join(r,n) for r,d,f in os.walk(path) for n in d]
            count=0
            for i in fps:
                count+=1
                print("\n{} || {}".format(count, i))
                self.shell_filesize_check(i)


ep = erp_data()


################################### NEW CLASS STARTS HERE ###################################

class site_data:
    #get_h1s()
    def __init__(self):
    
        self.ant_set = {'ant'}
        self.ans_set = {'ans'}
        self.other_exps = {'vp3', 'cpt', 'ern', 'aod', 'stp', 'gng'}
                
    def check_cnt_copy(self, path, exp_tuple):
        """
        checks to see if files you want to h1 are actually in the directory to begin with
        """

        self.path = path
        self.exp_tuple = exp_tuple

        cnt_dict = {}
        for r,d,f in os.walk(path):
            for n in f:
                if n.startswith((exp_tuple)) and n.endswith('_32.cnt'):
                    split = n.split('_')
                    cnt_dict.setdefault(split[3], []).append(split[0])

        for k,v in cnt_dict.items():
            if len(set(v)) is not len(exp_tuple): # using set on value could cause problems?
                missing_exp = '.'.join(str(s) for s in (set(v) ^ set(list(exp_tuple))))
                print('\n\nLOOK HERE!!!{} cnt file missing from {}\n\n'.format(missing_exp.upper(), path))
                
    #get_h1s()                
    def rename_cnts(self, path, skip=False, trg_dir=None, exp_tuple=None):
        """
        rename file ending with _rr.cnt if it doesn't already exist
        """
        self.path = path
        self.skip = skip
        self.trg_dir = trg_dir
        self.exp_tuple = exp_tuple
        
        if skip:
            for r,d,f in os.walk(path):
                for n in f: ### if reruns gets messed up, startswith() caused it
                    if n.startswith(exp_tuple) and n.endswith('_rr.cnt'):
                        print("\n>>> RERUN CNT FOUND <<<\n\nRerun found for {} -- create h1.ps file manually".format(n))
            #return True
        
        # find cnts, make sure when removing _rr that another file by that name doesnt already exist...
        # if it doesnt, copy that file to trg_dir & rename in TRG DIR 
        
        if trg_dir:
            rr_dirs = []
            for r,d,f in os.walk(path):
                for n in f:
                    if n.endswith('_rr.cnt'):
                        new_rr_fname = os.path.join(r, n[:-7] + '.cnt')
                        if not os.path.exists(new_rr_fname):
                            old_dir = os.path.join(r,n)
                            trg_dir_exp = "{}/{}".format(trg_dir,n[:3])
                            if not os.path.exists(trg_dir_exp):
                                os.makedirs(trg_dir_exp)
                                new_dir = os.path.join(trg_dir_exp,n)
                                rr_dirs.append(new_dir)
                                shutil.copy(old_dir, new_dir)
                                print("\n>>> RERUN CNT FOUND <<<\n\nWill rename {} when copied to {}".format(n, trg_dir_exp))
                            else:
                                new_dir = os.path.join(trg_dir_exp,n)
                                rr_dirs.append(new_dir)
                                shutil.copy(old_dir, new_dir)
                                print("\n>>> RERUN CNT FOUND <<<\n\nWill rename {} when copied to {}".format(n, trg_dir_exp))

                        else:
                            print("\n>>> RERUN CNT FOUND <<<\n\nTried to remove '_rr' from {} but that file already exists. File not copied.".format(n))

            for rr in rr_dirs:
                fname = os.path.basename(rr)
                new_rr_fname = os.path.join(os.path.dirname(rr), fname[:-7] + '.cnt')
                os.rename(rr, new_rr_fname)
                print("Renaming {} => {}".format(fname, os.path.basename(new_rr_fname)))

        

    #get_h1s()                    
    def create_cnth1(self, path):
        """
        create cnt.h1 files from shell script
        """
        self.path = path
        
        print('\n\n>>> MAKING CNT.H1 FILES <<<\n') 
        for r,d,f in os.walk(path):
            for n in f:
                if n.startswith(self.cnth1_tups) and n.endswith('_32.cnt'):
                    path = os.path.join(r,n)
                    p = subprocess.Popen("create_cnthdf1_from_cntneuroX.sh {}".format(path),shell=True, 
                                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(path))
                    result = p.communicate()[1]
                    print(result.decode('ascii'))

    #get_h1s()
    def create_avgh1(self, path):
        """
        create avg.h1 files from shell script
        """
        self.path = path

        print('\n\n>>> Making AVG.H1 FILES <<<\n') 
        for r,d,f in os.walk(path):
            for n in f:
                if n.startswith(self.ant_tup) and n.endswith('cnt.h1'):
                    ant_path = os.path.join(r,n)
                    p_ant = subprocess.Popen('create_avghdf1_from_cnthdf1X -lpfilter 8 -hpfilter 0.03 -thresh 75 -baseline_times -125 0 {}'.format(ant_path), 
                                             shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(ant_path))
                    result_ant = p_ant.communicate()[1]
                    print(result_ant.decode('ascii'))
                if n.startswith(self.ans_tup) and n.endswith('cnt.h1'):
                    ans_path = os.path.join(r,n)
                    p_ans = subprocess.Popen('create_avghdf1_from_cnthdf1X -lpfilter 16 -hpfilter 0.03 -thresh 100 -baseline_times -125 0 {}'.format(ans_path), 
                                            shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(ans_path))
                    result_ans = p_ans.communicate()[1]
                    print(result_ans.decode('ascii'))
                if n.startswith((self.others_tup)) and n.endswith('cnt.h1'):
                    path=os.path.join(r,n)
                    p_others = subprocess.Popen('create_avghdf1_from_cnthdf1X -lpfilter 16 -hpfilter 0.03 -thresh 75 -baseline_times -125 0 {}'.format(path), 
                                                shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(path))
                    result_others = p_others.communicate()[1]
                    print(result_others.decode('ascii'))

    #get_h1s()
    def create_avgps(self, path):
        """
        create avg.h1.ps files from shell script
        """
        
        self.path = path

        print('\n\n>>> Making AVG.PS FILES <<<\n') 
        for path, subdirs, files in os.walk(path):
            for name in files:
                if name.endswith("avg.h1"):
                    ps_paths = os.path.join(path, name)
                    subprocess.Popen("plot_hdf1_data.sh {}".format(name), shell=True, cwd=os.path.dirname(ps_paths))
                    print("creating ps files.. " + name)
                    
    #get_h1s()                
    def delete_bad_files(self, path, exts_to_keep=None, to_be_deleted_set=None):
        ''' returns any extension not in exts_to_keep & prompts user to delete '''
    
        self.path = path
        self.exts_to_keep = exts_to_keep
        self.to_be_deleted_set = to_be_deleted_set


        
        print("\n\n>>> REMOVING FILES <<<\n") 
        if exts_to_keep:

            for r,d,f in os.walk(path):
                for n in f:
                    if n.endswith(('_cnt.h1', '_avg.h1', 'h1.ps')):
                        os.remove(os.path.join(r,n))
                        print('Removing {}'.format(n))

        if to_be_deleted_set:
            
            for r,d,f in os.walk(path):
                for n in f:
                    if n.endswith(('_32.cnt', '_cnt.h1')):
                        os.remove(os.path.join(r,n))
                        print('Removing {}'.format(n))



    
    def get_h1s(self, path, set_of_exps, del_ext=None, ps=None, trg_dir=None):
        '''combines all these commands together'''
        
        self.path = path
        self.set_of_exps = set_of_exps
        self.ps = ps
        self.trg_dir = trg_dir
        
        #use in create_cnth1()
        self.cnth1_tups = tuple(set_of_exps)
        
        if_ant = self.ant_set & set_of_exps
        if_ans = self.ans_set & set_of_exps
        all_others = self.other_exps & set_of_exps
        
        #used in create_avgh1()
        self.ant_tup = tuple(if_ant)
        self.ans_tup = tuple(if_ans)
        self.others_tup = tuple(all_others)

        #if being used for peak picking, create new directories and move all cnt files to the correct folder...and so on
        if trg_dir:
            #create new directories
            exps_list = list(set_of_exps)
            for exp in exps_list:
                new_dirs = os.path.join(trg_dir, exp)
                if not os.path.exists(new_dirs):
                    os.makedirs(new_dirs)
                    print(">>> Creating {} <<<".format(new_dirs))
                else:
                    #print("{} already exist".format(new_dirs))
                    pass
            #copy cnt files to newly created directories       
            count = 0
            print('\n>>> COPYING CNT FILES <<<\n')
            for r,d,f in os.walk(path):
                for n in f:
                    if n.startswith(self.cnth1_tups) and n.endswith('_32.cnt'):
                        count+=1
                        print('Copying {}'.format(n))
                        shutil.copy(os.path.join(r,n), os.path.join(trg_dir, n[:3]))
            print('\nCopied {} of {} files'.format(count, len(self.cnth1_tups)))

            self.rename_cnts(path,trg_dir=trg_dir)
            self.check_cnt_copy(trg_dir, self.cnth1_tups)
            self.create_cnth1(trg_dir)
            self.create_avgh1(trg_dir)
            if ps:
                self.create_avgps(trg_dir)
            if del_ext:
                self.delete_bad_files(trg_dir, to_be_deleted_set=True)
            return True
        
        if ps:
            self.rename_cnts(path, skip=True, exp_tuple=self.cnth1_tups)
            self.create_cnth1(path)
            self.create_avgh1(path)
            self.create_avgps(path)
            #self.delete_bad_files(path, exts_to_keep=True)
            

sd = site_data()


def concat_peak_paths(site, exp_name):
    """
    concats path to peak picked and reject directory for any site
    """


    peak_pick_dirs = ['ant_phase4__NewPPicker_peaks_2018', 'aod_phase4__NewPPicker_peaks_2018', 
                      'vp3_phase4__NewPPicker_peaks_2018']

    hbnl = '/vol01/active_projects/HBNL/'

    pp_dirs = []

    for i in peak_pick_dirs:
        if exp_name in i:
            good_dir = hbnl + i + '/' + site
            rej_dir = os.path.join(good_dir, 'reject')
            pp_dirs.append(good_dir)
            pp_dirs.append(rej_dir)
            
    return pp_dirs


def create_peaks_dict(path_to_picked_files):
    """
    creates a nested dict of lists {exp_name:{sub_id:[mt, h1, pdf]}}
    """
    
    peaks_dict ={}
    for root,dirs,files in os.walk(path_to_picked_files):
        for fname in files:
            if fname.endswith(('avg.h1', 'pdf', 'avg.mt')):
                regex = re.split(r'[_.]', fname)
                peaks_dict.setdefault(regex[0], {}).setdefault(regex[3], []).append(regex[-1])
    return peaks_dict


def move_peaks(path_to_picked_files, peaks_dict, exp_name, site):
    

    concat_hbnl_path = os.path.join(path_to_picked_files, exp_name)
    
    count_spacer_accepted = 0
    count_spacer_rejected = 0
    accepted_count = 0
    rejected_count = 0
    
    print("{} FILES TO ME MOVED\n\n".format(exp_name.upper()))
    for k,v in peaks_dict.items():
        if exp_name in k:
            for sub_id, file_exts in v.items():
                if 'mt' in file_exts and len(file_exts) == 3:
                    good_dir = "*" + sub_id + "*"
                    print("\n{} {} {}".format(k, sub_id, file_exts))
                    wildcard_path_good = os.path.join(concat_hbnl_path, good_dir) 
                    non_rej_dir = concat_peak_paths(site, exp_name)[0] ## func here
                    for fname in glob(wildcard_path_good):
                        new_hbnl_fname_path_good = os.path.join(non_rej_dir, os.path.basename(fname))
                        if (os.path.exists(new_hbnl_fname_path_good)):
                            print("{} already exists!".format(new_hbnl_fname_path_good))
                        else:
                            shutil.copy(os.path.join(wildcard_path_good, fname), non_rej_dir)
                            count_spacer_accepted+=1
                            accepted_count+=1
                            print("Moved {}".format(fname))
                            if count_spacer_accepted %3 == 0:
                                print('\n\n')


                    # move to reject directory
                else:
                    rej_dir = "*" + sub_id + "*"
                    print("\n{} {} {}".format(k, sub_id, file_exts))
                    wildcard_path_rej = os.path.join(concat_hbnl_path, rej_dir) 
                    rej_dir = concat_peak_paths(site, exp_name)[1] ## func here
                    for fname in glob(wildcard_path_rej):
                        new_hbnl_fname_path_rej = os.path.join(rej_dir, os.path.basename(fname))
                        if (os.path.exists(new_hbnl_fname_path_rej)):
                            print("{} already exists!".format(new_hbnl_fname_path_rej))
                        else:
                            shutil.copy(os.path.join(wildcard_path_rej, fname), rej_dir)
                            count_spacer_rejected+=1
                            rejected_count+=1
                            print("Moved {}".format(fname))
                            if count_spacer_rejected %2 == 0:
                                print('\n\n')

    print ("\n\nTotal of {} subs accepted.\nTotal of {} subs rejected.\n\n".format(int(accepted_count / 3), int(rejected_count /2)))

def start_mover(path_to_picked_files, site):
    """
    path_to_picked_files must not have aod/vp3/ant append to it
    """
    
    peaks_dict = create_peaks_dict(path_to_picked_files)
    
    
    exp_names = [n for r,d,f in os.walk(path_to_picked_files) for n in d] 
    
    for exp in exp_names:
        move_peaks(path_to_picked_files, peaks_dict, exp, site)


def checkIds(subId, directorySite):
    """
    given a list of IDS, takes first index of ID to see if it matches site name 
    """
    
    site_dict = {'1': 'uconn', '2': 'indiana', '3': 'iowa',
             '4': 'suny', '5': 'washu', '6': 'ucsd'}
    
    siteToId = subId[0] in site_dict and directorySite == site_dict[subId[0]] 
    try: 
        if siteToId == False:
            print("ERROR: {} does not match site name {}".format(subId, directorySite))
            raise FileNotFoundError
    except (RuntimeError) as e:
        e = sys.exc_info()
        print("ERROR TYPE: {}".format('You made a big fucking error'))





################################### NEW FUNCTIONS START HERE ###################################

def parse_mt_files(single_mt_path):
    """
    parses an mt file to create a frequency dictionary of condition & peak
    """
    
    peaks_lst = []
    sub_id = []
    with open(single_mt_path, 'r') as file:
        for line in file:
            if line.startswith('#'):
                pass
            else:
                sp = line.split(None, 10)
                peaks_lst.append(sp[5]+ '_' +  sp[7])
                sub_id.append(sp[0])


    peaks_counter = Counter(sorted(peaks_lst))            

    mt_dict = {}
    mt_dict[sub_id[0]] = peaks_counter
    
    return mt_dict

def check_parsed_mt_files(peak_pick_path):
    """
    given a path to folder with mt files, collects parses them & checks for accuracy.
    works with an entire HBNL exp folder or exp folders for speicfic sites.
    """
    print('Finding mt files...\n')
    mts = [os.path.join(r,n) for r,d,f in os.walk(peak_pick_path) for n in f if n.endswith('mt')]
    
    print('Found {} mt files.\nParsing mt files...\n'.format(len(mts)))
    lst = []
    for i in mts:
        lst.append(parse_mt_files(i))
       
    parsed_exp_dict ={}
    for i in lst:
        d = i
        for k,v in d.items():
            for k1,v1 in v.items():
                parsed_exp_dict.setdefault(k, {})[k1] =v1
                
    # correct dictionaries for aod/vp3/ant          
    aod_dict = {'1_N1': 61, '2_P2': 61, '2_N1': 61, '1_P3': 61}
    vp3_dict = {'3_N1': 61, '2_N1': 61, '1_P3': 61, '2_P3': 61, '1_N1': 61, '3_P3': 61}
    ant_dict = {'1_N4': 61, '2_N4': 61, '1_P3': 61, '2_P3': 61, '3_N4': 61, '3_P3': 61}

    mt_check_dict = {}
    mt_check_dict['ant'] = ant_dict
    mt_check_dict['aod'] = aod_dict
    mt_check_dict['vp3'] = vp3_dict

    exp_name = ""
    if peak_pick_path.endswith(('indiana', 'iowa', 'suny', 'uconn', 'ucsd', 'washu')):
        exp_name+=os.path.basename(os.path.dirname(peak_pick_path))[:3]
    else: 
        exp_name+=os.path.basename(peak_pick_path)[:3]
    
    exp_name_dict = mt_check_dict[exp_name]


    bad_ids = []
    for k,v in parsed_exp_dict.items():
        if v != exp_name_dict:
            bad_ids.append(k)
            
    if len(bad_ids) == 0:
        return "All files correctly picked!"

    bad_h1s = []
    for i in bad_ids:
        wildcard = "{}".format(i)
        for r,d,f in os.walk(peak_pick_path):
            for n in f:
                if wildcard in n and n.endswith('avg.h1'):
                    bad_h1s.append(os.path.join(r,n))
    return bad_h1s
    


class Log(object):
    def __init__(self, edit):
        self.out = sys.stdout
        self.textEdit = edit

    def write(self, message):
        #self.out.write(message) # writes to terminal 
        self.textEdit.insertPlainText(message)

    def flush(self):
        self.out.flush()

class App(QMainWindow):        
 
    def __init__(self):   
        super(App, self).__init__()
        
        self.title = 'Site Data Utilities - ERP'
        self.left = 0
        self.top = 0
        self.width = 1400
        self.height = 800
        self.setWindowTitle(self.title)
        self.setWindowIcon(QIcon('/vol01/active_projects/anthony/brain.jpg'))
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        self.stylesheet = """ 
        QTabBar::tab:selected {background: pink;}
        QTabWidget>QWidget>QWidget{background: black;}
        """

        now = datetime.now()
        self.fname = '/vol01/active_projects/anthony/pyqt_logs/erp/' + sys.argv[1].split('-')[-1] + '_' + now.strftime("%Y-%m-%d_%H-%M")
        self.count = 0
        
        # Initialize tab widget
        self.tabs = QTabWidget()
        
        self.initReviewDataTab()
        self.initShellScriptsTab()
        self.initH1PeaksTab()
        self.initH1ViewingTab()
        self.initMoveFilesTab()
        self.initCheckPeaksTab()
        self.addTabsAndShow()
        

        
    def initReviewDataTab(self):
        """
        creates review data tab 
        """
        
        # CREATE tab & layout
        self.erpReviewDataTab = QWidget()
        self.erpReviewDataTabLayout = QVBoxLayout()
        self.erpReviewDataGrid = QHBoxLayout()
        self.erpReviewDataOutputWindow = QTextEdit()
            
        # CREATE input box & button 
        self.reviewDataDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/ns650', self.erpReviewDataTabLayout)
        self.reviewDataButton = self.createButtons('Review Site Data', self.reviewSiteData)
        self.reviewDataClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.erpReviewDataOutputWindow))
        # horizontal button row 
        erpReviewDataButtons = self.buttonRow(self.reviewDataButton, self.reviewDataClearButton, self.erpReviewDataGrid)
       
        # ADD css
        self.cssInstructions(self.reviewDataDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.reviewDataButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.reviewDataClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.erpReviewDataOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.erpReviewDataTab.setStyleSheet(self.stylesheet)
        
        # ADD to tab
        self.erpReviewDataTab.setLayout(self.reviewDataDir[0])
        self.erpReviewDataTabLayout.addLayout(erpReviewDataButtons)
        self.erpReviewDataTabLayout.addWidget(self.erpReviewDataOutputWindow)
        
    def initShellScriptsTab(self):
        """
        creates shell scripts tab
        """
        
        # CREATE tab & layout
        self.erpShellScriptsTab = QWidget()
        self.erpShellScriptsTabLayout = QVBoxLayout()
        self.erpShellScriptsGrid = QHBoxLayout()
        self.erpShellScriptsOutputWindow = QTextEdit()
                
        # CREATE input box & button
        self.shellScriptsDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/ns650', self.erpShellScriptsTabLayout)
        self.shellScriptsButton = self.createButtons('Run Shell Scripts', self.shellScripts)
        self.shellScriptsClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.erpShellScriptsOutputWindow))
        # horizontal button row 
        erpShellScriptsButtons = self.buttonRow(self.shellScriptsButton, self.shellScriptsClearButton, self.erpShellScriptsGrid)
        
        # ADD css
        self.cssInstructions(self.shellScriptsButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.shellScriptsDir[1], "INCONSOLATA", 22, "white", "#000000")
        self.cssInstructions(self.shellScriptsClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.erpShellScriptsOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.erpShellScriptsTab.setStyleSheet(self.stylesheet)
        
        # ADD to tab 
        self.erpShellScriptsTab.setLayout(self.shellScriptsDir[0])
        self.erpShellScriptsTabLayout.addLayout(erpShellScriptsButtons)
        self.erpShellScriptsTabLayout.addWidget(self.erpShellScriptsOutputWindow)
        
    def initH1PeaksTab(self):
        """
        creates peak picking tab 
        """
        
        # CREATE tab & layout 
        self.erpH1PeaksTab = QWidget()
        self.erpH1PeaksTabLayout = QVBoxLayout()
        self.checkboxLayout = QHBoxLayout()
        self.erpH1PeaksGrid = QHBoxLayout()
        self.erpH1PeaksOutputWindow = QTextEdit()
        
        # CREATE input box     
        self.peaksDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/ns650', self.erpH1PeaksTabLayout)
        self.peaksTrgDir = self.createWidgetLayout('Target Directory: ', '/vol01/active_projects/anthony/test_qt', self.erpH1PeaksTabLayout)
        self.peaksExcludeDir = self.createWidgetLayout('Dirs to Exclude: ', '00000001 00000002 00000003', self.erpH1PeaksTabLayout)
        # CREATE checkboxes
        self.checkboxAll = self.createCheckbox('all exps', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxVP3 = self.createCheckbox('vp3', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxCPT = self.createCheckbox('cpt', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxERN = self.createCheckbox('ern', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxANT = self.createCheckbox('ant', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxAOD = self.createCheckbox('aod', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxANS = self.createCheckbox('ans', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxSTP = self.createCheckbox('stp', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        self.checkboxGNG = self.createCheckbox('gng', self.expCheckboxHandler, self.checkboxLayout, self.erpH1PeaksTabLayout)
        # CREATE buttons
        self.peaksButton = self.createButtons('Peak Picking', self.peaksH1)
        self.erpH1PeaksClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.erpH1PeaksOutputWindow))
        # horizontal button row 
        erpH1PeaksButtons = self.buttonRow(self.peaksButton, self.erpH1PeaksClearButton, self.erpH1PeaksGrid)
        
        # ADD css
        self.cssCheckboxes(self.checkboxAll[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxVP3[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxCPT[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxERN[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxANT[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxAOD[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxANS[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxSTP[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxGNG[1], (50,50), 'INCONSOLATA', 16)
        self.cssInstructions(self.peaksDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.peaksTrgDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.peaksExcludeDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.peaksButton, "INCONSOLATA", 22, "#000000", "white")
        self.cssInstructions(self.erpH1PeaksClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.erpH1PeaksOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.erpH1PeaksTab.setStyleSheet(self.stylesheet)
        
        # ADD input boxes to tab 
        self.erpH1PeaksTab.setLayout(self.peaksDir[0])
        self.erpH1PeaksTab.setLayout(self.peaksTrgDir[0])
        self.erpH1PeaksTab.setLayout(self.peaksExcludeDir[0])
        # ADD checkboxes to tab 
        self.erpH1PeaksTab.setLayout(self.checkboxAll[0])
        self.erpH1PeaksTab.setLayout(self.checkboxVP3[0])
        self.erpH1PeaksTab.setLayout(self.checkboxCPT[0])
        self.erpH1PeaksTab.setLayout(self.checkboxERN[0])
        self.erpH1PeaksTab.setLayout(self.checkboxANT[0])
        self.erpH1PeaksTab.setLayout(self.checkboxAOD[0])
        self.erpH1PeaksTab.setLayout(self.checkboxANS[0])
        self.erpH1PeaksTab.setLayout(self.checkboxSTP[0])
        self.erpH1PeaksTab.setLayout(self.checkboxGNG[0])
        # ADD to tab
        self.erpH1PeaksTabLayout.addLayout(erpH1PeaksButtons)
        self.erpH1PeaksTabLayout.addWidget(self.erpH1PeaksOutputWindow)

        
        
    def initH1ViewingTab(self):
        """
        creates tab to make H1's in PWD
        """
        
        # CREATE tab & layouts
        self.erpPsViewingTab = QWidget()
        self.erpPsViewingTabLayout = QVBoxLayout()
        self.checkboxLayoutPs = QHBoxLayout()
        self.psButtonLayout = QHBoxLayout()
        self.erpPsViewingGrid = QHBoxLayout()
        self.erpPsViewingOutputWindow = QTextEdit()
        
        # CREATE input boxes    
        self.psViewingDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/ns650', self.erpPsViewingTabLayout)
        self.psViewingExcludeDir = self.createWidgetLayout('Dirs to Exclude: ', '00000001 00000002', self.erpPsViewingTabLayout)
        # CREATE checkboxes
        self.checkboxAllPs = self.createCheckbox('all exps', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxVP3Ps = self.createCheckbox('vp3', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxCPTPs = self.createCheckbox('cpt', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxERNPs = self.createCheckbox('ern', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxANTPs = self.createCheckbox('ant', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxAODPs = self.createCheckbox('aod', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxANSPs = self.createCheckbox('ans', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxSTPPs = self.createCheckbox('stp', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        self.checkboxGNGPs = self.createCheckbox('gng', self.expCheckboxHandlerPs, self.checkboxLayoutPs, self.erpPsViewingTabLayout)
        # CREATE buttons  
        self.psViewingButton = self.createButtons('Create h1.ps files', self.createPsFiles)
        self.psViewingButtonDelete = self.createButtons('Delete h1 and h1.ps', self.deleteViewingFiles)
        self.psViewingClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.erpPsViewingOutputWindow))
        # horizontal button row 
        erpPsViewingButtons = self.buttonRow(self.psViewingButton, self.psViewingButtonDelete, self.erpPsViewingGrid, btn3=self.psViewingClearButton)
        
        # ADD CSS
        self.cssInstructions(self.psViewingDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.psViewingExcludeDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssCheckboxes(self.checkboxAllPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxVP3Ps[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxCPTPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxERNPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxANTPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxAODPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxANSPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxSTPPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssCheckboxes(self.checkboxGNGPs[1], (50,50), 'INCONSOLATA', 16)
        self.cssInstructions(self.psViewingButton, "INCONSOLATA", 22, "#000000", "white")
        self.cssInstructions(self.psViewingButtonDelete, "INCONSOLATA", 22, "#000000", "white")
        self.cssInstructions(self.psViewingClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.erpPsViewingOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.erpPsViewingTab.setStyleSheet(self.stylesheet)

        # SET layouts for checkboxes
        self.erpPsViewingTab.setLayout(self.checkboxAllPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxVP3Ps[0])
        self.erpPsViewingTab.setLayout(self.checkboxCPTPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxERNPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxANTPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxAODPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxANSPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxSTPPs[0])
        self.erpPsViewingTab.setLayout(self.checkboxGNGPs[0])
        # SET layouts for dir & button
        self.erpPsViewingTab.setLayout(self.psViewingDir[0])
        self.erpPsViewingTab.setLayout(self.psViewingExcludeDir[0])
        
        self.erpPsViewingTabLayout.addLayout(erpPsViewingButtons)
        self.erpPsViewingTabLayout.addWidget(self.erpPsViewingOutputWindow)
    
    def initMoveFilesTab(self):
        """
        create tab that moves peak picked files to /active_projects/HBNL/...
        """
        
        # CREATE tab & layouts
        self.erpMovePeaksTab = QWidget()
        self.erpMovePeaksTabLayout = QVBoxLayout()
        self.erpMovePeaksGrid = QHBoxLayout()
        self.erpMovePeaksOutputWindow = QTextEdit()
        
        # CREATE input boxes & buttons 
        self.erpMovePeaksDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/waitingOn/erp_dec_suny', self.erpMovePeaksTabLayout)
        self.erpMovePeaksSite = self.createWidgetLayout('Site: ', 'suny', self.erpMovePeaksTabLayout)
        self.erpMovePeaksButton = self.createButtons('Move Peaks', self.movePeaks)
        self.erpMovePeaksClearButton = self.createButtons('Clear all text',  functools.partial(self.clearWindowText, windowName = self.erpMovePeaksOutputWindow))
        # horizontal button row 
        erpMovePeaksButtons = self.buttonRow(self.erpMovePeaksButton, self.erpMovePeaksClearButton, self.erpMovePeaksGrid)

        # ADD css
        self.cssInstructions(self.erpMovePeaksDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.erpMovePeaksSite[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.erpMovePeaksButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.erpMovePeaksClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.erpMovePeaksOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.erpMovePeaksTab.setStyleSheet(self.stylesheet)
        
        #ADD to tab 
        self.erpMovePeaksTab.setLayout(self.erpMovePeaksDir[0])
        self.erpMovePeaksTab.setLayout(self.erpMovePeaksSite[0])           
        self.erpMovePeaksTabLayout.addLayout(erpMovePeaksButtons)
        self.erpMovePeaksTabLayout.addWidget(self.erpMovePeaksOutputWindow)

    def initCheckPeaksTab(self):
        """
        creates tab to parse mt files to ensure they were correctly picked
        """

        self.checkPeaksTab = QWidget()
        self.checkPeaksTabLayout = QVBoxLayout()
        self.checkPeaksGrid = QHBoxLayout()
        self.checkPeaksOutputWindow = QTextEdit()


        # CREATE input boxes & buttons 
        self.checkPeaksDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/HBNL/aod_phase4__NewPPicker_peaks_2018/washu', self.checkPeaksTabLayout)
        self.checkPeaksButton = self.createButtons('Check Peaks', self.checkPeaks)
        self.checkPeaksClearButton = self.createButtons('Clear all text',  functools.partial(self.clearWindowText, windowName = self.checkPeaksOutputWindow))
        # horizontal button row 
        checkPeaksButtons = self.buttonRow(self.checkPeaksButton, self.checkPeaksClearButton, self.checkPeaksGrid)

        # ADD css
        self.cssInstructions(self.checkPeaksDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.checkPeaksButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.checkPeaksClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.checkPeaksOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.checkPeaksTab.setStyleSheet(self.stylesheet)
        
        #ADD to tab 
        self.checkPeaksTab.setLayout(self.checkPeaksDir[0])          
        self.checkPeaksTabLayout.addLayout(checkPeaksButtons)
        self.checkPeaksTabLayout.addWidget(self.checkPeaksOutputWindow)


    
    def addTabsAndShow(self):
        """
        adds above tabs to GUI & show
        """
        
        self.tabs.addTab(self.erpReviewDataTab, "Review ERP Data")
        self.tabs.addTab(self.erpShellScriptsTab, "Run Shell Scripts")
        self.tabs.addTab(self.erpH1PeaksTab, "H1 - Peak Picking")
        self.tabs.addTab(self.erpPsViewingTab, "H1 - Viewing ps files")
        self.tabs.addTab(self.erpMovePeaksTab, "H1 - Move Peak Picked Files")
        self.tabs.addTab(self.checkPeaksTab, "H1 - Check Peak Picked Files")
        
        self.setCentralWidget(self.tabs)
        self.show()

    def write_logging_file(self, fname, text_to_write, count):
        """
        write output from QTextEdit window in each tab to .log file
        """
        ast = ''.join(["*" for i in range(70)])
        with open(fname, 'a') as f:
            f.write("\n\n{}\n{}\n{}\n\n".format(ast, str(count), ast))
            f.write(text_to_write)    
        
    def buttonRow(self, btn1, btn2, hbox, btn3 = False):
        """
        side-by-side buttons 
        """
        self.btn1 = btn1
        self.btn2 = btn2
        self.hbox = hbox

        hbox.addWidget(btn1)
        hbox.addWidget(btn2)
        if btn3:
            hbox.addWidget(btn3)
            return hbox
                                                       
        return hbox 
                                                        
    def clearWindowText(self, signal, windowName):
        self.windowName = windowName
        windowName.clear()

        
    def deleteViewingFiles(self):
        """
        this works 
        """
        directoryInp = self.psViewingDir[2].text().strip()
        directoryExclude = self.psViewingExcludeDir[2].text().strip()
        
        # do those dirs exist 
        self.pathExists([directoryInp])

        dirs = [os.path.join(r,n) for r,d,f in os.walk(directoryInp) for n in f if n.endswith(('.cnt.h1', '_avg.h1'))]
        if len(dirs) == 0:
            return sd.delete_bad_files(directoryInp, exts_to_keep=True)
        
        excludedToCheck = [directoryInp + '/' + i for i in directoryExclude.split()]
        self.pathExists(excludedToCheck)
        
        # if excluded dirs
        if len(excludedToCheck) != 0:
            
            excluded = directoryExclude.split()
            include_dirs = [os.path.join(directoryInp, i) for i in os.listdir(directoryInp) if i not in excluded]
            count = 0
            for i in include_dirs:
                count+=1
                print("\n\n{}".format(count)), sd.delete_bad_files(i, exts_to_keep=True) 
        else:
            count = 0
            for i in dirs:
                count+=1
                print("\n\n{}".format(count)), sd.delete_bad_files(directoryInp, exts_to_keep=True)
            

        
    # ALL TABS  
    def createWidgetLayout(self, qLabelTitle, qLineEditText, vbox):
        """
        used to create labels with text input box.
        all you need to do is setLayout on Tab on return[0].
        use return[1] & return[2] to style with css
        """
        self.qLabelTitle = qLabelTitle
        self.qLineEditText = qLineEditText
        self.vbox = vbox

        # CREATE horozontial layout
        widgetLayout = QHBoxLayout()
        widgetLabel = QLabel(qLabelTitle)
        widgetInput = QLineEdit(qLineEditText)
        
        # ADD WIDGETS to layout then add widgetLayout to tabLayout(vbox)
        widgetLayout.addWidget(widgetLabel)
        widgetLayout.addWidget(widgetInput)
        vbox.addLayout(widgetLayout)
        return vbox, widgetLabel, widgetInput
    
    # ALL TABS 
    def createInstructionsLayout(self, qLabelInstructions, vbox):
        """
        returns layout for instructions 
        all you need to do is SetLayout on return[0]
        use return[1] to style with css
        """
        self.qLabelInstructions = qLabelInstructions
        self.vbox = vbox
        
        # CREATE horozontial layout
        instructionsLayout = QHBoxLayout()
        instructions = QLabel(qLabelInstructions)
        
        #ADD WIDGETS to layout then add widgetLayout to tabLayout(vbox)
        instructionsLayout.addWidget(instructions)
        vbox.addLayout(instructionsLayout)
        return vbox, instructions
    
    # ALL TABS
    def createButtons(self, buttonText, buttonMethod):
        """
        return layout for button
        all you need to do is SetLayout on return[0]
        use return[1] to style with css
        """
        self.buttonText = buttonText
        self.buttonMethod = buttonMethod
   
        
        buttonName = QPushButton(buttonText)
        buttonName.clicked.connect(buttonMethod)
        return buttonName
        
    # ALL TABS 
    def cssInstructions(self, buttonName, fontFamily, fontSize, fontColor, bgroundColor):
        """
        add CSS for the instructions box at the top of every tab 
        """
        
        self.buttonName = buttonName
        self.fontFamily = fontFamily
        self.fontSize = fontSize
        self.fontColor = fontColor
        self.bgroundColor = bgroundColor
        
        buttonFont = QFont(fontFamily, int(fontSize)) #QFont("SansSerif", 20, QFont.Bold) 
        formatCSS = "color: {}; background-color: {};".format(fontColor, bgroundColor)
        buttonName.setStyleSheet(formatCSS)
        return buttonName.setFont(buttonFont)
        
    # erpH1PeaksTab & erpPsViewingTab  
    def cssCheckboxes(self,checkboxName,widthHeightTuple, fontFamily, fontSize):
        """
        increase checkbox size
        """
        
        self.checkboxName = checkboxName
        self.widthHeightTuple = widthHeightTuple
        self.fontFamily = fontFamily
        self.fontSize = fontSize
        
        checkboxFont = QFont(fontFamily, int(fontSize))
        formatCSS = "QCheckBox::indicator {{ width:{}px; height: {}px;}}".format(str(widthHeightTuple[0]), str(widthHeightTuple[1]))
        checkboxName.setStyleSheet(formatCSS)
        checkboxName.setFont(checkboxFont)
        checkboxName.setStyleSheet("color:black; background-color: white;")
        
    # ALL TABS     
    def pathExists(self, filepath): 
        """
        stops execution of script if filepath doesnt exist
        """
        self.filepath = filepath
        
        try: 
            for i in filepath:
                if not os.path.exists(i):
                    print("ERROR: {} doesn't exist.\nCheck ^^ path and run again.\n".format(i))
                    raise FileNotFoundError
        except (FileNotFoundError):
            e = sys.exc_info()
            print("ERROR TYPE: {}".format(e[0]))
            
    #erpReviewDataTab   
    def reviewSiteData(self, signal):
        """
        ONLY WORKS if directory has >= 2 sub-directories
        """
        self.count+=1

        sys.stdout = Log(self.erpReviewDataOutputWindow)
        
        directoryInp = self.reviewDataDir[2].text().strip()

        self.pathExists([directoryInp])
        dirs = [os.path.join(r,n) for r,d,f in os.walk(directoryInp) for n in d]

        count = 0
        for i in dirs:
            count+=1
            print("\n\n{} || {}".format(count, i)), ep.execute_all(i) 
            QApplication.processEvents()

        reviewDataText = self.erpReviewDataOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log', reviewDataText, self.count)
            
        sys.stdout = sys.__stdout__ 

    #checkPeaksTab
    def checkPeaks(self, signal):
        """
        given a path to folder with mt files - checks for accuracy of picks
        """
        self.count+=1

        sys.stdout = Log(self.checkPeaksOutputWindow)

        directoryInp = self.checkPeaksDir[2].text().strip()

        self.pathExists([directoryInp])

        potential_errors = check_parsed_mt_files(directoryInp)
        if type(potential_errors) == list:
            print('The following files were found to be incorrectly peak picked: \n')
            for i in potential_errors:
                print("{}\n".format(i))
        else:
            print(potential_errors)

        checkPeaksText = self.checkPeaksOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log',  checkPeaksText, self.count)
            
        sys.stdout = sys.__stdout__
            


            
    # erpShellScriptsTab      
    def shellScripts(self, signal):
        """
        run David's shell scripts
        """

        self.count+=1

        sys.stdout = Log(self.erpShellScriptsOutputWindow)
        
            
        directoryInp = self.shellScriptsDir[2].text().strip()
        try:
            if not os.path.exists(directoryInp):
                print("ERROR: {} doesn\'t exist\nCheck path and run again.\n".format(directoryInp))
                raise FileNotFoundError
            else:
                ep.iter_shell_check(directoryInp)

        except (FileNotFoundError):
            e = sys.exc_info()
            print("ERROR TYPE: {}".format(e[0]))


        

        shellScriptText = self.erpShellScriptsOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log',  shellScriptText, self.count)
            
        sys.stdout = sys.__stdout__
            
    # erpH1PeaksTab & erpPsViewingTab         
    def createCheckbox(self, checkboxName, func_to_handle_toggle, hbox, vbox):
        """
        returns checkbox that only needs to be added to tab layout with setlayout()
        """
    
        self.checkboxName = checkboxName
        self.func_to_handle_toggle = func_to_handle_toggle
        self.hbox = hbox
        self.vbox = vbox

        checkbox = QCheckBox(checkboxName, self)
        checkbox.stateChanged.connect(func_to_handle_toggle)

        hbox.addWidget(checkbox)
        vbox.addLayout(hbox)
        return vbox, checkbox
    
    #erpH1PeaksTab                       
    def expCheckboxHandler(self):
        """
        When ERP Peak Picking checkbox is clicked, runs this function
        """
        expList = []
        if self.checkboxAll[1].isChecked():
            expList.extend(ep.dat_exps)
        if self.checkboxVP3[1].isChecked():
            expList.append('vp3')
        if self.checkboxCPT[1].isChecked():
            expList.append('cpt')
        if self.checkboxERN[1].isChecked():
            expList.append('ern')
        if self.checkboxANT[1].isChecked():
            expList.append('ant')
        if self.checkboxAOD[1].isChecked():
            expList.append('aod')
        if self.checkboxANS[1].isChecked():
            expList.append('ans')
        if self.checkboxSTP[1].isChecked():
            expList.append('stp')
        if self.checkboxGNG[1].isChecked():
            expList.append('gng')
        # return a set so user doesn't accientially choose 'all' & some other exps 
        return set(expList)
    
    # erpPsViewingTab
    def expCheckboxHandlerPs(self):
        """When ERP PS FILES checkbox is clicked, runs this function"""
        
        all_exps = ['vp3', 'cpt', 'ern', 'ant', 'aod', 'ans', 'stp', 'gng']
        
        expList = []
        if self.checkboxVP3Ps[1].isChecked():
            expList.append('vp3')
        if self.checkboxCPTPs[1].isChecked():
            expList.append('cpt')
        if self.checkboxERNPs[1].isChecked():
            expList.append('ern')
        if self.checkboxANTPs[1].isChecked():
            expList.append('ant')
        if self.checkboxAODPs[1].isChecked():
            expList.append('aod')
        if self.checkboxANSPs[1].isChecked():
            expList.append('ans')
        if self.checkboxSTPPs[1].isChecked():
            expList.append('stp')
        if self.checkboxGNGPs[1].isChecked():
            expList.append('gng')
        if self.checkboxAllPs[1].isChecked():
            expList.extend(all_exps)
            
        return set(expList)
        

    # erpH1PeaksTab
    def peaksH1(self, signal):
        """ creates avg.h1 files for peak picking outside of _32.cnt directory """
        # get inputs from GUI

        self.count+=1

        directoryInp = self.peaksDir[2].text().strip()
        directorytrg = self.peaksTrgDir[2].text().strip()
        directoryExclude = self.peaksExcludeDir[2].text().strip()
        files_set = self.expCheckboxHandler()
        
        sys.stdout = Log(self.erpH1PeaksOutputWindow)
        
        # do those dirs exist 
        self.pathExists([directoryInp])
        
        # why check path if its about to be created?
        #self.pathExists([directorytrg])
        

        # create avg.h1 for only 1 directory 
        dirs = [os.path.join(r,n) for r,d,f in os.walk(directoryInp) for n in d]
        if len(dirs) == 0:
             return sd.get_h1s(directoryInp, files_set, del_ext=True, trg_dir=directorytrg)
            
        # do files in excluded dirs exist   
        excludedToCheck = [directoryInp + '/' + i for i in directoryExclude.split()]
        self.pathExists(excludedToCheck)
        
        # if excluded dirs 
        if len(excludedToCheck) != 0:
            excluded = directoryExclude.split()
            include_dirs = [os.path.join(directoryInp, i) for i in os.listdir(directoryInp) if i not in excluded]
            count = 0
            for i in include_dirs:
                count+=1
                print("\n\n{}".format(count)), sd.get_h1s(i, files_set, del_ext=True, trg_dir=directorytrg)
                QApplication.processEvents()
        # create h1's in all sub-directories 
        else:
            count = 0
            for i in dirs:
                count+=1
                print("\n\n{}".format(count)), sd.get_h1s(i, files_set, del_ext=True, trg_dir=directorytrg)
                QApplication.processEvents()
        
        erpH1Text = self.erpH1PeaksOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.txt',  erpH1Text, self.count)

        sys.stdout = sys.__stdout__ 
    
    # erpPsViewingTab
    def createPsFiles(self, signal):
        """ creates avg.h1/h1.ps files for viewing purposes """
        
        self.count+=1

        directoryInp = self.psViewingDir[2].text().strip()
        directoryExclude = self.psViewingExcludeDir[2].text().strip()
        files_set = self.expCheckboxHandlerPs()
        
        sys.stdout = Log(self.erpPsViewingOutputWindow)
        
        self.pathExists([directoryInp])

        
        # create avg.h1 for only 1 directory 
        dirs = [os.path.join(r,n) for r,d,f in os.walk(directoryInp) for n in d]
        if len(dirs) == 0:
             return sd.get_h1s(directoryInp, files_set, ps=True) 
        # do files in excluded dirs exist     
        excludedToCheck = [directoryInp + '/' + i for i in directoryExclude.split()]
        self.pathExists(excludedToCheck)
        
        # if excluded dirs
        if len(excludedToCheck) != 0:
            
            excluded = directoryExclude.split()
            include_dirs = [os.path.join(directoryInp, i) for i in os.listdir(directoryInp) if i not in excluded]
            count = 0
            for i in include_dirs:
                count+=1
                print("\n\n{}".format(count)), sd.get_h1s(i, files_set, ps=True)
                QApplication.processEvents()
        # create h1's in all sub-directories 
        else:
            count = 0
            for i in dirs:
                count+=1
                print("\n\n{}".format(count)), sd.get_h1s(i, files_set, ps=True)
                QApplication.processEvents()
        
        erpPsText = self.erpPsViewingOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.txt',  erpPsText, self.count)

        sys.stdout = sys.__stdout__ 
                
    #erpMovePeaksTab           
    def movePeaks(self, signal):
        """
        moves peaks from a directory to the appropriate directory in HBNL
        directoryInp must not have exp name at the of path...
        /vol01/active_projects/anthony/waitingOn/erp_dec_suny/ant :(
        /vol01/active_projects/anthony/waitingOn/erp_dec_suny :)
        
        """
        self.count+=1

        sys.stdout = Log(self.erpMovePeaksOutputWindow)
        
        directoryInp = self.erpMovePeaksDir[2].text().strip()
        directorySite = self.erpMovePeaksSite[2].text().strip()

        self.pathExists([directoryInp])
        
        # get all sub ids from directoryINP
        unique_ids = list(set([re.split(r'[_.]', n)[3] for r,d,f in os.walk(directoryInp) for n in f if n.endswith(('avg.h1', 'avg.mt', 'h1.pdf'))]))
        # does first number in subID match directorySite?
        for i in unique_ids:
            checkIds(i, directorySite)
        
        start_mover(directoryInp, directorySite)
        QApplication.processEvents()
        
        movePeaksText = self.erpMovePeaksOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.txt',  movePeaksText, self.count)

        sys.stdout = sys.__stdout__       
        
# if __name__ == '__main__':
#     app = QCoreApplication.instance() ### adding this if statement prevents kernel from crashing 
#     if app is None:
#         app = QApplication(sys.argv)
#         print(app)
#     ex = App()
#     sys.exit(app.exec_())
        
       
app = QApplication(sys.argv)
GUI = App()
sys.exit(app.exec_())
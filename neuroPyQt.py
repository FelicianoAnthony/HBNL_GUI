from PyQt5.QtWidgets import (QMainWindow, QApplication, QPushButton, QWidget, QAction, 
                             QTabWidget,QVBoxLayout, QHBoxLayout, QInputDialog, QLineEdit, QLabel,
                             QFileDialog, QMainWindow, QTextEdit, QMessageBox, QCheckBox, QTableView,
                             QHeaderView)
from PyQt5.QtGui import QIcon, QTextCursor, QFont, QPixmap
from PyQt5.QtCore import (pyqtSlot, QCoreApplication, QProcess, QObject, pyqtSignal,QCoreApplication, 
                          QAbstractTableModel, QVariant, QModelIndex, QRect)
from PyQt5.QtCore import Qt
import sys
import os
import pandas as pd
from random import choice

# neuropsych function modules
from collections import defaultdict, Counter
from glob import glob
import shutil
import re
from datetime import datetime
import hashlib
import functools


# class to display data frame in PyQt

class PandasModel(QAbstractTableModel): 
    def __init__(self, df = pd.DataFrame(), parent=None): 
        QAbstractTableModel.__init__(self, parent=parent)
        self._df = df

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()

        if orientation == Qt.Horizontal:
            try:
                return self._df.columns.tolist()[section]
            except (IndexError, ):
                return QVariant()
        elif orientation == Qt.Vertical:
            try:
                # return self.df.index.tolist()
                return self._df.index.tolist()[section]
            except (IndexError, ):
                return QVariant()

    def data(self, index, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()

        if not index.isValid():
            return QVariant()

        return QVariant(str(self._df.ix[index.row(), index.column()]))

    def setData(self, index, value, role):
        row = self._df.index[index.row()]
        col = self._df.columns[index.column()]
        if hasattr(value, 'toPyObject'):
            # PyQt4 gets a QVariant
            value = value.toPyObject()
        else:
            # PySide gets an unicode
            dtype = self._df[col].dtype
            if dtype != object:
                value = None if value == '' else dtype.type(value)
        self._df.set_value(row, col, value)
        return True

    def rowCount(self, parent=QModelIndex()): 
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()): 
        return len(self._df.columns)

    def sort(self, column, order):
        colname = self._df.columns.tolist()[column]
        self.layoutAboutToBeChanged.emit()
        self._df.sort_values(colname, ascending= order == QtCore.Qt.AscendingOrder, inplace=True)
        self._df.reset_index(inplace=True, drop=True)
        self.layoutChanged.emit()


##############################################################################################################
# move neuropsych files

def file_counter(base_path, num_files_dict):
    """
    creates a list of new neuropsych data files prepended with...
    /raw_data/neuropsych/site/subdir + newdata fname from num_files_dict
    """
    
    multiply_files = []
    for k,v in num_files_dict.items():
        dir_path = "{}/{}".format(base_path, k)
        file_freq = (dir_path * v).split('/vol01')
        multiply_files.extend(file_freq)
        
    return ['/vol01' + i for i in multiply_files if i]

def move_neuro_files(new_site_data, neuro_path_server):
    """
    COPIES neuropsych data to raw data/site/subID
    checks if file exists before moving
    creates new dirs if they dont already exist
    """
    
    # get count of how many files per sub in each directory of new site data 
    num_files_dict = defaultdict(int)
    for r,d,f in os.walk(new_site_data):
        for n in f:
            sub_ids = n.split('_')[0]
            num_files_dict[sub_ids] +=1
            
    # get dir names from neuropsych dics to check against raw_data/neuropsych/site
    disc_dir_names = list(num_files_dict.keys())
    
    # if dirs exist in raw data, append those dirs to a list -- ONLY IDS 
    dirs_found = []
    for i in disc_dir_names:
        neuro_dirs = glob(neuro_path_server + '/' + i)
        for nd in neuro_dirs:
            if os.path.exists(nd) == True:
                dirs_found.append(os.path.basename(nd))
                
    # here are the dirs that need to be created - ONLY IDS 
    to_be_created = set(disc_dir_names) ^ set(dirs_found)
    
    # remove to_be_created from num_files_dict & create new dirs & add keys that were removed to a new dict 
    to_be_created_dict = {}
    new_dirs = []
    if len(to_be_created) != 0:
        for new_dir in list(to_be_created):
            if new_dir in num_files_dict.keys():
                to_be_created_dict[new_dir] = num_files_dict[new_dir]
            del num_files_dict[new_dir]
            new_dir = [neuro_path_server + '/' + new_dir]
            for dirs in new_dir:
                if os.path.exists(dirs):
                    print('This directory ({}) already exists'.format(dirs))
                else:
                    os.makedirs(dirs)
                    print('Making new directory {}\n'.format(dirs))
                    new_dirs.append(dirs) 
                    
    # key for neuro_dict dictionary -- is a list of files with dirs that exist in raw_data                 
    dirs_that_exist = file_counter(neuro_path_server, num_files_dict)
    
    # walk through new data & separate PATH + FILENAME by whether it was found in raw_data
    files_to_move = []
    files_that_need_new_dirs = []
    for r,d,f in os.walk(new_site_data):
        for n in d:
            if n in dirs_found:
                path = os.path.join(r,n)
                files = os.listdir(path)
                for fi in files:
                    have_rawdata_dir = r + '/' + n + '/' + fi
                    files_to_move.append(have_rawdata_dir)
            else:
                new_dirs_path = os.path.join(r,n)
                new_dirs_files = os.listdir(new_dirs_path)
                for new in new_dirs_files:
                    files_that_need_new_dirs.append(os.path.join(new_dirs_path,new))
                    
                    
    # checks to see that number of files found in new data folders equal number of files found when...
    # searching rawdata for that directory 
    try: 
        if len(dirs_that_exist) != len(files_to_move):
            raise Exception ('heres an error.  figure it out')
    except Exception as e:
        print(str(e))
        
    # key for neuro_dict_new_dirs dictionary -- is a list of files with dirs NOT existing in raw_data 
    dirs_that_dont_exist = file_counter(neuro_path_server,to_be_created_dict)
    
    neuro_dict = {}
    for server, site in zip(sorted(dirs_that_exist), sorted(files_to_move)):
        neuro_dict.setdefault(server, []).append(site)
        
    neuro_dict_new_dirs = {}
    for server, site in zip(sorted(dirs_that_dont_exist), sorted(files_that_need_new_dirs)):
        neuro_dict_new_dirs.setdefault(server, []).append(site)
        
    neuro_dict.update(neuro_dict_new_dirs)
    
    # move files 
    subs_moved = []
    count = 0
    print('>>> Moving neuropsych files <<< ')
    for k,v in neuro_dict.items():
        count+=1
        print("\n\n{} || {}\n".format(count,k))
        for newdata in v:
            to_be_moved = os.path.join(k, os.path.basename(newdata))
            if not os.path.exists(to_be_moved):
                shutil.copy(newdata, to_be_moved)
                print('\nNew Data Directory - {}\nRaw Data Directory - {}'.format(newdata, to_be_moved))
                subs_moved.append(to_be_moved)
            else:
                print('{}\n file already exists in \n{}\n'.format(newdata, os.path.dirname(to_be_moved)))
                
    num_subs = set([os.path.basename(i).split('_')[0] for i in subs_moved])
    print('\n\nTotal of {} subjects moved from {} to {}\n\n'.format(len(num_subs), new_site_data, neuro_path_server))



##############################################################################################################
# create data frame from xml files

def neuro_xml_to_df(path):
    """Given a full path to neuropsych sub folders, returns data frame of first 6 lines of xml file"""

    xml = [os.path.join(root,name) for root,dirs,files in os.walk(path) for name in files if name.endswith(".xml")]

    ids_lst=[]
    dob_lst = []
    gen_lst=[]
    test_lst =[]
    ses_lst=[]
    han_lst=[]
    for i in xml:
        with open(i) as f:
            for line in f:
                if line.startswith('  <Sub'):
                    ids_lst.extend(re.findall(r'<SubjectID>(.*?)</SubjectID>', line))
                if line.startswith('  <DOB'):
                    dob_lst.extend(re.findall(r'<DOB>(.*?)</DOB>', line))
                if line.startswith('  <Gen'):
                    gen_lst.extend(re.findall(r'<Gender>(.*?)</Gender>', line))
                if line.startswith('  <Test'):
                    test_lst.extend(re.findall(r'<TestDate>(.*?)</TestDate>', line))
                if line.startswith('  <Sess'):
                    ses_lst.extend(re.findall(r'<SessionCode>(.*?)</SessionCode>', line))
                if line.startswith('  <Hand'):
                    han_lst.extend(re.findall(r'<Hand>(.*?)</Hand>', line))

    data_set = pd.DataFrame(ids_lst, columns=["Subject ID"])
    data_set['Test_Date'] = test_lst
    data_set['DOB'] = dob_lst
    data_set['Gender'] = gen_lst
    data_set['Handedness'] = han_lst
    data_set['Run Letter'] = ses_lst

    data_set['Test_Date'] =pd.to_datetime(data_set.Test_Date)
    table = data_set.sort_values('Test_Date', ascending=True)
    print("sorting by test date...")
    return table


##############################################################################################################
# review neuropsych data & check for duplicates 

class neuropsych_check:
    


    def create_neuro_dict(self, key, neuro_dict, inner_key, inner_inner_key, value):
        """
        formats nested dictionary of lists
        """
        
        self.key = key
        self.neuro_dict = neuro_dict
        self.inner_key = inner_key
        self.inner_inner_key = inner_inner_key
        self.value = value
            
        return neuro_dict.setdefault(key, {}).setdefault(inner_key, {}).setdefault(inner_inner_key, []).append(value)



    def parse_neuro_files(self, path):
        """
        parse all relevant info from sum.txt/txt/xml file NAMES into nested dictionary
        """
        self.path = path
        
        key = path.split('/')[-1]

        neuro_dict = {}
        for f in os.listdir(path):
            if f.endswith('_sum.txt'):
                sum_txt_split = f.split('_')
                self.create_neuro_dict(key, neuro_dict, 'sum.txt', 'exp_name', sum_txt_split[1])
                self.create_neuro_dict(key, neuro_dict, 'sum.txt', 'run_letter', sum_txt_split[3][0])
                self.create_neuro_dict(key, neuro_dict, 'sum.txt', 'num_files', sum_txt_split[-1])
                self.create_neuro_dict(key, neuro_dict, 'sum.txt', 'id', sum_txt_split[0])
            if not f.endswith('_sum.txt') and not f.endswith('xml'):
                txt_split = re.split(r'[_.]', f)
                self.create_neuro_dict(key, neuro_dict, 'txt', 'exp_name', txt_split[1])
                self.create_neuro_dict(key, neuro_dict, 'txt', 'run_letter', txt_split[3][0])
                self.create_neuro_dict(key, neuro_dict, 'txt', 'num_files', txt_split[-1])
                self.create_neuro_dict(key, neuro_dict, 'txt', 'id', txt_split[0])
            ### need to create optarg for this below
            if f.endswith('xml'):
                xml_split = re.split(r'[_.]', f)
                neuro_dict.setdefault(key, {}).setdefault('xml', {})['id']=xml_split[0]
                neuro_dict.setdefault(key, {}).setdefault('xml', {})['num_files']=xml_split[-1]
                neuro_dict.setdefault(key, {}).setdefault('xml', {})['run_letter']=xml_split[1]
                
        return neuro_dict


    def neuro_dict_check(self, neuro_dict, file_ext):
        """
        take dictionary from parse_neuro_files  & check for errors
        """
        self.neuro_dict = neuro_dict
        self.file_ext = file_ext
        
        exp_lst = ['TOLT', 'CBST']
        
        error_list = []
        for k,v in neuro_dict.items():
            for k1,v1 in v.items():
                if k1 == file_ext:
                    for k2,v2 in v1.items():
                        if k2 == 'exp_name':
                            for exp in v2:
                                if exp not in exp_lst:
                                    error_list.append('Error: Missing experiment for a {} file for {}'.format(file_ext, k))
                        if k2 == 'id':
                            if len(set(v2)) != 1:
                                error_list.append('Error: Incorrect ID in {} file for {}'.format(file_ext, k))
                            for sub_id in v2:
                                if len(sub_id) != 8:
                                     error_list.append('Error: Sub ID incorrect length in {} file for {}'.format(file_ext, k))
                        if k2 == 'num_files':

                            if v2.count(file_ext) != 2:
                                error_list.append('Error: Missing a {} file for {}'.format(file_ext, k))
        return error_list

                                

    def parse_inside_xml(self, path):
        """
        create dictionary of important stuff INSIDE XML FILE 
        """
        self.path = path
        
        key = path.split('/')[-1]
        
        xml = [os.path.join(path, f) for f in os.listdir(path) if f.endswith('xml')]


        xml_dict = {}
        with open(''.join(xml)) as f:
            for line in f:
                if line.startswith('  <Sub'):
                    sub = ''.join(re.findall(r'<SubjectID>(.*?)</SubjectID>', line))
                    xml_dict.setdefault(key, {})['id']=sub
                if line.startswith('  <Sess'):
                    run = ''.join(re.findall(r'<SessionCode>(.*?)</SessionCode>', line))
                    xml_dict.setdefault(key, {})['run_letter'] = run
                if line.startswith('  <Motivation>'):
                    motiv= ''.join(re.findall(r'<Motivation>(.*?)</Motivation>', line))
                    xml_dict.setdefault(key, {})['motiv'] = motiv
                if line.startswith('  <DOB>'):
                    dob =  ''.join(re.findall(r'<DOB>(.*?)</DOB>', line))
                    xml_dict.setdefault(key, {})['dob'] = dob
                if line.startswith('  <TestDate>'):
                    test_date = ''.join(re.findall(r'<TestDate>(.*?)</TestDate>', line))
                    xml_dict.setdefault(key, {})['test_date'] = test_date
                if line.startswith('  <Gender>'):
                    gender =  ''.join(re.findall(r'<Gender>(.*?)</Gender>', line))
                    xml_dict.setdefault(key, {})['gender'] = gender
                if line.startswith('  <Hand>'):
                    hand = ''.join(re.findall(r'<Hand>(.*?)</Hand>', line))
                    xml_dict.setdefault(key, {})['hand'] = hand
        return xml_dict



    def inside_xml_error_check(self, inside_xml_dict, neuro_year):
        """
        check stuff INSIDE XML FILE -- except id & run letter & motivation score 
        """

        self.inside_xml_dict = inside_xml_dict
        self.year = neuro_year
        
        error_list = []
        for k,v in inside_xml_dict.items():
            for k1,v1 in v.items():
                # is sub ID 8 characters long?
                if k1 == 'id':
                    if len(v1) != 8:
                        error_list.append('Error: Sub ID incorrect length in {} file'.format(k))
                # is dob later than 2010??
                if k1 == 'dob':
                    date_split = v1.split('/')
                    year = int(date_split[-1])
                    if year > 2010:
                        error_list.append('Error: Check DOB in xml file for {}'.format(k))
                # is test year later than current year? __________ probably needs revamping      
                if k1 == 'test_date':
                    test_split = v1.split('/')
                    test_year = int(test_split[-1])
                    if test_year != int(neuro_year):
                        error_list.append('Error: Check test date in xml file for {}'.format(k))
                # is gender & handedness capitalized??
                if k1 == 'gender':
                    if not v1[0].isupper(): #maybe str.istitle() would be better?
                        error_list.append('Error: Make gender uppercase in xml file for {}'.format(k))
                if k1 == 'hand':
                    if not v1[0].isupper():
                        error_list.append('Error: Make handedness uppercase in xml file for {}'.format(k))

        return error_list



    def xml_check(self, path, xml_dict, neuro_dict):
        """
        checks sub ID & run letter between inside & outside of xml file
        """
        self.xml_dict = xml_dict
        self.neuro_dict = neuro_dict
        self.path = path

        
        key = path.split('/')[-1]
        
        error_list = []
        
        # xml checks -- id
        xml_inside_id = xml_dict[key]['id']
        xml_outside_id = neuro_dict[key]['xml']['id']

        if xml_inside_id != xml_outside_id:
            error_list.append("Error: Subject ID inside xml doesn't match ID outside xml for {}".format(key))

        # xml checks -- run letter
        xml_inside_run = xml_dict[key]['run_letter']
        xml_outside_run = neuro_dict[key]['xml']['run_letter']

        if xml_inside_run != xml_outside_run:
             error_list.append("Error: Run Letter inside xml doesn't match run letter outside xml for {}".format(key))
        
        # check run letter between xml filename & sum.txt/txt files 
        sum_txt_run = set(neuro_dict[key]['sum.txt']['run_letter'])
        txt_run = set(neuro_dict[key]['txt']['run_letter'])

        if txt_run != sum_txt_run:
            error_list.append("Error: Run letter in txt file doesn't match sum.txt file for {}".format(key))
          
        return error_list
    
    
    def md5(self, path):
        """
        generate md5 -- read file in binary mode 
        """
        self.path = path

        with open(path, "rb") as f:
            data = f.read()
            md5_return = hashlib.md5(data).hexdigest()
            return md5_return
    

    def md5_check_walk(self, path):
        """
        return any file pairs with matching checksums 
        """
        self.path = path
        
        md5_dict = defaultdict(list)
        for r,d,f in os.walk(path):
            for n in f:
                fp = os.path.join(r,n)
                md5_dict[self.md5(fp)].append(fp)
        
        dupes_list = []
        for k,v in md5_dict.items():
            if len(v) > 1:  #multiple values for the same key
                dupes_list.append("Error: Identical files found:\n")
                for dupe in v:
                    dupes_list.append("Filename: {}\nChecksum: {}\n".format(dupe,k))
                   
        if len(dupes_list) != 0:
            for dupe in dupes_list:
                print(dupe)
        else:
            print('No duplicates found!')

            
    def run_all(self, path, year):
        """
        combines all methods into 1 giant method 
        """
        
        self.path = path
        self.year = year
        
        file_ext = ['txt', 'sum.txt']
        
        errors = []
        errors_duplicates = []
        for ext in file_ext:
        
            # check for txt/sum.txt files
            neuro_dict = self.parse_neuro_files(path)
            err1 = self.neuro_dict_check(neuro_dict, ext)
            errors.extend(err1)

            # check for xml files
            xml_dict = self.parse_inside_xml(path)
            err2 = self.inside_xml_error_check(xml_dict, year)
            errors.extend(err2)
            
            err3 = self.xml_check(path, xml_dict, neuro_dict)
            errors.extend(err3)

        unique_errors = set(errors)
        if len(list(unique_errors)) == 0:
            print("No errors found in {}".format(path))

        for i in list(unique_errors):
            if i is None:
                pass
            else:
                print("{}\n\n".format(i))
        
                            
        
np = neuropsych_check()


##############################################################################################################
# check server to see if new neuropsych files exist 

def np_run_exists(path_to_new_data, site):
    """
    given a path to new data and str(site) -- 
    tells if file already exists in directory
    """
    
    np_basename = '/vol01/raw_data/neuropsych/'
    
    files = []
    for r,d,f in os.walk(path_to_new_data):
        for n in f:
            files.append(n)
            
         
    np_full_path = np_basename + site
    
    duplicate_files = []  
    for r,d,f in os.walk(np_full_path):
        for n in f:
            if n in files:
                path = os.path.join(r,n)
                duplicate_files.append(path)
    
    if len(duplicate_files) == 0:
        print('All files are unique')
    else:
        print('The following files already exist in {}...\n'.format(np_full_path))
        count = 0
        for idx, i in enumerate(duplicate_files):
            if idx % 5 == 0:
                print('\n{}'.format(i))
            else:
                print(i)


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
        
        self.title = 'Site Data Tools - Neuropsych'
        self.left = 0
        self.top = 0
        self.width = 1400
        self.height = 400
        self.setWindowTitle(self.title)
        self.setWindowIcon(QIcon('/vol01/active_projects/anthony/brain.jpg'))
        self.setGeometry(self.left, self.top, self.width, self.height)
        
        now = datetime.now()
        self.fname = '/vol01/active_projects/anthony/pyqt_logs/neuro/' + sys.argv[1].split('-')[-1] + '_' + now.strftime("%Y-%m-%d_%H-%M")
        self.count = 0
        
        self.stylesheet = """ 
        QTabBar::tab:selected {background: black;}
        QTabWidget>QWidget>QWidget{background: black;}
        """
        
        # Initialize tab widget
        self.tabs = QTabWidget()
        # init tabs
        self.initCheckServerTab()
        self.initReviewDataTab()
        self.initXmlTab()
        self.initMoveFilesTab()
        self.addTabsAndShow()
            
    def initCheckServerTab (self):
        """
        creates Check Server tab
        """

        # CREATE tab & layouts
        self.neuroCheckServerTab = QWidget()
        self.neuroCheckServerLayout = QVBoxLayout()
        self.neuroCheckServerGrid = QHBoxLayout()
        self.neuroCheckServerOutputWindow = QTextEdit()

        # CREATE input boxes & buttons
        self.neuroCheckServerDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/pyqt_neuro', self.neuroCheckServerLayout)
        self.neuroCheckServerSite = self.createWidgetLayout('Site: ', 'indy', self.neuroCheckServerLayout)
        self.neuroCheckServerButton = self.createButtons('Do files exist?', self.checkServer)
        self.neuroCheckServerClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.neuroCheckServerOutputWindow))
        # horizontal button grid 
        neuroCheckServerButtons = self.buttonRow(self.neuroCheckServerButton, self.neuroCheckServerClearButton, self.neuroCheckServerGrid)

        # ADD css 
        self.cssInstructions(self.neuroCheckServerDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroCheckServerSite[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroCheckServerButton, "INCONSOLATA", 22, '#000000',  'white')
        self.cssInstructions(self.neuroCheckServerClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.neuroCheckServerOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.neuroCheckServerTab.setStyleSheet(self.stylesheet)

        # ADD to tab
        self.neuroCheckServerTab.setLayout(self.neuroCheckServerDir[0])
        self.neuroCheckServerTab.setLayout(self.neuroCheckServerSite[0])
        self.neuroCheckServerLayout.addLayout(neuroCheckServerButtons)
        self.neuroCheckServerLayout.addWidget(self.neuroCheckServerOutputWindow)

    def initReviewDataTab(self):
        """
        creates Review Data tab
        """
        
        # CREATE tab & set layouts
        self.neuroReviewDataTab = QWidget()
        self.neuroReviewDataLayout = QVBoxLayout()
        self.neuroReviewDataButtonGrid = QHBoxLayout()
        self.neuroReviewDataOutputWindow = QTextEdit()

        # CREATE input boxes & buttons    
        self.neuroReviewDataDir = self.createWidgetLayout('Directory: ', '/vol01/active_projects/anthony/pyqt_neuro', self.neuroReviewDataLayout)
        self.neuroReviewDataYear = self.createWidgetLayout('Year: ', '2017', self.neuroReviewDataLayout)
        self.neuroReviewDataButton = self.createButtons('Review Data', self.reviewData)
        self.neuroReviewDataDuplicates = self.createButtons('Duplicate Check', self.duplicateCheck)
        self.neuroReviewDataClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.neuroReviewDataOutputWindow))
        neuroReviewDataButtons = self.buttonRow(self.neuroReviewDataButton, self.neuroReviewDataDuplicates, self.neuroReviewDataButtonGrid, btn3=self.neuroReviewDataClearButton)

        # ADD css
        self.cssInstructions(self.neuroReviewDataDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroReviewDataYear[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroReviewDataButton, "INCONSOLATA", 22, '#000000',  'white')
        self.cssInstructions(self.neuroReviewDataDuplicates, "INCONSOLATA", 22, '#000000',  'white')
        self.cssInstructions(self.neuroReviewDataClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.neuroReviewDataOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.neuroReviewDataTab.setStyleSheet(self.stylesheet)

        # ADD to tab
        self.neuroReviewDataTab.setLayout(self.neuroReviewDataDir[0])
        self.neuroReviewDataTab.setLayout(self.neuroReviewDataYear[0])
        self.neuroReviewDataLayout.addLayout(neuroReviewDataButtons)
        self.neuroReviewDataLayout.addWidget(self.neuroReviewDataOutputWindow)

    def initXmlTab(self):
        """
        creates XML to data frame tab
        """

        # CREATE tab & layout
        self.neuroXmlDataFrameTab = QWidget()
        self.neuroXmlDataFrameLayout = QVBoxLayout()
        self.neuroXmlDataFrameDir = self.createWidgetLayout('Directory: ', '/vol01/raw_data/staging/indiana', self.neuroXmlDataFrameLayout)
        self.neuroXmlDataFrameButton = self.createButtons('Create Data frame', self.createDataFrame)

        # CREATE widget to show data frame
        self.tableView=QTableView()
        self.tableView.setObjectName('Neuropsych')
        self.tableView.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.tableView.setMinimumHeight(200)
        self.neuroXmlDataFrameLayout.addWidget(self.tableView)

        # message letting you know if directory exists or not 
        self.startStatus = QLabel('Enter directory...')
        self.startStatus.setFixedHeight(150)
        self.startStatus.setWordWrap(True)
        self.startStatus.setStyleSheet("color: white;")

        # ADD css
        self.cssInstructions(self.neuroXmlDataFrameDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroXmlDataFrameButton, "INCONSOLATA", 22, '#000000',  'white')
        self.neuroXmlDataFrameTab.setStyleSheet(self.stylesheet)

        # ADD to tab 
        self.neuroXmlDataFrameLayout.addWidget(self.tableView)
        self.neuroXmlDataFrameLayout.addWidget(self.startStatus)
        self.neuroXmlDataFrameLayout.addWidget(self.neuroXmlDataFrameButton)
        self.neuroXmlDataFrameTab.setLayout(self.neuroXmlDataFrameDir[0])


    def initMoveFilesTab(self):
        """
        Creates tab that moves new neuropsych files to raw_data/neuropsych/_site_
        """

        # CREATE tab & layouts
        self.neuroMoveFilesTab = QWidget()
        self.neuroMoveFilesLayout = QVBoxLayout()
        self.neuroMoveFilesButtonGrid = QHBoxLayout()
        self.neuroMoveFilesOutputWindow = QTextEdit()

        # CREATE directory boxes & buttons
        self.neuroMoveFilesNewDataDir = self.createWidgetLayout('New Data Directory: ', '/vol01/raw_data/staging/indiana', self.neuroMoveFilesLayout)
        self.neuroMoveFilesTrgDir = self.createWidgetLayout('Raw Data Directory: ', '/vol01/active_projects/anthony/test_neuro/site_name', self.neuroMoveFilesLayout)
        self.neuroMoveFilesButton = self.createButtons('Move to raw_data', self.neuroMoveFiles)
        self.neuroMoveFilesClearButton = self.createButtons('Clear all text', functools.partial(self.clearWindowText, windowName = self.neuroMoveFilesOutputWindow))
        neuroMoveFilesButtons = self.buttonRow(self.neuroMoveFilesButton, self.neuroMoveFilesClearButton, self.neuroMoveFilesButtonGrid)

        # ADD css
        self.cssInstructions(self.neuroMoveFilesNewDataDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroMoveFilesTrgDir[1], "INCONSOLATA", 22, 'white', '#000000')
        self.cssInstructions(self.neuroMoveFilesButton , "INCONSOLATA", 22, '#000000',  'white')
        self.cssInstructions(self.neuroMoveFilesClearButton, "INCONSOLATA", 22, '#000000', 'white')
        self.cssInstructions(self.neuroMoveFilesOutputWindow, "INCONSOLATA", 14, 'black', 'white')
        self.neuroMoveFilesTab.setStyleSheet(self.stylesheet)

        # SET layouts
        self.neuroMoveFilesTab.setLayout(self.neuroMoveFilesNewDataDir[0])
        self.neuroMoveFilesTab.setLayout(self.neuroMoveFilesTrgDir[0])
        self.neuroMoveFilesLayout.addLayout(neuroMoveFilesButtons)
        self.neuroMoveFilesLayout.addWidget(self.neuroMoveFilesOutputWindow)

    
    def addTabsAndShow(self):
        """
        add the above tabs to GUI & show
        """

        self.tabs.addTab(self.neuroCheckServerTab, "Do files already exist?")
        self.tabs.addTab(self.neuroReviewDataTab, "Filename and duplicates check")
        self.tabs.addTab(self.neuroXmlDataFrameTab, "Parse xml file")
        self.tabs.addTab(self.neuroMoveFilesTab, "Move to raw data")

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
        creates a row of buttons
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
        """
        clear window within tab 
        """
        self.windowName = windowName
        windowName.clear()
        
        
    def trailingSlashes(self, inputsList):
        """
        checks to see if inputs have trailing slash, some functions wont work otherwise 
        """
        self.inputsList = inputsList
        try: 
            for i in inputsList:
                if i.endswith('/'):
                    print("Remove the trailing slash from {}".format(i)) 
                    raise Exception
        except Exception as e:
            e = sys.exc_info()
            print("ERROR TYPE: {}".format(e[0]))
    
    
    def neuroMoveFiles(self):
        """
        handles moving neuropsych files when button is clicked. 
        error handling taken care of.
        """

        self.count = 0



       	

        directoryNewDataDir = self.neuroMoveFilesNewDataDir[2].text().strip()
        directoryTrgDir = self.neuroMoveFilesTrgDir[2].text().strip()
        
        
        self.pathExists([directoryNewDataDir])
        self.pathExists([directoryTrgDir])
        
        
        sys.stdout = Log(self.neuroMoveFilesOutputWindow)
        
        site_dict = {'1': 'uconn', '2': 'indy', '3': 'iowa',
                     '4': 'suny', '5': 'washu', '6': 'ucsd'}
        
        # get info needed for error handling 
        siteName = directoryTrgDir.split('/')[-1]
        dirId = set([n[0] for r,d,f in os.walk(directoryNewDataDir) for n in d])
        siteNum = ''.join(dirId)
        siteToId = siteNum in site_dict and siteName == site_dict[siteNum] 
        rawDataDirs = list(site_dict.values())
        
        # what does this even do?
        #try:
            #ints = int(directoryNewDataDir.split('/')[-1])
        #except Exception as e:
            #e = sys.exc_info()
            #print("ERRORSSSS TYPE: {}".format(e[0]))
        # error handling "logic"   
        try: 
            # split str.split wont work if theres a trailing / 
            if directoryNewDataDir.endswith('/') or directoryTrgDir.endswith('/'):
                print("Remove trailing '/' character.")
                raise RuntimeError
            # prevent accidential target directory being a sub folder 
            for i in [siteName]:
                if i not in rawDataDirs:
                    print("{} is not a directory name in /raw_data/neuropsych".format(siteName))
                    raise RuntimeError
            # make sure all IDs of data to be moved is of the same ID
            if len(dirId) is 1:
                pass
            else:
                print("There are participants from different sites in this folder.\n\nID numbers = {}".format(dirId))
                raise RuntimeError
            # make sure site exists in ./raw_data/neuropsych/__sitename__
            if siteToId == True:
                move_neuro_files(directoryNewDataDir, directoryTrgDir)
            else:
                print("Cannot move IDs beginning with {} to {} folder.".format(dirId, siteName))
                raise RuntimeError

        except (RuntimeError) as e:
            e = sys.exc_info()
            print("ERROR TYPE: {}".format(e[0]))

        moveFilesText = self.neuroMoveFilesOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log', moveFilesText, self.count)   
            
        sys.stdout = sys.__stdout__

    
    def createDataFrame(self):
        """
        corresponds to parse xml file tab 
        """
        
        directoryInp = self.neuroXmlDataFrameDir[2].text().strip()
        
        if not os.path.exists(directoryInp):
            self.startStatus.setText("{} doesn't exist.  Check filepath again!".format(directoryInp))
        else:
            self.startStatus.setText("Good to go!")
        
        df = neuro_xml_to_df(directoryInp)
        model = PandasModel(df)
        self.tableView.setModel(model)
        
        
    def duplicateCheck(self):
        """
        corresponds to Review data tab 
        """
        self.count+=1

        sys.stdout = Log(self.neuroReviewDataOutputWindow)
    
        directoryInp = self.neuroReviewDataDir[2].text().strip()
        self.pathExists([directoryInp])
        
        dirs = [os.path.join(r,n) for r,d,f in os.walk(directoryInp) for n in d]
        
        if len(dirs) != 0:
            for d in dirs:
                np.md5_check_walk(d)
        else:
            for i in [directoryInp]:
                np.md5_check_walk(i)
                QApplication.processEvents()
                
        duplicateCheckText = self.neuroReviewDataOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log', duplicateCheckText, self.count)

                
        sys.stdout = sys.__stdout__
        
    def checkNeuroSubdirs(self, path):
        """
        checks to make sure there's no accidental subdirectories inside each sub folder 
        """
        self.path = path

        directoryInp = self.neuroReviewDataDir[2].text().strip()


        all_neuro_dirs = [os.path.dirname(os.path.join(r,n)) for r,d,f in os.walk(path) for n in d]
        return [i for i in all_neuro_dirs if i!= directoryInp] 
        
    def reviewData(self, signal):
        """
        corresponds to Review data tab
        """
        self.count+=1
        
        directoryInp = self.neuroReviewDataDir[2].text().strip()
        directoryYear = self.neuroReviewDataYear[2].text().strip()
        
        sys.stdout = Log(self.neuroReviewDataOutputWindow)
        
        self.pathExists([directoryInp])


        
        dirs = [os.path.join(r,n) for r,d,f in os.walk(directoryInp) for n in d]




        bad_dirs = self.checkNeuroSubdirs(directoryInp.strip('/'))

        
        # NEED TO MAKE THIS WORK FOR SINGLE NEUROPSYCH FOLDERS --  CURRENTLY WORKS FOR MULTIPLE
        if len(bad_dirs) !=0:
            for i in bad_dirs:
                print("ERROR: {} erroneously has a folder within it -- Please move or remove & run check again.".format(i))
            return True




        
        if len(dirs) != 0:
            for d in dirs:
                np.run_all(d, directoryYear)

        else:
            lst = []
            for r,d,f in os.walk([directoryInp]):
                for n in d:
                    path = os.path.join(r,n)
                    lst.append(os.path.dirname(path))
            if len(lst) != 0:
                for i in lst:
                    print("ERROR: {} erroneously has a folder within it -- Please move or remove & run check again.".format(i))
                return True


            for i in [directoryInp]:
                np.run_all(i, directoryYear)
                QApplication.processEvents()

        reviewDataText = self.neuroReviewDataOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log', reviewDataText, self.count)
                
        sys.stdout = sys.__stdout__
        

    # neuroCheckServerTab
    def checkServer(self, signal):
        """ check if new neuropsych data already exists on server"""
        
        self.count+=1

        sys.stdout = Log(self.neuroCheckServerOutputWindow)
        
        
        directoryInp = self.neuroCheckServerDir[2].text().strip()
        directorySite = self.neuroCheckServerSite[2].text().strip()
        
        # quick check to make sure site text box input matches IDs in neuropsych folder
        rawDataPath = directoryInp + '/' + directorySite
        
        site_dict = {'1': 'uconn', '2': 'indy', '3': 'iowa',
                     '4': 'suny', '5': 'washu', '6': 'ucsd'}
        
        try:
            site_num = [i[0] for i in os.listdir(directoryInp)][0]
            matchesOrNot = site_num in site_dict and directorySite == site_dict[site_num]
            if matchesOrNot == False:
                print("ERROR: Site input ({}) doesn't match IDs (site {}) in {} ".format(directorySite, site_num, directoryInp))
                raise FileNotFoundError
            else:
                np_run_exists(directoryInp, directorySite)
        except (FileNotFoundError):
            e = sys.exc_info()
            print("ERROR TYPE: {}".format(e[0]))

        checkServerText = self.neuroCheckServerOutputWindow.toPlainText()
        self.write_logging_file(self.fname + '.log', checkServerText, self.count)
        
        sys.stdout = sys.__stdout__

    # len(return) == 3   
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
    
    def createInstructionsLayout(self, qLabelInstructions, vbox):
        """
        returns layout for instructions 
        all you need to do is SetLayout on return[0]
        use return[1] to style with css
        """
        
        self.qLabelInstructions = qLabelInstructions
        self.vbox = vbox
        
        instructionsLayout = QHBoxLayout()
        instructions = QLabel(qLabelInstructions)
        
        instructionsLayout.addWidget(instructions)
        vbox.addLayout(instructionsLayout)
        return vbox, instructions
    
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
        
        
    
    def cssInstructions(self, buttonName, fontFamily, fontSize, fontColor, bgroundColor):
        
        self.buttonName = buttonName
        self.fontFamily = fontFamily
        self.fontSize = fontSize
        self.fontColor = fontColor
        self.bgroundColor = bgroundColor
        
        buttonFont = QFont(fontFamily, int(fontSize)) #QFont("SansSerif", 20, QFont.Bold) 
        formatCSS = "color: {}; background-color: {};".format(fontColor, bgroundColor)
        buttonName.setStyleSheet(formatCSS)
        buttonName.setFont(buttonFont)
        
        
    def cssCheckboxes(self,checkboxName,widthHeightTuple):
        
        self.checkboxName = checkboxName
        self.widthHeightTuple = widthHeightTuple
        
        formatCSS = "QCheckBox::indicator {{ width:{}px; height: {}px;}}".format(str(widthHeightTuple[0]), str(widthHeightTuple[1]))
        checkboxName.setStyleSheet(formatCSS)
        
        
    def pathExists(self, filepath): 
        """
        stops executing of script if filepath doesnt exist
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
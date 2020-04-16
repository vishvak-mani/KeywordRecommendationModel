import pke
from nltk.corpus import stopwords
import textract
import PyPDF2
import os
import argparse
import re
from tika  import parser as tika_parser
import nltk
from nltk.corpus import stopwords
import ssl
import spacy
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context
nltk.download('stopwords')
nltk.download('universal_tagset')
spacy.download('en')
nltk.download('punkt')

import yake
from rake_nltk import Rake, Metric

#global variables
custom_list_stop_words = []
db_investors_by_topic = {}
db_keyword_by_topic = {}

def PrintHelp():
    print("Help")

def get_text_by_tika(filepath):
    raw = tika_parser.from_file(filepath)
    return(raw['content'])

def get_text_by_textract(filepath):
    resume_extract_text = textract.process(filepath, encoding='ascii')
    return(str(resume_extract_text.decode("ASCII")))

def extract_keywords_yake_pke(filename, text):
    text = re.sub('[^a-zA-Z0-9|^\-]', ' ', text)

    # Remove words with digits
    text = re.sub("\S*\d\S*", "", text).strip()

    # Remove empty hyphens
    text = re.sub(' - ', ' ', text)

    extractor = pke.unsupervised.YAKE()

    extractor.load_document(input=text,
                            language='en',
                            normalization=None)

    stoplist = stopwords.words('english')

    stoplist += custom_list_stop_words

    extractor.candidate_selection(n=2, stoplist=stoplist)

    window = 2
    use_stems = True # use stems instead of words for weighting
    extractor.candidate_weighting(window=window,
                              stoplist=stoplist,
                              use_stems=use_stems)

    threshold = 0.7
    keyphrases = extractor.get_n_best(n=20, threshold=threshold)
    return keyphrases
    for kw in keyphrases:
        print(kw)

def get_list_of_files_from_folder(input_folder):
    list_of_files = []
    for dirpath, _, filenames in os.walk(input_folder):
        for f in filenames:
            if f.endswith(".pdf") or f.endswith(".doc") or f.endswith(".docx") or f.endswith(".txt") or f.endswith(".csv"):
                list_of_files.append(os.path.abspath(os.path.join(dirpath, f)))

    return list_of_files

def getListOfStopWords(stopwords_dir):
    global custom_list_stop_words
    list_files = get_list_of_files_from_folder(stopwords_dir)
    if len(list_files) == 0:
        return

    for file_path in list_files:
        filename_w_ext = os.path.basename(file_path)

        file1 = open(file_path, 'r')
        lines = file1.readlines()

        for line in lines:
            custom_list_stop_words.append(line.strip().lower())

def SuggestInvestors(input_folder, stopwords_dir):
    global db_keyword_by_topic
    global db_investors_by_topic
    list_files = get_list_of_files_from_folder(input_folder)
    if len(list_files) == 0:
        print("No Files found in input folder " + input_folder + "\n Exiting program")
        PrintHelp()
        return

    getListOfStopWords(stopwords_dir)
    for file_path in list_files:
        filename_w_ext = os.path.basename(file_path)

        keywords = []
        if filename_w_ext.endswith(".pdf"):
            text = get_text_by_tika(file_path)
        else:
            text = get_text_by_textract(file_path)

        keywords = extract_keywords_yake_pke(filename_w_ext, text)

        keywords_score = {}

        for kw in keywords:
            keyword = str(kw[0])
            if (keyword in db_keyword_by_topic):
                if keyword not in keywords_score:
                    keywords_score[db_keyword_by_topic[keyword]] = 1
                else:
                    keywords_score[db_keyword_by_topic[keyword]] += 1

        reverse_sorted = sorted(keywords_score.items(), key=lambda x: (-x[1], x[0]))

        key_industry = list(reverse_sorted[0])

        print("Keywords for - " + filename_w_ext)
        print(keywords)
        print("Key Industry : " + key_industry[0])
        if (key_industry[0] in db_investors_by_topic):
            print ("Suggested Investors :")
            investors = db_investors_by_topic[key_industry[0]]
            print(investors)

        print("\n")
        continue

        print("\n" + filename_w_ext)
        for kw in keywords:
            print(str(kw[0]))

def buildDB(sectors_dir, investors_dir):
    global db_investors_by_topic
    global db_keyword_by_topic
    list_files_sectors = get_list_of_files_from_folder(sectors_dir)
    if len(list_files_sectors) == 0:
        print("No Files found in sector folder " + sectors_dir + "\n Exiting program")
        PrintHelp()
        return

    list_files_investors = get_list_of_files_from_folder(investors_dir)
    if len(list_files_investors) == 0:
        print("No Files found in investors folder " + investors_dir + "\n Exiting program")
        PrintHelp()
        return

    for file_path in list_files_sectors:
        filename_w_ext = os.path.basename(file_path)

        file1 = open(file_path, 'r')
        lines = file1.readlines()
        sector_name = os.path.splitext(filename_w_ext)
        for line in lines:
            db_keyword_by_topic[line.strip().lower()] = sector_name[0].strip()


    for file_path in list_files_sectors:
        filename_w_ext = os.path.basename(file_path)

        file1 = open(file_path, 'r')
        lines = file1.readlines()
        sector_name = os.path.splitext(filename_w_ext)[0].strip()
        for line in lines:
            db_keyword_by_topic[line.strip().lower()] = sector_name


    for file_path in list_files_investors:
        filename_w_ext = os.path.basename(file_path)

        file1 = open(file_path, 'r', encoding="utf-8", errors='ignore')
        lines = file1.readlines()
        sector_name = os.path.splitext(filename_w_ext)
        for line in lines:
            line = line.replace('"', '')
            split_test =  line.split(",")
            if (len(split_test) < 3):
                continue

            for i in range(len(split_test)):
                if i < 2 or len(split_test[0]) == 0:
                    continue
                else:
                    sector = split_test[i].lower().replace(" ", "")
                    if sector not in db_investors_by_topic:
                        db_investors_by_topic[sector] = [split_test[0]]
                    else:
                        db_investors_by_topic[sector].append(split_test[0].strip())

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument('--dir', dest='dir', required=False, help='<Required> path to folder containing resumes')
    arg_parser.add_argument('--stopwords-dir', dest='stopwords_dir', required=False, help='<Optional> Optional File path to folder containing files with to stopwords')

    arg_parser.add_argument('--sectors-dir', dest='sectors_dir', required=False,
                            help='<Required> File path to folder containing keywords by sector')
    arg_parser.add_argument('--investors-dir', dest='investors_dir', required=False,
                            help='<Required> File path to folder containing list of investors and the sectors they are interested in')

    arg_parser.add_argument("--print-help", dest='print_help', action='store_true')

    parsed_args = arg_parser.parse_args();

    if parsed_args.print_help:
        PrintHelp()
        exit()

    folder = parsed_args.dir
    if (str(folder) == ""):
        print("Usage : --dir argument empty")
        PrintHelp()

    stopwords_dir = parsed_args.stopwords_dir
    sectors_dir = parsed_args.sectors_dir
    investors_dir = parsed_args.investors_dir

    buildDB(sectors_dir, investors_dir)

    SuggestInvestors(folder, stopwords_dir)
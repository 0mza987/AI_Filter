import os
import glob
import json

from Bio import pairwise2

PUNCT = [',', '.', '?', ':', '!', ';']
DATA_FILE = [
    'updated_sample.json',
    'updated_overall.json'
]

def ans_equals_ref(ans, ref):
    ''' Incase reference has multiple answers '''
    LIST_ref = ref.split('@@')
    return True if ans in LIST_ref else False


def locate_prob(raw_text, text, prob):
    '''Align two text to get proper probabilities.

    Example: locate_prob('| faith.','faith',[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8])
        
        raw_text = '| faith.'   text = 'faith'

        prob:  [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8]   
        align1:  |       f   a   i   t   h   .
        align2:  -   -   f   a   i   t   h   -
        text_prob:     [0.3,0.4,0.5,0.6,0.7]           
    
    Note:   text must be a subsequence of raw_text
    '''    

    if raw_text=='' or text='': return []
    assert(len(prob) == len(raw_text))
    raw_text = raw_text.replace('-', '`')
    text = text.replace('-', '`')
    alignments = pairwise2.align.globalmx(raw_text, text, 2, -1)
    align1, align2, score, begin, end = alignments[-1]
    text_prob = [prob[index] for (index, item) in enumerate(align1) if align2[index]!='-']
    return text_prob

def check_pass_rate(fname=''):
    ''' return pass rate of the data file '''
    fname = DATA_FILE[0]
    fname = DATA_FILE[1]
    # fname = 'blank_data_sample.json'
    # fname = 'blank_data_overall.json'
    dataset = json.load(open('./dataset/{}'.format(fname)))
    pass_cnt_original = 0
    pass_cnt_new = 0
    for item in dataset:
        if item['marked'] == False:
            pass_cnt_original += 1
        if filter_condition(item):
            pass_cnt_new += 1

    print fname, len(dataset)
    print 'New rate: {}. Old rate: {}'.format(pass_cnt_new*1.0/len(dataset), pass_cnt_original*1.0/len(dataset))


def filter_condition(blank_data):
    ''' specific conditions to select blank data '''
    res = False
    if ans_equals_ref(blank_data['detectResult'], blank_data['reference']) \
        and blank_data['prob_val'] >= 0.5 :
        # and blank_data['prob_val'] < 0.9 \
        # and blank_data['detectResult'] != blank_data['manuallyResult']:
        res =True
    return res 


def filter():
    ''' filter data with certain conditions '''
    fname = DATA_FILE[1]
    dataset = json.load(open('./dataset/{}'.format(fname)))
    res = []
    for item in dataset:
        if filter_condition(item):
            res.append(item)
    print '{} out of {} items are left.'.format(len(res), len(dataset))
    json.dump(res, open('./dataset/residual_data.json', 'w'))


def discriminator(blank_data):
    '''
    Rules to judge if the blank data should pass ai filter automatically thus no need for human re-check.
    Input: blank_data dict
    Output: 1. FLAG_CORRECT: true if student's answer is right, vice versa.
            2. FLAG_CONFIDENT: true if no need for human re-check, vice versa.        
    '''
    FLAG_CORRECT    = False
    FLAG_CONFIDENT  = False
    
    text        = blank_data['detectResult']
    reference   = blank_data['reference']
    prob        = blank_data['prob']
    prob_avg    = blank_data['prob_val']

    # 1. 
    if ans_equals_ref(text, reference) and prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True
        return FLAG_CORRECT, FLAG_CONFIDENT


if __name__=='__main__':
    # check_pass_rate()
    filter()
    




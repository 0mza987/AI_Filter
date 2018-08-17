import os
import glob
import json


PUNCT = [',', '.', '?', ':', '!', ';']
DATA_FILE = [
    'updated_sample.json',
    'updated_overall.json'
]

def ans_equals_ref(ans, ref):
    ''' Incase reference has multiple answers '''
    LIST_ref = ref.split('@@')
    return True if ans in LIST_ref else False


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

    print fname
    print 'New rate: {}. Old rate: {}'.format(pass_cnt_new*1.0/len(dataset), pass_cnt_original*1.0/len(dataset))


def filter_condition(blank_data):
    ''' specific conditions to select blank data '''
    res = False
    if ans_equals_ref(blank_data['detectResult'], blank_data['reference']) \
        and blank_data['prob_val'] >= 0.5 \
        and blank_data['prob_val'] < 0.9 \
        and blank_data['detectResult'] != blank_data['manuallyResult']:
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
    FLAG_CORRECT = False
    FLAG_CONFIDENT = False
    
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




# -*-coding:utf-8-*-

import os
import glob
import json
import time
import random
import numpy as np

from Bio import pairwise2

PUNCT = [',', '.', '?', ':', '!', ';']
DATA_FILE = [
    'updated_sample.json',
    'updated_overall.json'
]

LIST_ALIAS = [
    sorted(['v','r']),
    sorted(['i','l'])
]

def ans_equals_ref(ans, ref):
    ''' Incase reference has multiple answers '''
    LIST_ref = ref.split('@@')
    return True if ans in LIST_ref else False


def locate_prob(raw_text, text, prob):
    '''Align two text to get proper probabilities.

    Example: locate_prob('| faith.','faith',[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8])
        
        raw_text = '| faith.'   text = 'fath'

        prob:  [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8]   
        align1:  |       f   a   i   t   h   .
        align2:  -   -   f   a   -   t   h   -
        text_prob:     [0.3,0.4    ,0.6,0.7]           
    
    Note:   text must be a subsequence of raw_text
    '''    

    if raw_text=='' or text=='': return []
    if len(prob) != len(raw_text): return []
    raw_text = raw_text.replace('-', '`')
    text = text.replace('-', '`')
    alignments = pairwise2.align.globalmx(raw_text, text, 2, -1)
    align1, align2, score, begin, end = alignments[-1]
    text_prob = [prob[index] for (index, item) in enumerate(align1[begin:end]) if align2[index]!='-']
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
        # if item['marked'] == False:
        if discriminator(item)[1] == True:
        # if filter_condition(item):
            pass_cnt_original += 1
        # elif filter_condition(item):

    print fname, len(dataset)
    print 'New rate: {}. Old rate: {}'.format(pass_cnt_new*1.0/len(dataset), pass_cnt_original*1.0/len(dataset))


def filter_condition(blank_data):
    ''' specific conditions to select blank data '''
    res = False

    raw_text    = blank_data['raw_text'].lower()        # 原始识别结果，包含删除符号，标点符号
    text        = blank_data['detectResult'].lower()    # 干净识别结果，只有字符与空格
    reference   = blank_data['reference'].lower()       # 标准答案
    prob        = blank_data['prob']                    # 对应原始识别结果的概率list
    prob_avg    = blank_data['prob_val']                # 概率list的平均值
    human_text  = blank_data['manuallyResult'].lower()  # 运营人员标注结果
    score       = blank_data['score']                   # 该题的得分值

    ref_size    = len(reference)
    ans_size    = len(text)
    # clean_prob  = locate_prob(raw_text, text, prob)

    # if ans_equals_ref(text, reference) and prob_avg >= 0.5:
    #     res =False
        
    # elif '@@' in reference:
    #     pass

    # elif raw_text == '' and ref_size>1:
    #     res = True

    # if raw_text == '|' and text == '':
    #     res = True

    # if (reference.isdigit() or ref_size==1)  and text=='' and score!=0:
    #     res =True
    # if min_distance(text, reference)==1 and ref_size>2 and ans_size==ref_size:
    #     for i in xrange(ref_size):
    #         if reference[i] != text[i]: 
    #             char_pair = sorted([reference[i], text[i]])
    #             if char_pair in LIST_ALIAS:
    #                 clean_prob = locate_prob(raw_text, text, prob)
    #                 # 注意这里可能返回空集合
    #                 if clean_prob != [] and clean_prob[i] > 0.9:
    #                     res = True


    # f = discriminator(blank_data)
    # if f[1]==True:
    #     if f[0]==True and score==0:
    #         res = True
    #     elif f[0]==False and score!=0:
    #         res=True
    if ''.join(text.split(' ')) == ''.join(reference.split(' ')) and score==0:
        res = True

    # if not reference.isdigit() and ref_size > 1 and '@@' not in reference:
    #     if min_distance(text, reference)>2 and ref_size>2 and score!=0:
    #         res = True
        # if text!=reference and score!=0:
        #     res = True
    

    # if reference=='':
    #     res =True
    return res 


def filter():
    ''' filter data with certain conditions '''
    fname = DATA_FILE[0]
    dataset = json.load(open('./dataset/{}'.format(fname)))
    res = []
    for item in dataset:
        if discriminator(item)[1]==False and filter_condition(item):
        # if filter_condition(item):
            res.append(item)
    print '{} out of {} items are left. Ratio: {}'.format(len(res), len(dataset), len(res)*1.0/len(dataset))
    json.dump(res, open('./dataset/residual_data.json', 'w'))


def min_distance(s1, s2):
    ''' calculate min edit distance of two words '''
    n = len(s1)
    m = len(s2)
    matrix = [([0]*(m+1)) for i in xrange(n+1)]
    for i in xrange(m+1):
        matrix[0][i] = i
    for i in xrange(n+1):
        matrix[i][0] = i
    for i in xrange(1,n+1):
        for j in xrange(1,m+1):
            temp = min(matrix[i-1][j]+1, matrix[i][j-1]+1)
            d = 0 if s1[i-1]==s2[j-1] else 1
            matrix[i][j] = min(temp, matrix[i-1][j-1]+d)
    return matrix[n][m]


def discriminator(blank_data):
    '''
    Rules to judge if the blank data should pass ai filter automatically thus no need for human re-check.
    Input: blank_data dict
    Output: 1. FLAG_CORRECT: true if student's answer is right, vice versa.
            2. FLAG_CONFIDENT: true if no need for human re-check, vice versa.        
    '''
    FLAG_CORRECT    = False
    FLAG_CONFIDENT  = False
    
    raw_text    = blank_data['raw_text'].lower()        # 原始识别结果，包含删除符号，标点符号
    text        = blank_data['detectResult'].lower()    # 干净识别结果，只有字符
    reference   = blank_data['reference'].lower()       # 标准答案
    prob        = blank_data['prob']                    # 对应原始识别结果的概率list
    prob_avg    = blank_data['prob_val']                # 概率list的平均值

    ref_size    = len(reference)
    ans_size    = len(text)

    # 1. 识别结果与答案相等，且识别概率在0.5以上
    if ans_equals_ref(text, reference) and prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True

    # 2. 识别结果为空，且答案长度大于1（模型对一两个字符的答案以及数字的识别效果不佳，易出现空白结果）
    elif raw_text == '' and ref_size>1:
        FLAG_CORRECT = False
        FLAG_CONFIDENT = True

    # 3. 原始识别结果为一个删除符号，最终结果为空，易出现情况：学生修改后的结果未被识别出。需要运营检查
    elif raw_text == '|' and text == '':
        FLAG_CORRECT = False
        FLAG_CONFIDENT = False

    # 4. 答案为单个字符以及数字的情况，单独处理
    elif reference.isdigit() or ref_size < 2:
        pass
    
    # 5. 多选题单独处理
    elif '@@' in reference:
        pass
    
    # 6. 识别结果后半部分包含标准答案时。很大可能是学生作答正确但识别多识别出了字符的情况，例如：
    #    {reference = 'ffice', text = 'o ffice'}, 模型将填空题首字母印刷体o也识别出来了
    elif ans_size >= ref_size and text[-ref_size:] == reference and ref_size>=(ans_size/2):
        # 若text前半部分为以下词汇，则判为错误 (e.g. {reference: 'know', text: 'to know'})
        watch_out = ['at','to','in','the','has','have','had','be','being','is','was','are','been']
        # 部分易混淆的特殊情况，可单独添加. {reference: 'other', text: 'another'}
        key_words = ['another', 'international']
        FLAG_CONFIDENT = True
        if text[0:-ref_size].strip().lower() not in watch_out and text not in key_words:
            FLAG_CORRECT = True
        else:
            FLAG_CORRECT = False

    # 7. 对于易混淆字符的处理。若学生作答与正确答案只差一个字符，该字符属于易错字符且识别概率低于0.9，判为正确答案
    #   {reference: 'move', text: 'more'}
    elif ref_size>2 and ans_size==ref_size and min_distance(text, reference)==1:
        for i in xrange(ref_size):
            if reference[i] != text[i]: 
                char_pair = sorted([reference[i], text[i]])
                if char_pair in LIST_ALIAS:
                    clean_prob = locate_prob(raw_text, text, prob)
                    # 注意这里可能返回空集合
                    if clean_prob != [] and clean_prob[i] <= 0.9:
                        FLAG_CORRECT = True
                        FLAG_CONFIDENT = True

    # 8. 识别结果中多出或者少了空格，大概率是正确答案
    elif ''.join(text.split(' ')) == ''.join(reference.split(' ')) and prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True

    return FLAG_CORRECT, FLAG_CONFIDENT


if __name__=='__main__':
    TIME_s = time.time()
    check_pass_rate()
    # filter()
    print 'Time cost: {} s'.format(time.time()-TIME_s)
    




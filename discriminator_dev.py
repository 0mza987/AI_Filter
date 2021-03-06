# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-08-15 15:23:49
# 
# Last Modified By: honglin
# Last Modified At: 2018-10-27 15:23:18
#======================================

import os
# os.environ['OMP_NUM_THREADS'] = '1'
import cv2
import glob
import json
import time
import random
import traceback
import numpy as np
import helper as H
import pandas as pd

from Bio import pairwise2
from data_gain import initialize_rpc, recognize, data_convert_image
from generate_feature import generate_feature
from sklearn.externals import joblib

PUNCT = [',', '.', '?', ':', '!', ';']
DATA_FILE = [
    'updated_sample.json',
    'updated_overall.json',
    'residual_data.json'
]

LIST_ALIAS = [
    sorted(['v','r']),
    sorted(['i','l'])
]

# load xgb classifier and run with only 1 thread
CLF = joblib.load('./models/xgb_clf.model')
CLF._Booster.set_param('nthread', 1)

def check_pass_rate(fname=''):
    ''' return pass rate of the data file '''
    fname = DATA_FILE[0]
    fname = DATA_FILE[1]
    dataset = json.load(open('./dataset/{}'.format(fname)))
    pass_cnt_new = 0
    for item in dataset:
        # if item['marked'] == False:
        if discriminator(item)['confident'] == True:
            pass_cnt_new += 1
        # elif filter_condition(item):

    print fname, len(dataset)
    print 'New rate: {}'.format(pass_cnt_new*1.0/len(dataset))


def filter():
    ''' filter data with certain conditions '''
    fname = DATA_FILE[0]
    dataset = json.load(open('./dataset/{}'.format(fname)))
    res = []
    for idx, item in enumerate(dataset):
        if idx%10000 == 0:
            print 'Processing {}/{}'.format(idx, len(dataset))
        ans = discriminator(item)
        if ans['step']=='199':
            res.append(item)
    print '{} out of {} items are left. Ratio: {}'.format(len(res), len(dataset), len(res)*1.0/len(dataset))
    json.dump(res, open('./dataset/residual_data.json', 'w'))


def recognize():
    ''' get new recognization results from OCR model '''
    en_predictor = initialize_rpc()
    dataset = json.load(open('./dataset/residual_data.json'))
    for item in dataset:
        fname = item['local_addr']
        try:
            result = recognize_single(en_predictor, fname)
            item['raw_text_1'] = result['raw_text']
            item['text_1'] = result['text']
            item['prob_1'] = result['prob']
            print 'Processing:', fname
        except:
            print traceback.format_exc()
    json.dump(dataset, open('./dataset/residual123_data.json', 'w'))
        

def discriminator(blank_data):
    """
    Rules to judge if the blank data should pass ai filter automatically
    thus no need for human re-check.

    Arguments:
        blank_data {dict} -- a dictionary including blank data info
    
    Returns:
        FLAG_CORRECT {bool} -- true if student's answer is right, vice versa
        FLAG_CONFIDENT {bool} -- true if no need for human re-check, vice versa
        step {str} -- help to locate which step the blank data went through  
    """

    # =============================================
    # 初始化数据
    # =============================================
    FLAG_CORRECT    = False
    FLAG_CONFIDENT  = False
    FLAG_test       = False
    prob = 0
    blank_inst = H.Blank(blank_data)

    # =============================================
    # 分步骤处理
    # =============================================

    # 1. 识别结果与答案相等，且识别概率在0.5以上
    if H.ans_equals_ref(blank_inst.text, blank_inst.reference) and blank_inst.prob_avg >= 0.6:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True
        blank_inst.step = '1'

    # 2. 答案为单个字符,数字或者长句子的情况，单独处理
    elif blank_inst.FLAG_DIGIT or blank_inst.FLAG_SHORT:
        blank_inst.step = '2'
        if blank_inst.prob_avg < 0.9:
            blank_inst.step = '102'

    # 3. 答案为长句子/词组的情况，单独处理
    elif blank_inst.ref_word_size > 3:
        # 如果识别结果为空，判为错误
        if blank_inst.raw_text == '' or blank_inst.text == '':
            FLAG_CORRECT = False
            FLAG_CONFIDENT = True
            blank_inst.step = '3'

    # 4. 识别结果为空，且答案长度大于1（模型对一两个字符的答案以及数字的识别效果不佳，易出现空白结果）
    elif blank_inst.raw_text == '' and blank_inst.ref_size > 1:
        is_blank, _, black_ratio = H.blank_img_check(blank_inst.url)
        # is_blank = True
        if is_blank:
            FLAG_CORRECT = False
            FLAG_CONFIDENT = True
            blank_inst.step = '4'
        elif black_ratio > 0.04:
            blank_inst.step = '104'             # 出现频率：0.0025

    # 5. 原始识别结果为一个删除符号，最终结果为空，易出现情况：学生修改后的结果未被识别出。需要运营检查
    elif blank_inst.raw_text == '|' and blank_inst.text == '':
        is_blank, _, black_ratio = H.blank_img_check(blank_inst.url)
        FLAG_CORRECT = False
        FLAG_CONFIDENT = False
        blank_inst.step = '5'
        if black_ratio < 0.02:
            blank_inst.step = '105'             # 出现频率：0.0105
    
    # 6. 多选题单独处理
    elif '@@' in blank_inst.reference:
        blank_inst.step = '6'
    
    # 7. 识别结果后半部分包含标准答案时。很大可能是学生作答正确但识别多识别出了字符的情况，例如：
    #    {reference = 'ffice', text = 'o ffice'}, 模型将填空题首字母印刷体o也识别出来了
    elif (blank_inst.ans_size >= blank_inst.ref_size and 
          blank_inst.text[-blank_inst.ref_size:] == blank_inst.reference and 
          blank_inst.ref_size >= (blank_inst.ans_size/2)):
        # 若text前半部分为以下词汇，则不进行机器判定(e.g. {reference: 'know', text: 'to know'})
        watch_out = ['at','to','in','the','has','have','had','be','being',
                     'is','was','are','been','im','more','less','un','tobe']
        # 部分易混淆的特殊情况，可单独添加. {reference: 'other', text: 'another'}
        key_words = ['other', 'national', 'cross']
        if (blank_inst.text[0:-blank_inst.ref_size].strip().lower() not in watch_out and 
            blank_inst.reference not in key_words):
            FLAG_CORRECT = True
            FLAG_CONFIDENT = True
            blank_inst.step = '7'

    # 8. 对于易混淆字符的处理。若学生作答与正确答案只差一个字符，该字符属于易错字符且识别概率低于0.9，判为正确答案
    #   {reference: 'move', text: 'more'}
    elif (blank_inst.ref_size>2 and 
          blank_inst.ans_size==blank_inst.ref_size and 
          H.min_distance(blank_inst.text, blank_inst.reference)==1):
        for i in xrange(blank_inst.ref_size):
            if blank_inst.reference[i] != blank_inst.text[i]: 
                char_pair = sorted([blank_inst.reference[i], blank_inst.text[i]])
                if char_pair in LIST_ALIAS:
                    clean_prob = H.locate_prob(blank_inst.raw_text, blank_inst.text, blank_inst.prob)
                    # 注意这里可能返回空集合
                    if clean_prob != [] and clean_prob[i] <= 0.9:
                        FLAG_CORRECT = True
                        FLAG_CONFIDENT = True
                        blank_inst.step = '8'
                else:
                    blank_inst.step = '108'

    # 9. 识别结果中多出或者少了空格，大概率是正确答案
    elif blank_inst.pure_ref == blank_inst.pure_text and blank_inst.prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True
        blank_inst.step = '9'
        
    # 10. 若此时答案单词数依然大于3，有可能为长句子题型，需要人工检查
    elif blank_inst.ans_word_size > 3:
        blank_inst.step = '10'

    # 11. 编辑距离大于2，且平均置信度高于0.95，判为错误
    elif (H.min_distance(blank_inst.pure_text, blank_inst.pure_ref) > 2 and 
          '|' not in blank_inst.raw_text and 
          blank_inst.prob_avg > 0.95 and
          H.lcs_length(blank_inst.pure_text, blank_inst.pure_ref) < 
          0.8 * min(blank_inst.pure_text_size, blank_inst.pure_ref_size)):
        FLAG_CORRECT = False
        FLAG_CONFIDENT = True
        blank_inst.step = '11'

    # 12,13 机器学习模型预测
    # if (FLAG_CONFIDENT == False and blank_inst.FLAG_MULTI == False and
    #     blank_inst.ref_word_size <=3 and blank_inst.ans_word_size <=3):
    #     res, prob = predict(blank_inst, CLF)
    #     if prob > 0.9:
    #         if res == 1:
    #             FLAG_CONFIDENT = True
    #             FLAG_CORRECT = True
    #             blank_inst.step = '12'
    #         elif res == 0:
    #             if ('|' not in blank_inst.raw_text and 
    #                 blank_inst.prob_avg > 0.9 and
    #                 blank_inst.pure_text not in blank_inst.pure_ref and 
    #                 blank_inst.pure_ref not in blank_inst.pure_text):
    #                 FLAG_CONFIDENT = True
    #                 FLAG_CORRECT = False
    #                 blank_inst.step = '13'

    if blank_inst.step == '0' and 0 < blank_inst.prob_avg < 0.7:
        blank_inst.step = '199'

    # 当判断为正确的时候给出suggested answer
    suggested = blank_inst.text
    if FLAG_CONFIDENT == True and FLAG_CORRECT == True and blank_inst.FLAG_MULTI == False:
        suggested = blank_inst.reference

    result = {
        'correct': FLAG_CORRECT,
        'confident': FLAG_CONFIDENT,
        'step': blank_inst.step,
        'test': FLAG_test,
        'weight': round(prob, 4),
        'suggested': suggested
    }
    return result


def predict(blank_inst, model=None):
    """
    Predict with specific model
    
    Arguments:
        blank_inst {object} -- an instance of class Blank
    
    Keyword Arguments:
        model {model} -- model as predictor (default: {None})
    
    Returns:
        int -- predicted class name
        float -- probability of the class
    """
    col_names = [
        'prob_avg', 'text_size', 'ref_size', 'text_word_size',
        'ref_word_size', 'flag_short', 'flag_digit', 
        'prob_0', 'prob_1', 'prob_2', 'prob_3', 'prob_4', 'prob_5', 'prob_6',
        'edit_distance', 'pure_edit_distance', 'nb_dele', 'nb_strip', 'flag_equal',
        'feature_0', 'feature_1', 'feature_2', 'feature_3',
        'feature_4', 'feature_5', 'feature_6', 'feature_7'
    ]
    features = generate_feature(blank_inst)
    features = pd.DataFrame([features, features], columns=col_names).iloc[0:1,:]
    pred = model.predict_proba(features)
    return pred.argmax(), pred.max()


def ml_test():
    # fname = DATA_FILE[0]
    fname = DATA_FILE[1]
    LIST_res = []
    dataset = json.load(open('./dataset/{}'.format(fname)))
    for item in dataset[0:100]:
        blank_inst = H.Blank(item)
        pred = predict(blank_inst, CLF)
        print pred.tolist()[0]
        LIST_res.append(pred.tolist()[0])
    print LIST_res
    df = pd.DataFrame(LIST_res, columns=CLF.classes_)
    print df
        

def exam_id_list():
    LIST_files = glob.glob(r'./dataset/blank_data/*.json')
    LIST_id = []
    for item in LIST_files:
        eid = os.path.basename(item)[0:-5]
        LIST_id.append(eid)
    json.dump(LIST_id, open('./dataset/exam_id.json', 'w'))


def rectify(fname):
    # fname = './dataset/updated_overall.json'
    dataset = json.load(open(fname))
    for item in dataset:
        result = discriminator(item)
        if result['step']=='1':
            item['score'] = item['totalScore']
    json.dump(dataset, open(fname, 'w'))


if __name__=='__main__':
    TIME_s = time.time()
    # check_pass_rate()
    filter()
    # rectify()
    # recogize()
    # ml_test()
    # exam_id_list()
    print 'Time cost: {} s'.format(time.time()-TIME_s)
    




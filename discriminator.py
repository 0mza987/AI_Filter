# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-09-10 17:08:11
# 
# Last Modified By: honglin
# Last Modified At: 2018-09-13 15:33:12
#======================================

import os
import cv2
import glob
import json
import time
import random
import requests
import traceback
import numpy as np
import helper as H

PUNCT = [',', '.', '?', ':', '!', ';']

LIST_ALIAS = [
    sorted(['v','r']),
    sorted(['i','l'])
]

def discriminator(blank_data):
    """
    Rules to judge if the blank data should pass ai filter automatically thus no need for human re-check.
    Input: blank_data dict
    Output: 1. FLAG_CORRECT: true if student's answer is right, vice versa.
            2. FLAG_CONFIDENT: true if no need for human re-check, vice versa.      
            3. step: help to locate which step the blank data went through  
    """

    # =============================================
    # 初始化数据
    # =============================================
    FLAG_CORRECT    = False
    FLAG_CONFIDENT  = False
    
    blank_inst = H.Blank(blank_data)

    # =============================================
    # 分步骤处理
    # =============================================

    # 1. 识别结果与答案相等，且识别概率在0.5以上
    if H.ans_equals_ref(blank_inst.text, blank_inst.reference) and blank_inst.prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True
        blank_inst.step = '1'

    # 2. 答案为单个字符,数字或者长句子的情况，单独处理
    elif blank_inst.FLAG_DIGIT or blank_inst.FLAG_SHORT or blank_inst.ref_word_size > 3:
        blank_inst.step = '2'

    # 3. 识别结果为空，且答案长度大于1（模型对一两个字符的答案以及数字的识别效果不佳，易出现空白结果）
    elif blank_inst.raw_text == '' and blank_inst.ref_size>1:
        is_blank = H.blank_img_check(blank_inst.url)[0]
        if is_blank:
            FLAG_CORRECT = False
            FLAG_CONFIDENT = True
            blank_inst.step = '3'

    # 4. 原始识别结果为一个删除符号，最终结果为空，易出现情况：学生修改后的结果未被识别出。需要运营检查
    elif blank_inst.raw_text == '|' and blank_inst.text == '':
        FLAG_CORRECT = False
        FLAG_CONFIDENT = False
        blank_inst.step = '4'
    
    # 5. 多选题单独处理
    elif '@@' in blank_inst.reference:
        blank_inst.step = '5'
    
    # 6. 识别结果后半部分包含标准答案时。很大可能是学生作答正确但识别多识别出了字符的情况，例如：
    #    {reference = 'ffice', text = 'o ffice'}, 模型将填空题首字母印刷体o也识别出来了
    elif (blank_inst.ans_size >= blank_inst.ref_size and 
          blank_inst.text[-blank_inst.ref_size:] == blank_inst.reference and 
          blank_inst.ref_size >= (blank_inst.ans_size/2)):
        # 若text前半部分为以下词汇，则不进行机器判定(e.g. {reference: 'know', text: 'to know'})
        watch_out = ['at','to','in','the','has','have','had','be',
                     'being','is','was','are','been','im','more','less','un']
        # 部分易混淆的特殊情况，可单独添加. {reference: 'other', text: 'another'}
        key_words = ['another', 'international']
        if (blank_inst.text[0:-blank_inst.ref_size].strip().lower() not in watch_out and 
            blank_inst.text not in key_words):
            FLAG_CORRECT = True
            FLAG_CONFIDENT = True
            blank_inst.step = '6'

    # 7. 对于易混淆字符的处理。若学生作答与正确答案只差一个字符，该字符属于易错字符且识别概率低于0.9，判为正确答案
    #   {reference: 'move', text: 'more'}
    elif (blank_inst.ref_size>2 and 
          blank_inst.ans_size==blank_inst.ref_size and 
          H.min_distance(blank_inst.text, blank_inst.reference)==1):
        for i in xrange(blank_inst.ref_size):
            if blank_inst.reference[i] != blank_inst.text[i]: 
                char_pair = sorted([blank_inst.reference[i], blank_inst.text[i]])
                if char_pair in LIST_ALIAS:
                    clean_prob = locate_prob(blank_inst.raw_text, blank_inst.text, blank_inst.prob)
                    # 注意这里可能返回空集合
                    if clean_prob != [] and clean_prob[i] <= 0.9:
                        FLAG_CORRECT = True
                        FLAG_CONFIDENT = True
                        blank_inst.step = '7'

    # 8. 识别结果中多出或者少了空格，大概率是正确答案
    elif blank_inst.pure_ref == blank_inst.pure_text and blank_inst.prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True
        blank_inst.step = '8'
        
    # 9. 若此时答案单词数依然大于3，有可能为长句子题型，需要人工检查
    elif blank_inst.ans_word_size > 3:
        blank_inst.step = '9'

    # 10. 编辑距离大于2，且平均置信度高于0.9，判为错误
    elif (H.min_distance(blank_inst.pure_text, blank_inst.pure_ref) > 2 and 
          '|' not in blank_inst.raw_text and 
          blank_inst.prob_avg > 0.9 and
          blank_inst.pure_text not in blank_inst.pure_ref and 
          blank_inst.pure_ref not in blank_inst.pure_text):
        FLAG_CORRECT = False
        FLAG_CONFIDENT = True
        blank_inst.step = '10'

    result = {
        'correct': FLAG_CORRECT,
        'confident': FLAG_CONFIDENT,
        'step': blank_inst.step
    }
    return result


def discriminator_old(blank_data):
    """ old discriminator version, for emergency rollback """
    # =============================================
    # 初始化数据
    # =============================================
    FLAG_CORRECT    = False
    FLAG_CONFIDENT  = False
    
    blank_inst = H.Blank(blank_data)

    # =============================================
    # 处理数据
    # =============================================
    if H.ans_equals_ref(blank_inst.text, blank_inst.reference) and blank_inst.prob_avg > 0.9:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True

    result = {
        'correct': FLAG_CORRECT,
        'confident': FLAG_CONFIDENT,
        'step': '0.5'
    }

    return result


if __name__=='__main__':
    TIME_s = time.time()
    H.check_pass_rate()
    # filter()
    # recogize()
    print 'Time cost: {} s'.format(time.time()-TIME_s)
    




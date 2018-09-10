# -*-coding:utf-8-*-

import os
import cv2
import glob
import json
import time
import random
import requests
import traceback
import numpy as np

from Bio import pairwise2

PUNCT = [',', '.', '?', ':', '!', ';']

LIST_ALIAS = [
    sorted(['v','r']),
    sorted(['i','l'])
]

def ans_equals_ref(ans, ref):
    """ Incase reference has multiple answers """
    LIST_ref = ref.split('@@')
    return True if ans in LIST_ref else False


def data_convert_image(data):
    """ 
    standard image read and load online version
    """
    if isinstance(data, basestring):
        if data.startswith(('http:', 'https:')):
            resp = requests.get(data).content
            image = np.asarray(bytearray(resp), dtype=np.uint8)
            image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
        elif data.endswith(('.jpg', '.png')):
            data = data.replace('\\', '/')
            image = cv2.imread(data, cv2.IMREAD_GRAYSCALE)
        else:
            image = np.asarray(bytearray(data), dtype=np.uint8)
            image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
    else:
        image = data
    return image


def locate_prob(raw_text, text, prob):
    """Align two text to get proper probabilities.

    Example: locate_prob('| faith.','fath', prob)
        
        raw_text = '| faith.'   text = 'fath'

        prob:  [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8]   
        align1:  |       f   a   i   t   h   .
        align2:  -   -   f   a   -   t   h   -
        text_prob:     [0.3,0.4,    0.6,0.7]           
    
    Note:   text must be a subsequence of raw_text
    """    

    if raw_text=='' or text=='': return []
    if len(prob) != len(raw_text): return []
    raw_text = raw_text.replace('-', '`')
    text = text.replace('-', '`')
    alignments = pairwise2.align.globalmx(raw_text, text, 2, -1)
    align1, align2, score, begin, end = alignments[-1]
    text_prob = [prob[index] for (index, item) in enumerate(align1[begin:end]) if align2[index]!='-']
    return text_prob


def min_distance(s1, s2):
    """ calculate min edit distance of two words """
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


def blank_img_check(url):
    """ check if the image is blank """
    img = data_convert_image(url)
    h, w = img.shape
    img = 255 - img[:, int(w*0.2):int(w*0.9)]
    img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    black_pixel_cnt = img.sum() / 255
    black_pixel_ratio = black_pixel_cnt * 1.0 / (h * w)
    FLAG_BLANK = True if black_pixel_ratio < 0.01 else False
    return FLAG_BLANK, black_pixel_cnt, black_pixel_ratio


        

class Blank(object):

    def __init__(self, blank_data):
        
        self.step        = '0'
        self.raw_text    = blank_data['raw_text'].lower()           # 原始识别结果，包含删除符号，标点符号
        self.text        = blank_data['detectResult'].lower()       # 干净识别结果，只有字符与空格
        self.reference   = blank_data['reference'].lower()          # 标准答案
        self.prob        = blank_data['prob']                       # 对应原始识别结果的概率list
        self.prob_avg    = blank_data['prob_val']                   # 概率list的平均值
        self.url         = blank_data['url']                        # 填空题图片地址

        # self.human_text  = blank_data['manuallyResult'].lower()     # 运营人员标注结果
        # self.score       = blank_data['score']                      # 该题的得分值
        
        self.ref_size       = len(self.reference)
        self.ans_size       = len(self.text)
        self.ref_word_size  = len(self.reference.split(' '))
        self.ans_word_size  = len(self.text.split(' '))

        # 针对多个答案的填空题
        LIST_ANS    = self.reference.split('@@')
        LIST_SIZE   = [len(ans) for ans in LIST_ANS if len(ans)<2]
        LIST_NB     = [ans for ans in LIST_ANS if ans.isdigit()]

        self.FLAG_SHORT  = True if LIST_SIZE!=[] else False
        self.FLAG_DIGIT  = True if LIST_NB!=[] else False

        # generate pure text and reference
        LIST_toclean = [' ', '.', '-', '?', '!', ',', ':']
        pure_text   = self.text
        pure_ref    = self.reference
        for item in LIST_toclean:
            pure_text   = pure_text.replace(item, '')
            pure_ref    = pure_ref.replace(item, '')
        self.pure_text  = pure_text
        self.pure_ref   = pure_ref


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
    
    blank_inst = Blank(blank_data)

    # =============================================
    # 分步骤处理
    # =============================================

    # 1. 识别结果与答案相等，且识别概率在0.5以上
    if ans_equals_ref(blank_inst.text, blank_inst.reference) and blank_inst.prob_avg >= 0.5:
        FLAG_CORRECT = True
        FLAG_CONFIDENT = True
        blank_inst.step = '1'

    # 2. 答案为单个字符,数字或者长句子的情况，单独处理
    elif blank_inst.FLAG_DIGIT or blank_inst.FLAG_SHORT or blank_inst.ref_word_size > 3:
        blank_inst.step = '2'

    # 3. 识别结果为空，且答案长度大于1（模型对一两个字符的答案以及数字的识别效果不佳，易出现空白结果）
    elif blank_inst.raw_text == '' and blank_inst.ref_size>1:
        is_blank = blank_img_check(blank_inst.url)[0]
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
        if blank_inst.text[0:-blank_inst.ref_size].strip().lower() not in watch_out and blank_inst.text not in key_words:
            FLAG_CORRECT = True
            FLAG_CONFIDENT = True
            blank_inst.step = '6'

    # 7. 对于易混淆字符的处理。若学生作答与正确答案只差一个字符，该字符属于易错字符且识别概率低于0.9，判为正确答案
    #   {reference: 'move', text: 'more'}
    elif blank_inst.ref_size > 2 and blank_inst.ans_size == blank_inst.ref_size and min_distance(blank_inst.text, blank_inst.reference)==1:
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
    elif (min_distance(blank_inst.pure_text, blank_inst.pure_ref) > 2 and 
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
    
    blank_inst = Blank(blank_data)

    # =============================================
    # 处理数据
    # =============================================
    if ans_equals_ref(blank_inst.text, blank_inst.reference) and blank_inst.prob_avg > 0.9:
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
    check_pass_rate()
    # filter()
    # recogize()
    print 'Time cost: {} s'.format(time.time()-TIME_s)
    




# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-09-12 16:51:26
# 
# Last Modified By: honglin
# Last Modified At: 2018-09-28 14:31:12
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

from Bio import pairwise2

def ans_equals_ref(ans, ref):
    """ Incase reference has multiple answers """
    LIST_ref = ref.split('@@')
    return True if ans in LIST_ref else False


def data_convert_image(data):
    """ standard image read and load online version """
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
    """
    Align two text to get proper probabilities.

    Example: locate_prob('| faith.','fath', prob)

        raw_text = '| faith.'   text = 'fath'

        prob:  [0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8]   
        align1:  |       f   a   i   t   h   .
        align2:  -   -   f   a   -   t   h   -
        text_prob:     [0.3,0.4,    0.6,0.7]           
    
    Note: 
        text must be a subsequence of raw_text
    
    Arguments:
        raw_text {str} -- raw text of ocr results
        text {str} -- clean text of ocr results
        prob {list} -- [description]
    
    Returns:
        text_prob {list} -- a sub-list of original raw text prob list
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
    """ check if the image is blank through image """
    img = data_convert_image(url)
    h, w = img.shape
    img = 255 - img[:, int(w*0.2):int(w*0.9)]
    img = cv2.threshold(img, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
    black_pixel_cnt = img.sum() / 255
    black_pixel_ratio = black_pixel_cnt * 1.0 / (h * w)
    FLAG_BLANK = True if black_pixel_ratio < 0.01 else False
    return FLAG_BLANK, black_pixel_cnt, black_pixel_ratio



class Blank(object):
    """
    Abstract a blank data structure to a class
    """

    def __init__(self, blank_data, valid=False):
        """
        Initialize a blank data object through a blank data dictionary
        
        Arguments:
            blank_data {dict} -- blank data dictionary
            valid {bool} -- data has already been scored
        """
        self.step       = '0'
        self.raw_text   = blank_data['raw_text'].lower()        # 原始识别结果，包含删除符号，标点符号
        self.text       = blank_data['detectResult'].lower()    # 干净识别结果，只有字符与空格
        self.reference  = blank_data['reference'].lower()       # 标准答案
        self.prob       = blank_data['prob']                    # 对应原始识别结果的概率list
        self.prob_avg   = blank_data['prob_val']                # 概率list的平均值
        self.url        = blank_data['url']                     # 填空题图片地址   

        if valid:
            self.marked     = blank_data['marked']                     # 是否被人工check过    
            self.human_text = blank_data['manuallyResult'].lower()     # 运营人员标注结果
            self.score      = blank_data['score']                      # 该题的得分值
        
        self.ref_size       = len(self.reference)
        self.ans_size       = len(self.text)
        self.raw_size       = len(self.raw_text)
        self.text_size      = len(self.text)
        self.ref_word_size  = len(self.reference.split(' '))
        self.ans_word_size  = len(self.text.split(' '))

        # 针对多个答案的填空题
        LIST_ANS    = self.reference.split('@@')
        LIST_SIZE   = [len(ans) for ans in LIST_ANS if len(ans)<2]
        LIST_NB     = [ans for ans in LIST_ANS if ans.isdigit()]

        self.FLAG_SHORT  = True if LIST_SIZE!=[] else False
        self.FLAG_DIGIT  = True if LIST_NB!=[] else False
        self.FLAG_MULTI  = True if '@@' in self.reference else False

        # generate pure text and reference
        LIST_toclean = [' ', '.', '-', '?', '!', ',', ':']
        pure_text   = self.text
        pure_ref    = self.reference
        for item in LIST_toclean:
            pure_text   = pure_text.replace(item, '')
            pure_ref    = pure_ref.replace(item, '')
        self.pure_text  = pure_text
        self.pure_ref   = pure_ref


if __name__ == '__main__':
    print 'Note: This is a helper file that is not supposed to be called directly.'


# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-09-13 10:13:09
# 
# Last Modified By: honglin
# Last Modified At: 2018-09-13 16:11:40
#======================================

import os
import numpy as np
import helper as H


def get_basic_info(blank_inst):
    """
    Get basic info from blank_inst
    
    Arguments:
        blank_inst {object} -- an instance of class Blank
    
    Returns:
        basic_info {list} -- a list of features
    """
    basic_info = [
        blank_inst.prob_avg,
        blank_inst.text_size,
        blank_inst.ref_size,
        blank_inst.text_word_size,
        blank_inst.ref_word_size,
        int(blank_inst.FLAG_SHORT),
        int(blank_inst.FLAG_DIGIT)
    ]
    return basic_info


def get_prob_info(blank_inst):
    """
    Get probability info

    Arguments:
        blank_inst {object} -- an instance of class Blank

    Returns:
        prob_info {list} -- a list of features
    """
    prob = H.locate_prob(blank_inst.raw_text, blank_inst.text, blank_inst.prob)
    prob = np.array(prob)

    prob_info = [
        prob[prob<=0.5].size,
        prob[(prob>0.5) & (prob<=0.6)].size,
        prob[(prob>0.6) & (prob<=0.7)].size,
        prob[(prob>0.7) & (prob<=0.8)].size,
        prob[(prob>0.8) & (prob<=0.9)].size,
        prob[(prob>0.9) & (prob<=0.95)].size,
        prob[prob>0.95].size
    ]
    return prob_info
    

def get_advanced_info(blank_inst):
    """
    Get advanced info

    Arguments:
        blank_inst {object} -- an instance of class Blank

    Returns:
        advanced_info {list} -- a list of features
    """
    advanced_info = [
        H.min_distance(blank_inst.reference, blank_inst.text),
        H.min_distance(blank_inst.pure_ref, blank_inst.pure_text),
        blank_inst.raw_text.count('|'),
        blank_inst.raw_size - blank_inst.text_size,
        int(blank_inst.text==blank_inst.reference)
    ]
    return advanced_info


def get_other_info(blank_inst):
    """
    Get other info
    
    Arguments:
        blank_inst {object} -- an instance of class Blank
    
    Returns:
        other_info {list} -- a list of features
    """
    other_info = [
        int(blank_inst.raw_text=='' and blank_inst.ref_size>1),
        int(blank_inst.text[-blank_inst.ref_size:] == blank_inst.reference),
        int(blank_inst.ref_size>=(blank_inst.ans_size/2)),
        int(blank_inst.reference in blank_inst.text),
        int(blank_inst.pure_ref==blank_inst.pure_text),
        int(blank_inst.pure_ref in blank_inst.pure_text),
        int(blank_inst.pure_text in blank_inst.pure_ref),
        int(blank_inst.prob_avg>0.5)
    ]
    return other_info, len(other_info)


def feature_generator(blank_inst):
    """
    Generate multiple features from blank_inst:
        basic:
            prob_avg，OCR识别结果的平均概率值
            text_size， OCR识别结果的字符长度
            ref_size，标准答案的字符长度
            text_word_size，干净识别结果的词语长度
            ref_word_size，标准答案的词语长度
            flag_short，答案是否为单个字符
            flag_digit，答案是否为数字

        prob:
            prob， 干净字符识别概率值: 小于0.5， 0.5-0.9每0.1一档，0.9-0.95， 0.95-1.00 共7维
            
        advanced:
            edit_distance，标准答案与干净识别结果的编辑距离
            pure_edit_distance，pure_text 与 pure_ref的最小编辑距离
            nb_dele，raw_text中的删除符号 “|” 的个数
            nb_strip，raw_text字符长度减去text_size
            flag_equal，答案是否等于干净识别结果

        other:
            feature_0，判断raw_text=="" and ref_size > 1
            feature_1，判断text[-ref_size:] == reference
            feature_2，判断ref_size >= (ans_size/2)
            feature_3，判断reference in text
            feature_4，判断pure_ref == pure_text
            feature_5，判断pure_ref in pure_text
            feature_6，判断pure_text in pure_ref
            feature_7，判断prob_avg > 0.5

    Arguments:
        blank_inst {object} -- an instance of class Blank
    
    Returns:
        features {list} -- a list of features
    """
    assert isinstance(blank_inst, H.Blank)
    features = []
    features += get_basic_info(blank_inst)
    features += get_prob_info(blank_inst)
    features += get_advanced_info(blank_inst)
    features += get_other_info(blank_inst)
    return features














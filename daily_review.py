# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-10-26 17:16:54
# 
# Last Modified By: honglin
# Last Modified At: 2018-10-27 15:45:40
#======================================

import os
import json
import time
import datetime

import data_gain as D

REVIEW_DIR = './dataset/daily_review'
if not os.path.exists(REVIEW_DIR): os.makedirs(REVIEW_DIR)


def download():
    eid = '3e3c71388e'
    exam_data = D.get_data_by_exam(eid)
    json.dump(exam_data, open('{}/{}.json'.format(D.DATA_PATH, eid), 'w'))

def review():
    """
    Review everyday's blank data and do the math.
    Introductions:
        '9'     : 识别结果中多出或少了空格
        '102'   : 识别结果为数字或者单个字符
        '104'   : 识别结果为空，但图片不为空
        '105'   : 识别结果为删除符号，但图片为空
        '108'   : 识别结果与标准答案相差一个字符
        '199'   : 其他，且平均识别概率低于阈值
    """
    # Prepare the data
    LIST_eid = []
    res = {
        # 'step': [amount, ratio]
        '9': [0, 0],
        '102': [0, 0],
        '104': [0, 0],
        '105': [0, 0],
        '108': [0, 0],
        '199': [0, 0],
    }

    # Create exam data
    for eid in LIST_eid:
        D.create_exam(eid)

    # Pull exam data from data center
    exam_data = []
    for eid in LIST_eid:
        exam_data += D.get_data_by_exam(eid)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    json.dump(exam_data, open('./dataset/daily_review/{}_blank.json'.format(today), 'w'))
    
    # Count for all situations
    total = len(exam_data)
    for blank in exam_data:
        aif_data = json.loads(blank['data'])['blocks'][0]['words']['ai_filter']
        step = aif_data['step']
        if step in res:
            res[step][0] += 1
            res[step][1] = res[step][0] * 1.0 / total
    
    for key in res:
        print '{}: {}'.format(key, res[key])


if __name__ == '__main__':
    review()
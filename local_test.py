# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-09-08 15:29:50
# 
# Last Modified By: honglin
# Last Modified At: 2018-09-28 14:40:41
#======================================

import os
import json
import zerorpc

def client_test():
    dataset = json.load(open('./dataset/updated_sample.json'))
    blank_client = zerorpc.Client(heartbeat=None, timeout=30)
    blank_client.connect('tcp://192.168.1.57:21000')

    cnt = 0
    right_cnt = 0
    for idx, item in enumerate(dataset[0:100]):
        print 'Processing {}/{}'.format(idx+1, len(dataset))
        result = blank_client.discriminate(item)['data']
        is_right = False
        if result['confident'] == True:
            cnt += 1
            if result['correct'] == True and item['score']!=0:
                is_right = True
            elif result['correct'] == False and item['score']==0:
                is_right = True
            if is_right: right_cnt += 1
        print result
    print 'Ratio: {}'.format(right_cnt * 1.0 / cnt)


def custom_test():
    """
    local test with customized parameters
    """
    # 自定义数据
    reference = 'will suggest'
    text = 'suggested suggest'
    raw_text = text
    prob = [0.8] * len(raw_text)
    prob_val = sum(prob) / len(prob)

    blank_data = {
        'reference': reference,
        'detectResult': text,
        'raw_text': raw_text,
        'prob': prob,
        'prob_val': prob_val,
    }
    # 调用本地RPC服务
    blank_client = zerorpc.Client(heartbeat=None, timeout=30)
    blank_client.connect('tcp://192.168.1.57:21000')

    result = blank_client.discriminate(blank_data)['data']
    print '''
    Reference: "{}"
    Text: "{}"
    Raw text: "{}"
    Confident: "{}"
    Correct: "{}"
    Step: "{}"'''.format(reference,text,raw_text,result['confident'],result['correct'],result['step'])

if __name__ == '__main__':
    # client_test()
    custom_test()
# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-08-13 10:41:06
# 
# Last Modified By: honglin
# Last Modified At: 2018-09-19 15:35:35
#======================================

import os
import re
import sys 
import cv2
import glob
import json
import shutil
import random
import base64
import zerorpc
import requests
import traceback
import numpy as np


IMAGE_PATH  = './dataset/blank_image'
DATA_PATH   = './dataset/blank_data' 
if not os.path.exists(IMAGE_PATH): os.makedirs(IMAGE_PATH)
if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)


def _str_to_img_base64(str_image, FLAG_color=False):
    """ convert base64 string to image """
    FLAG_decode = cv2.IMREAD_COLOR if FLAG_color else cv2.IMREAD_GRAYSCALE
    img_encoded = np.frombuffer(base64.b64decode(str_image), dtype=np.uint8)
    img = cv2.imdecode(img_encoded, FLAG_decode)
    return img


def _img_to_str_base64(image):
    """ convert image to base64 string """
    img_encode = cv2.imencode('.jpg', image)[1]
    img_base64 = base64.b64encode(img_encode)
    return img_base64


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


def ans_equals_ref(ans, ref):
    """ Incase reference has multiple answers """
    LIST_ref = ref.split('@@')
    return True if ans in LIST_ref else False


def initialize_rpc():
    c_en_predict = zerorpc.Client(heartbeat=None, timeout=240)
    c_en_predict.connect('tcp://192.168.1.115:12001')
    return c_en_predict


def recognize_single(c_en_predict, fname):
    image_inst = {
        'img_str': _img_to_str_base64(data_convert_image(fname)), 
        'fname': os.path.basename(fname)
        }
    resp = c_en_predict.predict_image([image_inst], 'blank')
    result = json.loads(resp['data']).values()[0]
    return result


def recognition_all():
    """ Re-recognize all images and update results """
    # RPC client
    c_en_predict = initialize_rpc()

    updated_data = []
    overall_data = json.load(open('./dataset/blank_data_overall.json'))
    for index, item in enumerate(overall_data[0:]):
        if item['local_addr'].split('/')[-2] == '6b262f90ea': continue # invalid exam id
        if index % 1000 == 0: print 'Processing {} / {}'.format(index, len(overall_data))
        fname = item['local_addr']
        try:
            result = recognize_single(c_en_predict, fname)
            # update recognition result for local data
            item['prob'] = result['prob']
            item['prob_val'] = result['prob_val']
            item['raw_text'] = result['raw_text']
            item['detectResult'] = result['text'].strip()
            # re-generate the original 'marked' result
            if ans_equals_ref(item['detectResult'],item['reference']) and item['prob_val'] > 0.9:
                item['marked'] = False
            else:
                item['marked'] = True
            updated_data.append(item)
        except:
            print traceback.format_exc()
            print 'Recognition failed. Index: {}'.format(index+1)
    json.dump(updated_data, open('./dataset/updated_overall.json', 'w'))
    print 'Original: {}. New: {}.'.format(len(overall_data), len(updated_data))
    random.shuffle(updated_data)
    json.dump(updated_data[0:10000], open('./dataset/updated_sample.json', 'w'))


def get_data_by_exam(eid):
    """ get data from data center """
    URL = 'http://dcs.hexin.im/api/blank/getList'
    page = 1
    params = {
        'exerciseUid': eid,
        'page': page,
        'pageSize': 5000
    }
    res = requests.get(URL, params=params)
    exam_data = res.json()['data']
    
    for item in exam_data:
        # re-generate the original 'marked' result
        if ans_equals_ref(item['detectResult'],item['reference']) and item['prob'] > 0.9:
            item['marked'] = False
        else:
            item['marked'] = True
        # get source image from url
        item['local_addr'] = get_and_save_blank_image(item)
        
    return exam_data


def get_image_from_115(url):
    """ get image from 115 and crop region of interest """
    x, y, w, h = map(int, re.findall(r'x_(\d+),y_(\d+),w_(\d+),h_(\d+)', url)[0])
    exam_id = url.split('/')[-4]
    pic_name = url.split('/')[-3].split('?')[0]
    URL = 'http://192.168.1.115/dcs/{}/{}'.format(exam_id, pic_name)
    resp = requests.get(URL).content
    image = np.array(bytearray(resp), dtype=np.uint8)
    image = cv2.imdecode(image, cv2.IMREAD_GRAYSCALE)
    image = image[y:y+h, x:x+w]
    return image


def get_and_save_blank_image(blank_data):
    """ download blank image to local and return local address """
    fname = '{}_{}.png'.format(blank_data['originUid'], blank_data['_id'])
    exam_id = blank_data['url'].split('/')[-4]
    fpath = os.path.join(IMAGE_PATH, exam_id)
    if not os.path.exists(fpath):
        os.makedirs(fpath)
    if not os.path.isfile(os.path.join(fpath, fname)):
        img = get_image_from_115(blank_data['url'])
        cv2.imwrite(os.path.join(fpath, fname), img)
    return os.path.abspath(os.path.join(fpath, fname))


def get_blank_from_dc():
    """ 
    pull data from data center, save data by exam id and overall data as well
    select a portion of overall data as sample data.
    """
    overall_data = []
    LIST_failed = []
    LIST_eid = json.load(open('./dataset/list_eid.json'))
    for idx, eid in enumerate(LIST_eid):
        print 'Processing: {}, {}/{}'.format(eid, idx+1, len(LIST_eid))
        try:
            exam_data = get_data_by_exam(eid)
            json.dump(exam_data, open('{}/{}.json'.format(DATA_PATH, eid), 'w'))
            overall_data += exam_data
        except:
            LIST_failed.append(eid)
            print traceback.format_exc()
    json.dump(overall_data, open('./dataset/blank_data_overall.json', 'w'))

    random.shuffle(overall_data)
    sample_data = overall_data[0:10000]
    json.dump(sample_data, open('./dataset/blank_data_sample.json', 'w'))
    print '{} exams failed: {}'.format(len(LIST_failed), LIST_failed)
             

def check_file():
    LIST_exam_file = glob.glob(r'./dataset/blank_data/*.json')
    LIST_res = []
    for file in LIST_exam_file:
        exam_data = json.load(open(file))
        for item in exam_data:
            if not os.path.exists(item['local_addr']) and file not in LIST_res:
                print file
                LIST_res.append(file)

    overall = json.load(open('./dataset/blank_data_overall.json'))
    print 'Blank overall count:', len(overall)
    


if __name__ == '__main__':
    # get_blank_from_dc()
    recognition()
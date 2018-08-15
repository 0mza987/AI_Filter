import os
import re
import sys 
import cv2
import glob
import json
import shutil
import random
import requests
import traceback

import numpy as np

IMAGE_PATH  = './dataset/blank_image'
DATA_PATH   = './dataset/blank_data' 
if not os.path.exists(IMAGE_PATH): os.makedirs(IMAGE_PATH)
if not os.path.exists(DATA_PATH): os.makedirs(DATA_PATH)


def get_data_by_exam(eid):
    '''get data from data center'''
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
        if item['detectResult'] == item['reference'] and item['prob'] > 0.9:
            item['marked'] = False
        else:
            item['marked'] = True
        # get source image from url
        item['local_addr'] = get_and_save_blank_image(item)
        
    return exam_data


def get_image_from_115(url):
    '''get image from 115 and crop region of interest'''
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
    '''download blank image to local and return local address'''
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
    check_file()
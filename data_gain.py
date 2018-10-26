# -*- coding:utf-8 -*-
#======================================
# Author: honglin
# Date:   2018-08-13 10:41:06
# 
# Last Modified By: honglin
# Last Modified At: 2018-10-26 17:07:32
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

from multiprocessing import Process, Pool, Queue

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


def initialize_rpc(idx):
    """
    Initialize the rpc client with specific idx
    
    Arguments:
        idx {int} -- remote server port index
    
    Returns:
        c_en_predict {obj} -- a client instance
    """
    c_en_predict = zerorpc.Client(heartbeat=None, timeout=240)
    c_en_predict.connect('tcp://192.168.1.115:1200{}'.format(idx))
    return c_en_predict


def recognize(c_en_predict, fname):
    """
    Method to recognize an image with rpc client
    
    Arguments:
        c_en_predict {obj} -- an instance of rpc client
        fname {string} -- file name
    
    Returns:
        result {dict} -- dict data
    """
    image_inst = {
        'img_str': _img_to_str_base64(data_convert_image(fname)), 
        'fname': os.path.basename(fname)
        }
    resp = c_en_predict.predict_image([image_inst], 'blank')
    result = json.loads(resp['data']).values()[0]
    return result


def recognition_mp():
    """
    Multiprocessing method to recognize image data
    """
    LIST_exam_files = glob.glob(r'./dataset/blank_data/*.json')
    overall_data = []
    p = Pool(5)
    res = p.map(recognition_single, LIST_exam_files)
    p.close()
    p.join()
    for item in res:
        overall_data += item
    json.dump(overall_data, open('./dataset/updated_overall.json', 'w'))
    random.shuffle(overall_data)
    json.dump(overall_data[0:10000], open('./dataset/updated_sample.json', 'w'))

# Multiprocessing queue
valid_idx = Queue()
for i in range(1,6):
    valid_idx.put(i)


def recognition_single(exam_file):
    """
    Recognize a specific exam's images and update results
    
    Arguments:
        exam_file {string} -- file path
    
    Returns:
        updated_data {dict} -- recognized results
    """
    updated_data = []
    exam_data = json.load(open(exam_file))
    # global valid_idx
    # if(len(valid_idx)!=0):
    #     rpc_index = valid_idx.pop()
    rpc_index = valid_idx.get()
    c_en_predict = initialize_rpc(rpc_index)
    print 'Processing: {}. Port index 1200{}'.format(os.path.basename(exam_file), rpc_index)
    for index, item in enumerate(exam_data[0:]):
        # if index % 1000 == 0: print '{}: {} / {}'.format(os.path.basename(exam_file), index, len(exam_data))
        fname = item['local_addr']
        try:
            result = recognize(c_en_predict, fname)
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
            print 'Recognition of {} failed. Index: {}'.format(exam_file, index+1)
    print '###### Completed: {}. Filtered amount: {}.'.format(os.path.basename(exam_file),
                                                              len(exam_data)-len(updated_data))
    json.dump(updated_data, open(exam_file, 'w'))
    valid_idx.put(rpc_index)
    return updated_data



def get_data_by_exam(eid, Sampling=False):
    """
    get data from data center
    
    Arguments:
        eid {string} -- exam id
        Sampling {bool} -- if true, only get the first page's data, false for all pages

    Returns:
        exam_data {dict} -- exam data
    """
    URL = 'http://dcs.hexin.im/api/blank/getList'
    page = 1
    FLAG_continue = True
    exam_data = []
    while(FLAG_continue):
        params = {
            'exerciseUid': eid,
            'page': page,
            'pageSize': 5000
        }
        res = requests.get(URL, params=params)
        while(res.status_code!=200):
            print 'Retrying...'
            res = requests.get(URL, params=params)
        page_data = res.json()['data']
        if Sampling == True or len(page_data)==0:
            FLAG_continue = False
        exam_data += page_data
        page += 1

    print '{} amount: {}'.format(eid, len(exam_data))
    for item in exam_data:
        # get source image from url
        # item['local_addr'] = get_and_save_blank_image(item)
        item['text'] = item['detectResult']
        del item['detectResult']
        
    return exam_data


def get_image_from_115(url):
    """ get image from 115 and crop region of interest """
    x, y, w, h = map(int, re.findall(r'x_(\d+),y_(\d+),w_(\d+),h_(\d+)', url)[0])
    exam_id = url.split('/')[-4]
    pic_name = url.split('/')[-3].split('?')[0]
    URL = 'http://192.168.1.115/dcs/{}/{}'.format(exam_id, pic_name)
    resp = requests.get(URL)
    while(resp.status_code!=200):
        print 'Retry to get image {}'.format(pic_name)
        resp = requests.get(URL)
    resp = resp.content
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
        # img = get_image_from_115(blank_data['url'])
        img = data_convert_image(blank_data['url'])
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
    # LIST_eid = ['1ea17ebad4']
    for idx, eid in enumerate(LIST_eid[0:]):
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
    

def create_exam(eid):
    """
    Create new exam data through eid
    
    Arguments:
        eid {string} -- exercise id
    """
    URL = 'http://dcs.hexin.im/api/exercise/create'
    # URL = 'http://192.168.0.126:8005/api/exercise/create'
    datas = {'exerciseUid':eid}
    res = requests.post(URL, data=datas)
    print 'response code: {}'.format(res.status_code)
    while(res.status_code!=200):
        print 'Retrying...'
        res = requests.post(URL, data=datas)
    resp = res.json()
    print 'status: {}'.format(resp['status'])
    print 'statusInfo: {}'.format(resp['statusInfo'])


def create_wrapper():
    """
    Wrapper of create_exam, create multiple exam data
    """
    LIST_eid = json.load(open('./dataset/list_eid.json'))
    offset = 0
    for idx, eid in enumerate(LIST_eid[offset:]):
        print '############# {}: {}/{} #############'.format(eid, idx+offset+1, len(LIST_eid))
        create_exam(eid)
    

def generate_new_list():
    """
    Generate new eid list according to local files
    """
    LIST_files = glob.glob(r'./dataset/blank_data/*.json')
    LIST_eid = []
    for item in LIST_files:
        LIST_eid.append(os.path.basename(item)[0:-5])
    json.dump(LIST_eid, open('./dataset/new_list.json', 'w'))


def download_online_images_single(efile):
    """
    Grab online images single job
    
    Arguments:
        efile {string} -- json file path
    """
    eid = os.path.basename(efile)[0:-5]
    print 'Processing: {}'.format(eid)
    exam_data = json.load(open(efile))
    for blank_data in exam_data:
        blank_data['local_addr'] = get_and_save_blank_image(blank_data)
    json.dump(exam_data, open(efile, 'w'))
    return exam_data


def download_online_images_mp():
    """
    Grab online images by multiprocessing
    """
    LIST_files = glob.glob(r'./dataset/blank_data/*.json')
    overall_data = []
    LIST_eid = []
    
    p = Pool(12)
    res = p.map(download_online_images_single, LIST_files)
    p.close()
    p.join()

    for item in res:
        overall_data += item
    json.dump(overall_data, open('./dataset/blank_data_overall.json', 'w'))
    random.shuffle(overall_data)
    sample_data = overall_data[0:10000]
    json.dump(sample_data, open('./dataset/blank_data_sample.json', 'w'))



if __name__ == '__main__':
    # get_blank_from_dc()
    # recognition()
    # create_wrapper()
    # generate_new_list()
    # download_online_images_mp()
    recognition_mp()
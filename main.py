import os
import sys 
import cv2
import glob
import json
import shutil
import requests
import numpy as np

IMAGE_PATH = './dataset/blank_image/'
if not os.path.exists(IMAGE_PATH): os.makedirs(IMAGE_PATH)


def get_blank_from_dc(eid=''):
    '''get data from data center'''
    URL = 'http://dcs.hexin.im/api/blank/getList'
    page = 1
    params = {
        # 'exerciseUid': eid,
        'page': page,
        'pageSize': 5000
    }
    res = requests.get(URL, params=params)
    exam_data = res.json()['data']
    print 'Blank data count:', len(exam_data)
    # get source image from url
    for item in exam_data:
        fname = '{}@{}.png'.format(item['originUid'], item['_id'])
        if not os.path.isfile(os.path.join(IMAGE_PATH, fname)):
            get_blank_image(item['url'], fname)
    # dump data file to local
    json.dump(exam_data, open('./dataset/blank_data1.json', 'w'))


def get_blank_image(url, fname):
    '''download blank image to local'''
    res = requests.get(url).content
    img = np.asarray(bytearray(res), dtype=np.uint8)
    img = cv2.imdecode(img, cv2.IMREAD_GRAYSCALE)
    cv2.imwrite(os.path.join(IMAGE_PATH, fname), img)
    

def main():
    get_blank_from_dc()
    pass

if __name__ == '__main__':
    main()
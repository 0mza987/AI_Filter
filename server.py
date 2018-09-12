# -*-coding:utf-8-*-

import os
import cv2
import glob
import json
import time
import random
import zerorpc
import traceback

from settings import logger
from discriminator import discriminator

class AIFilter(object):
    
    def __init__(self):
        logger.info('================== Initializing AI Filter ==================')

    def discriminate(self, blank_data):
        """ discriminate blank data through AI Filter """
        start_time = time.time()
        res = {
            'data': None,
            'code': 102,
            'msg': ''
        }

        try:
            result = discriminator(blank_data)
            res['data'] = result
            res['code'] = 0
            res['msg'] = 'ok'

        except Exception as e:
            res['code'] = 103
            res['msg'] = 'error'
            logger.error(str(e))
            logger.error(traceback.format_exc())
        logger.info('Time cost: {} ms'.format((time.time()-start_time)*1000))
        return res
            
if __name__ == '__main__':
    
    # from RPC_list import RPC_menu
    
    server_name = 'ai_filter_RPC'
    server = zerorpc.Server(AIFilter())
    local_addr = '192.168.1.57:21000'
    server.bind('tcp://{}'.format(local_addr))
    logger.info('Server bind successful -> {}: {}'.format(server_name, local_addr))
    server.run()
    
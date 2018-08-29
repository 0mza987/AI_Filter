# -*-coding:utf-8-*-

import socket
from easydict import EasyDict as edict
__C = edict()
RPC_menu = __C
host_name = socket.gethostname()

env = 'dev'
if host_name in ['gpu-master', 'iZuf626a59hclcqeunc42eZ']:
    env = 'prod-aliyun'
elif host_name == 'sigmaai':
    env = 'honglin'

DICT_addr = {'dev':                     '192.168.1.115',
             'prod-hexin':              '192.168.1.115',    # suggest use different machine node
             'prod-aliyun':             '0.0.0.0',
             'honglin':                 '192.168.1.57'}

#
# preprocess & layout
#
__C.page_layout_PRC                     = '%s:99999' % DICT_addr[env]
__C.anchor_RPC                          = ''
__C.qrcode_RPC                          = ''
__C.student_id_RPC                      = ''                        # 学号识别（但姓名更靠谱）


#
# 姓名识别 & 处理
#
__C.name_detect_PRC                     = '%s:10000' % DICT_addr[env]
__C.name_ocr_RPC                        = '%s:10001' % DICT_addr[env]
__C.name_ngram_RPC                      = '%s:10002' % DICT_addr[env]


#
# English OCR
#
# 依赖项
__C.ocr_en_blank_detect_PRC             = '%s:19100' % DICT_addr[env]     # GPU 0
__C.ocr_en_correct_detect_PRC           = '%s:19200' % DICT_addr[env]     # GPU 0


# 英文 nginx 入口
__C.en_ocr_RPC                          = '%s:12000' % DICT_addr[env]
__C.en_ocr_RPC_01                       = '%s:12001' % DICT_addr[env]
__C.en_ocr_RPC_02                       = '%s:12002' % DICT_addr[env]
__C.en_ocr_RPC_03                       = '%s:12003' % DICT_addr[env]
__C.en_ocr_RPC_04                       = '%s:12004' % DICT_addr[env]
__C.en_ocr_RPC_05                       = '%s:12005' % DICT_addr[env]
__C.en_ocr_RPC_06                       = '%s:12006' % DICT_addr[env]
__C.en_ocr_RPC_07                       = '%s:12007' % DICT_addr[env]
__C.en_ocr_RPC_08                       = '%s:12008' % DICT_addr[env]
__C.en_ocr_RPC_09                       = '%s:12009' % DICT_addr[env]
__C.en_ocr_RPC_10                       = '%s:12010' % DICT_addr[env]


# 中文 nginx 入口
__C.cn_ocr_RPC                          = '%s:11000' % DICT_addr[env]
__C.cn_ocr_RPC_01                       = '%s:11001' % DICT_addr[env]
__C.cn_ocr_RPC_02                       = '%s:11002' % DICT_addr[env]


# 数理 nginx 入口
__C.math_ocr_RPC                        = '%s:13000' % DICT_addr[env]
__C.math_ocr_RPC_01                     = '%s:13001' % DICT_addr[env]


# __C.cn_ocr_test_RPC                   = '%s:11002'
__C.en_ngram_RPC                        = '%s:12101' % DICT_addr[env]


# 试题 RPC 入口 - 线上
# __C.quest_RPC_00                        = '%s:17000' % DICT_addr[env]
__C.quest_RPC_01                        = '%s:17001' % DICT_addr[env]
__C.quest_RPC_02                        = '%s:17002' % DICT_addr[env]
__C.quest_RPC_03                        = '%s:17003' % DICT_addr[env]
__C.quest_RPC_04                        = '%s:17004' % DICT_addr[env]
__C.quest_RPC_05                        = '%s:17005' % DICT_addr[env]
__C.quest_RPC_06                        = '%s:17006' % DICT_addr[env]
__C.quest_RPC_07                        = '%s:17007' % DICT_addr[env]
__C.quest_RPC_08                        = '%s:17008' % DICT_addr[env]
__C.quest_RPC_09                        = '%s:17009' % DICT_addr[env]
__C.quest_RPC_10                        = '%s:17010' % DICT_addr[env]


# 长句子语义理解
__C.quest_text_similar_RPC              = '%s:17100' % DICT_addr[env]
__C.quest_text_similar_RPC_01           = '%s:17101' % DICT_addr[env]

# 英语作文接口
__C.quest_en_essay_RPC_01               = '%s:17301' % DICT_addr[env]


#
# kuaidi RPC options
#
__C.kuaidi_RPC                          = '%s:18888' % DICT_addr[env]
__C.kuaidi_detect_PRC                   = '%s:18000' % DICT_addr[env]
__C.kuaidi_ocr_RPC                      = '%s:18001' % DICT_addr[env]


# AI Filter
__C.ai_filter_RPC                       = '%s:21000' % DICT_addr[env]
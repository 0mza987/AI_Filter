import os
import json
import zerorpc

def client_test():
    dataset = json.load(open('./dataset/updated_sample.json'))
    blank_client = zerorpc.Client(heartbeat=None, timeout=30)
    blank_client.connect('tcp://192.168.1.57:21000')

    cnt = 0
    right_cnt = 0
    for idx, item in enumerate(dataset[0:2000]):
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

if __name__ == '__main__':
    client_test()
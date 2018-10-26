import os, json
import data_gain as D

def download():
    eid = '3e3c71388e'
    exam_data = D.get_data_by_exam(eid)
    json.dump(exam_data, open('{}/{}.json'.format(D.DATA_PATH, eid), 'w'))
    print eid, 'done.'


if __name__ == '__main__':
    download()
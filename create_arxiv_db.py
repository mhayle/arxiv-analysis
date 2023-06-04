import requests
import time
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import timedelta, datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import ConnectionError

start_time = time.time()

PATH = os.path.join(os.path.abspath('./'), 'arxiv-analysis')
os.chdir(PATH)


OAI_URL = "https://export.arxiv.org/oai2"
OAI_NAMESPACES = {
    'OAI': 'http://www.openarchives.org/OAI/2.0/',
    'arXiv': 'http://arxiv.org/OAI/arXivRaw/'
}


# SQLite connection
conn = sqlite3.connect('arxiv_metadata.db')

c = conn.cursor()

# Create table
c.execute('''CREATE TABLE IF NOT EXISTS metadata
             (arxiv_id TEXT, title TEXT, summary TEXT, subject TEXT, published TEXT, updated TEXT, authors TEXT)''')


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10), 
       retry=retry_if_exception_type(ConnectionError))
def make_request(harvest_url, parameters):
    response = requests.get(harvest_url, params=parameters)
    return response


def get_record_chunk(resumptionToken=None, harvest_url=OAI_URL, metadataPrefix='arXivRaw'):
    parameters = {'verb': 'ListRecords'}

    if resumptionToken:
        parameters['resumptionToken'] = resumptionToken
    else:
        parameters['metadataPrefix'] = metadataPrefix

    response = make_request(harvest_url, parameters) 

    if response.status_code == 200:
        return response.text

    if response.status_code == 503:
        secs = int(response.headers.get('Retry-After', 20)) * 1.5
        print('Requested to wait, waiting {} seconds until retry...'.format(secs))

        time.sleep(secs)
        return get_record_chunk(resumptionToken=resumptionToken)
    
    else:
        raise Exception(
            'Unknown error in HTTP request {}, status code: {}'.format(
                response.url, response.status_code
            )
        )

def date_parser(elm):
    
    dates = [
        subnode.text
        for node in elm.findall("arXiv:{}".format("version"), OAI_NAMESPACES)
        for subnode in node.findall("arXiv:{}".format("date"), OAI_NAMESPACES)
    ]

    new_dates = [datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %Z").strftime('%Y-%m-%d %H:%M:%S') for d in dates]
    
    published = new_dates[0]
    updated = new_dates[len(new_dates)-1]

    return published, updated


def parse_record(r):

    arxiv_id = r.find('arXiv:{}'.format('id'), OAI_NAMESPACES).text
    title = r.find('arXiv:{}'.format('title'), OAI_NAMESPACES).text
    abstract = r.find('arXiv:{}'.format('abstract'), OAI_NAMESPACES).text
    published, updated = date_parser(r)
    authors = r.find('arXiv:{}'.format('authors'), OAI_NAMESPACES).text
    subjects = r.find('arXiv:{}'.format('categories'), OAI_NAMESPACES).text

    records = (arxiv_id, title, abstract, subjects, published, updated, authors)
    
    return records


# def oai_harvest(resumptionToken=None, autoresume=True):
def oai_harvest(resumptionToken=None):
    
    calls = 0
    total_records = 0

    print("Starting downlaod...")

    # tokenfile = 'resumptionToken.txt'

    # if autoresume:
    #     try:
    #         resumptionToken = open(tokenfile, 'r').read()
    #     except Exception as e:
    #         print("No tokenfile found '{}'".format(tokenfile))
    #         print("Starting download from scratch...")


    while True:
        root = ET.fromstring(get_record_chunk(resumptionToken))

        resumptionToken = root.find(
            'OAI:ListRecords/OAI:resumptionToken',
            OAI_NAMESPACES
        )

        resumptionToken = resumptionToken.text if resumptionToken is not None else ''

        records = root.findall(
            'OAI:ListRecords/OAI:record/OAI:metadata/arXiv:arXivRaw',
            OAI_NAMESPACES
        )

        for r in records:
            pr = parse_record(r)
            c.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?)", pr)
        
        conn.commit()

        calls = calls + 1
        total_records = total_records + len(records)
        
        print("Time:", timedelta(seconds=time.time()-start_time))
        print("Papers in DB:", total_records)
        print("API Calls:", calls)
        
        # if resumptionToken:
        #     with open(tokenfile, 'w') as fout:
        #         fout.write(resumptionToken)
        # else:
        #     print('No resumption token, query finished')
        #     return

        if resumptionToken is None:
            print('No resumption token. Done.')
            break
        
        time.sleep(10)


try:
    if __name__ == "__main__":
        oai_harvest()
finally:
    conn.close()
    print("Connection Closed.")



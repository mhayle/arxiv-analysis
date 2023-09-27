import requests
import time
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, date
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


start_time = time.time()

os.chdir('C:\\Users\\mrmus\\Documents\\GitHub\\arxiv-analysis')

OAI_URL = "https://export.arxiv.org/oai2"
OAI_NAMESPACES = {
    'OAI': 'http://www.openarchives.org/OAI/2.0/',
    'arXiv': 'http://arxiv.org/OAI/arXivRaw/'
}


# SQLite connection
conn = sqlite3.connect('arxiv_metadata.db')

c = conn.cursor()


# get last published date
c.execute("SELECT MAX(published) FROM metadata")
last_date = c.fetchall()[0][0]
# last_date = last_date.split(" ")[0]


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
        parameters['from'] = last_date.split(" ")[0]

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


def update_arxiv_metadata(resumptionToken=None):
    
    calls = 0
    records_added = 0

    print("Starting downlaod...")

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
            # if pr[4].split(" ")[0] > last_date:
            if pr[4] > last_date:    
                # c.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?)", pr)
                records_added += 1
        
        conn.commit()

        calls = calls + 1
        
        print("Time:", timedelta(seconds=time.time()-start_time))
        print("Records added:", records_added)
        print("API Calls:", calls)

        if resumptionToken is None:
            print('No resumption token. Done.')
            break
        
        time.sleep(10)



try:
    if __name__ == "__main__":
        update_arxiv_metadata()
finally:
    conn.close()
    print("Connection Closed.")
import requests
# import feedparser
import time
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import timedelta
# from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result

start_time = time.time()
# base_url = 'http://export.arxiv.org/api/query?'

# Search parameters
# search_query = 'all'  # search in all categories
# start = 50000         # start at the first result
# total_results = 1000  # number of results to retrieve for each request

# SQLite connection
conn = sqlite3.connect('arxiv-analysis\\arxiv_metadata.db')

c = conn.cursor()

# Create table
c.execute('''CREATE TABLE IF NOT EXISTS metadata
             (arxiv_id TEXT, title TEXT, summary TEXT, subject TEXT, published TEXT, updated TEXT, authors TEXT)''')

# @retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10),
#        retry=retry_if_result(lambda result: len(result.entries) < total_results))
# def fetch_data(start):
#     query = f'search_query={search_query}&start={start}&max_results={total_results}'
#     response = requests.get(base_url + query)
#     feed = feedparser.parse(response.content)
#     return feed

# def scrape_arxiv_metadata():
#     current_result = start
#     while True:

#         try:
#             feed = fetch_data(current_result)
#         except Exception as e:
#             print(f"Fetch data failed with {str(e)}, stopping.")
#             break

#         for entry in feed.entries:
#             arxiv_id = entry.id.split('/abs/')[-1]
#             title = entry.title
#             summary = entry.summary
#             published = entry.published
#             updated = entry.updated
#             authors = ", ".join([author.name for author in entry.authors])
#             subject = ", ".join([cat.term for cat in entry.tags])

#             # Insert a row of data
#             c.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?)",
#                       (arxiv_id, title, summary, subject, published, updated, authors))

#         # Save changes
#         conn.commit()

#         # Move on to the next results
#         current_result += total_results

#         # Give website a break
#         time.sleep(5)

#         print("Time:", timedelta(seconds=time.time()-start_time))
#         print("Papers in DB:", current_result)


OAI_URL = "https://export.arxiv.org/oai2"
OAI_NAMESPACES = {
    'OAI': 'http://www.openarchives.org/OAI/2.0/',
    'arXiv': 'http://arxiv.org/OAI/arXivRaw/'
}

chunk = 0
total_records = 0

def get_record_chunk(resumptionToken=None, harvest_url=OAI_URL, metadataPrefix='arXivRaw'):
    parameters = {'verb': 'ListRecords'}

    if resumptionToken:
        parameters['resumptionToken'] = resumptionToken
    else:
        parameters['metadataPrefix'] = metadataPrefix

    response = requests.get(harvest_url, params=parameters)

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


def parse_record(root):

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
        arxiv_id = r.find('arXiv:{}'.format('id'), OAI_NAMESPACES).text
        title = r.find('arXiv:{}'.format('title'), OAI_NAMESPACES).text
        abstract = r.find('arXiv:{}'.format('abstract'), OAI_NAMESPACES).text
        
        # published = r.find('arXiv:{}'.format('id'), OAI_NAMESPACES).text
        # updated = r.find('arXiv:{}'.format('id'), OAI_NAMESPACES).text
        
        authors = r.find('arXiv:{}'.format('authors'), OAI_NAMESPACES).text
        subjects = r.find('arXiv:{}'.format('categories'), OAI_NAMESPACES).text

        records = (arxiv_id, title, abstract, published, updated, authors, subjects)
        
        return records, resumptionToken


def oai_harvest(resumptionToken=None):
    
    while True:
        root = ET.fromstring(get_record_chunk(resumptionToken))
        records, resumptionToken = parse_record(root)

        chunk = chunk + 1
        total_records = total_records + len(records)

        c.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?)", records)

        if resumptionToken:
            # with open(tokenfile, 'w') as fout:
            #     fout.write(resumptionToken)
        else:
            print('No resumption token, query finished')
            return

        print("Time:", timedelta(seconds=time.time()-start_time))
        print("Papers in DB:", total_records)
        print("Chunks:", chunk)

        time.sleep(5)



try:
    if __name__ == "__main__":
        #scrape_arxiv_metadata()
        oai_harvest()
finally:
    conn.close()



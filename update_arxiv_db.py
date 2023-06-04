import requests
import feedparser
import time
import sqlite3
from sqlite3 import Error
from datetime import timedelta
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_result

start_time = time.time()
base_url = 'http://export.arxiv.org/api/query?'

# Search parameters
search_query = 'all'  # search in all categories
start = 0             # start at the first result
total_results = 1000  # number of results to retrieve for each request

# SQLite connection
conn = sqlite3.connect('arxiv-analysis\\arxiv_metadata.db')

c = conn.cursor()

# Create table
c.execute('''CREATE TABLE IF NOT EXISTS metadata
             (arxiv_id TEXT, title TEXT, summary TEXT, subject TEXT, published TEXT, updated TEXT, authors TEXT)''')

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10),
       retry=retry_if_result(lambda result: len(result.entries) < total_results))
def fetch_data(start):
    query = f'search_query={search_query}&start={start}&max_results={total_results}&sortBy=submittedDate&sortOrder=descending'
    response = requests.get(base_url + query)
    feed = feedparser.parse(response.content)
    return feed

def update_arxiv_metadata():
    current_result = start
    looping = True

    while looping:

        try:
            feed = fetch_data(current_result)
        except Exception as e:
            print(f"Fetch data failed with {str(e)}, stopping.")
            break

        for entry in feed.entries:
            arxiv_id = entry.id.split('/abs/')[-1]
            title = entry.title
            summary = entry.summary
            published = entry.published
            updated = entry.updated
            authors = ", ".join([author.name for author in entry.authors])
            subject = ", ".join([cat.term for cat in entry.tags])

            current_result += 1

            if published: # parse the date if it isnt current date
                looping = False
                break

            # Insert a row of data
            c.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?)",
                      (arxiv_id, title, summary, subject, published, updated, authors))

        # Save changes
        conn.commit()

        # # Move on to the next results
        # current_result += total_results

        # Give website a break
        time.sleep(5)

        print("Time:", timedelta(seconds=time.time()-start_time))
        print("Papers added:", current_result)


try:
    if __name__ == "__main__":
        update_arxiv_metadata()
finally:
    conn.close()
import requests
import feedparser
import time
import sqlite3


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

def scrape_arxiv_metadata():
    current_result = start
    while True:
        query = f'search_query={search_query}&start={current_result}&max_results={total_results}'
        response = requests.get(base_url + query)

        # Parsing the response
        feed = feedparser.parse(response.content)
        for entry in feed.entries:
            arxiv_id = entry.id.split('/abs/')[-1]
            title = entry.title
            summary = entry.summary
            published = entry.published
            updated = entry.updated
            authors = ", ".join([author.name for author in entry.authors])
            subject = ", ".join([cat.term for cat in entry.tags])

            # Insert a row of data
            c.execute("INSERT INTO metadata VALUES (?,?,?,?,?,?,?)",
                      (arxiv_id, title, summary, subject, published, updated, authors))

        # Save changes
        conn.commit()

        # Move on to the next results
        current_result += total_results

        # Give website a break
        print("Break time")
        time.sleep(15)


#if __name__ == "__main__":
#    scrape_arxiv_metadata()

# Close the connection when finished
conn.close()

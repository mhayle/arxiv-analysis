# arXiv Analyis

## Overview
[arXiv](https://arxiv.org/) is a free distritbution service and open-access archive with over 2 million scholarly articles in mathematics, computer science, physics, and many other STEM fields. I frequently used this service in college when searching for research papers. In this project, I collected data on all papers in the archive in order to study trends in different research areas and identify popular subjects. Some questions I want to answer in this project are:
1. What are the most popular research areas over time and how have they changed. 
2. What are frequently used buzzwords in paper titles among the different research areas?
3. Many papers have multiple subject tags. What subjects have the most overlap?

Tools used include:


## Results
I gathered all my results in an interactive dashboard to display my findings. (Still in progress)



## create_arxiv_db.py
This script collects the data of all research papers on arXiv and imports them into an SQLite database to be used in the analysis. arXiv has two different APIs available for accessing their data: the standard API and the Open Archive Initiative (OAI) API. I initally wrote this script using the standard API, but ran into issues with result limits and wasn't able to get more than 50,000 papers. The OAI API doesn't have this issue, however, since it is used for bulk accessing all historical data. I then rewrote the script using this API. Each call to the OAI API returns 1,000 papers. The first API call takes approximately 1.5 minutes and the following each take 20 seconds. Overall it took 12 hours to collect the data on all 2.3 million research paper on arXiv. 


## update_arxiv_db.py
This is a modified version of **create_arxiv_db.py**. The previous script is ran only once in order to create the database and gather all previous papers. This script is then used to update the database with new papers. It is automatically run daily through Windows Task Scheduler to find new papers published each day and add them into the databse. This ensures that the dashboard is always current and will show the most recent results. 


## arxiv_analysis.ipynb
This notebook contains exploratory data analysis (EDA) of the dataset. This includes basic stats such as paper, subject, and author publication counts. Some plots made include word clouds of the abstract and titles, publications over time, and a network graph between categories. 


## arxiv_dashboard.py
Not Made yet.

After the analysis, I gather all my results into a dashboard for easy viewing and digesting. This is essentially a summarized version of **arxiv_analysis.ipynb**, where I took all my significant graphs and findings and condensed them into a single page without all the excess code and messiness. The dashboard can be viewed [here](https://www.google.com). 


## Acknowledgements 
Thank you to arXiv for use of its open access interoperability.

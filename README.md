# mlb_stats

MLB stats web scraping, analysis, and presentation project. client: John Laghezza (xxxx2@gmail.com)

A docker container hosts a javascript front-end using jinja2 and Flask. Triggered by requests from the front-end, a Selenium thread scrapes the requested MLB stats from Fangraphs.com and populates an Sqlite database. Google graphs is used to display moving averages for said stats over various intervals.

### Prerequisites
Docker must be installed

### Deployment
docker-compose up -d

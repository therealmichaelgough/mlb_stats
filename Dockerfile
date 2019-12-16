FROM tiangolo/uwsgi-nginx:python2.7

# By default, allow unlimited file sizes, modify it to limit the file sizes
# To have a maximum of 1 MB (Nginx's default) change the line to:
# ENV NGINX_MAX_UPLOAD 1m
ENV NGINX_MAX_UPLOAD 0

# By default, Nginx listens on port 80.
# To modify this, change LISTEN_PORT environment variable.
# (in a Dockerfile or with an option for `docker run`)
ENV LISTEN_PORT 80

# Which uWSGI .ini file should be used, to make it customizable
ENV UWSGI_INI /app/uwsgi.ini

COPY ./__init__.py /

ENV PYTHONPATH "/selenium_wrc:/graph_server:/"
ENV PATH "$PATH:/web_driver"

# Update
# Install Chrome
# Set the Chrome repo.
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list
# Install Chrome.
RUN apt-get update && apt-get -y install google-chrome-stable


RUN apt-get update
RUN apt-get update && \
apt-get install -yq gconf-service libasound2 libatk1.0-0 libc6 \
libcairo2 libcups2 libdbus-1-3 \
libexpat1 libfontconfig1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 \
libglib2.0-0 libgtk-3-0 libnspr4 \
libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 \
libxcb1 libxcomposite1 \
libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 \
libxrender1 libxss1 libxtst6 \
ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release \
xdg-utils wget chromium unzip

RUN apt-get  install -y xvfb x11vnc x11-xkb-utils xfonts-100dpi xfonts-75dpi xfonts-scalable xfonts-cyrillic x11-apps libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1

ADD ./xvfb-chromium /usr/bin/xvfb-chromium

ENV DISPLAY :99
ENV CHROME_BIN /usr/bin/google-chrome


COPY ./graph_server/ /graph_server/
COPY ./selenium_wrc/ /selenium_wrc/
COPY ./requirements.txt /app
COPY ../standard_web_scraper/web_driver /web_driver/
#RUN mkdir /data

WORKDIR /app


# Install app dependencies
RUN pip install -r requirements.txt


ENV CHROMEDRIVER_VERSION 2.36
ENV CHROMEDRIVER_SHA256 2461384f541346bb882c997886f8976edc5a2e7559247c8642f599acd74c21d4

RUN curl -SLO "https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip" \
  && echo "$CHROMEDRIVER_SHA256  chromedriver_linux64.zip" | sha256sum -c - \
  && unzip "chromedriver_linux64.zip" -d /usr/local/bin \
  && rm "chromedriver_linux64.zip"


EXPOSE  80
CMD ["python", "/graph_server/rest_server.py"]
#ENTRYPOINT ["tail", "-f", "/dev/null"]

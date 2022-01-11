FROM ubuntu:18.04

## Install base utilities
## cv2 needs ffmpeg libsm6 libxext6
# RUN apt update & apt install -y build-essential wget ghostscript ffmpeg libsm6 libxext6 
RUN apt-get -y update && apt-get install -y --no-install-recommends wget ghostscript ffmpeg libsm6 libxext6 gnupg gnupg2 gnupg1 unzip gsfonts-x11
#& \
# apt-get clean & \
# rm -rf /var/lib/apt/lists/*

# # Install miniconda
ENV CONDA_DIR /opt/conda
RUN wget --no-check-certificate https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && chmod 777 ~/miniconda.sh && /bin/bash ~/miniconda.sh -b -p /opt/conda
# --quiet
# # Put conda in path so we can use conda activate
ENV PATH=$CONDA_DIR/bin:$PATH
RUN /bin/bash -c "source ~/.bashrc && conda init bash && \
    conda install -c anaconda numpy pillow pytest --yes && \
    conda install -c conda-forge matplotlib selenium opencv --yes"

# ---------
# chromedriver
# needs gnupg gnupg2 gnupg1 for installation
# ---------
RUN wget -q -O - --no-check-certificate https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add \
    && echo "deb [arch=amd64]  http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \
    && apt-get -y update && apt-get -y --no-install-recommends install google-chrome-stable \
    && wget https://chromedriver.storage.googleapis.com/2.41/chromedriver_linux64.zip \
    && unzip chromedriver_linux64.zip \
    && mv chromedriver /usr/bin/chromedriver \
    && chown root:root /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver \
    && rm chromedriver_linux64.zip

# ---------
# xpdf tools. Note: apt install xpdf does not work (maybe it's bin32?), stick
# to the provided TAR.
# needs gsfonts-x11
# ---------
RUN cd /home \
    && wget --no-check-certificate https://dl.xpdfreader.com/xpdf-tools-linux-4.03.tar.gz \
    && tar -zxvf xpdf-tools-linux-4.03.tar.gz \
    && rm xpdf-tools-linux-4.03.tar.gz \
    && cp /home/xpdf-tools-linux-4.03/bin64/pdftohtml /usr/local/bin \
    && rm -r /home/xpdf-tools-linux-4.03
FROM ubuntu:18.04

## Install base utilities
## cv2 needs ffmpeg libsm6 libxext6
RUN apt-get update && \
    apt-get install -y build-essential wget ghostscript && \
    apt-get install -y ffmpeg libsm6 libxext6 \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# # Install miniconda
ENV CONDA_DIR /opt/conda
RUN wget --quiet https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda.sh && \
    chmod 777 ~/miniconda.sh && /bin/bash ~/miniconda.sh -b -p /opt/conda

# # Put conda in path so we can use conda activate
ENV PATH=$CONDA_DIR/bin:$PATH
RUN /bin/bash -c "source ~/.bashrc && conda init bash && \
                conda install -c anaconda numpy pillow --yes && \
                conda install -c conda-forge matplotlib selenium opencv --yes"
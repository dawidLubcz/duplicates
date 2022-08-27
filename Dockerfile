FROM python:3.8-slim
WORKDIR ./
COPY . .

# use volume to access data on the host
# note: via docker finding duplicates can be much slower
# docker run -v /path/to/data/on/the/host:/data -t duplicates
CMD ["python3", "duplicates.py", "-r", "/data"]
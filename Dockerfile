FROM ubuntu:latest
LABEL authors="Ivan"

ENTRYPOINT ["top", "-b"]
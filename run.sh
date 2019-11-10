#!/usr/bin/env bash

IMG="ometria:latest"

function run {
    case "$1" in
    version)
        echo ${IMG}| awk -F: '{print $1}'
        ;;
    build)
        docker build --rm --no-cache -t ${IMG} . \
            && docker images | grep `echo ${IMG}|awk -F: '{print $1}'`
        ;;
    test)
        [[ -d state ]] || mkdir state
        docker run --rm -it \
            -w /opt/ometria \
            -v "${PWD}"/state:/opt/ometria/state \
            -e "OMETRIA_APIKEY=${OMETRIA_APIKEY}" \
            -e "MAILCHIMP_APIKEY=${MAILCHIMP_APIKEY}" \
            ${IMG} python -m pytest -v
        ;;
    go)
        [[ -d state ]] || mkdir state
        docker run --rm -it \
            -w /opt/ometria \
            -v "${PWD}"/state:/opt/ometria/state \
            -e "OMETRIA_APIKEY=${OMETRIA_APIKEY}" \
            -e "MAILCHIMP_APIKEY=${MAILCHIMP_APIKEY}" \
            ${IMG} importer/main.py
        ;;
    *)
        echo "# ---"
        echo "# version: Show Docker Image Version"
        echo "# build: Build Docker Image"
        echo "# test: Run tests"
        echo "# go: Run controller"
        echo "# ---"
        ;;
    esac

}

run $@
exit $?

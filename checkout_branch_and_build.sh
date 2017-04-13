#!/bin/bash

dir=$1
branch=$2

cd ${dir}

git checkout ${branch}
sudo make install

cd -

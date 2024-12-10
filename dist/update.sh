#!/bin/bash

echo 'restart webapp service'
sudo systemctl restart webapp.service

echo 'restart nginx'
sudo systemctl restart nginx

echo 'update finished'

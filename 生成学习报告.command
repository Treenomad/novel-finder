#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if python3 career_finder.py; then
  open reports/latest.html
else
  echo '生成失败，请查看上方提示。按回车关闭。'
  read
fi

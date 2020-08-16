#!/usr/bin/python2.7
# -*- coding: utf-8 -*-

# import sys
import re
import os
import time
import hashlib
import json
import codecs

from urllib import urlopen
from urllib import urlencode

APP_ID = ''
APP_SECRET = ''
# HTTP
API_URL = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
# HTTPS
# API_URL = https://fanyi-api.baidu.com/api/trans/vip/translate

# 已翻译文件的记录文件
RECORD_FILE = 'record.txt'
TRANSLATE_DIR = 'path/to/translate'
OUTPUT_DIR = 'path/to/output'

TRANS_STEP = 80
TRANS_CONTENT = '{TrAnS_CoNtEnT}'
SLEEP = 1 + 0.05
count = 0

# 正则算子预编译、
translate_sentence = re.compile(r'^translate.*?$')
translate_string_sentence = re.compile(r'^translate.*?strings:')
no_old_pattern = re.compile(r' {4}(?!old|#)(.*)\n')
with_old_pattern = re.compile(r' {4}(?!#)(.*)\n')

source_pattern = re.compile(r' {4}.*?[" ]')
query_pattern = re.compile(r'".*"')
left_curly_bracket_pattern = re.compile(r'(\{\{})')
right_curly_bracket_pattern = re.compile(r'(\}\})')
left_bracket_pattern = re.compile(r'(\[\[)')
right_bracket_pattern = re.compile(r'(\[\[)')
val_pattern = re.compile(r'(\[.*?\])')
tag_pattern = re.compile(r'(\{.*?\})')
url_pattern = re.compile(r'http[s]://[a-z|A-Z|\/|.]*[a-z|A-Z|\/]')
trans_replace_pattern = [
		left_curly_bracket_pattern, 
		right_curly_bracket_pattern,
		left_bracket_pattern,
		right_bracket_pattern,
		val_pattern,
		tag_pattern,
		url_pattern
	]


def encrypt(query, salt):
	# 加密
	md5 = hashlib.md5()
	string = APP_ID + query + salt + APP_SECRET
	md5.update(string)
	sign = md5.hexdigest()
	return sign


def is_translate_string_sentence(line):
	if translate_string_sentence.match(line):
		return True
	else:
		return False


def is_translate_sentence(line):
	if translate_sentence.match(line):
		return True
	else:
		return False


def translation_is_needed(line_str, string_flag):
	if string_flag:
		# string 语句，不翻译以old开头的
		pattern = no_old_pattern
	else:
		pattern = with_old_pattern
	if pattern.match(line_str):
		return True
	else:
		return False


def exist_or_create(path):
	if os.path.exists(path):
		return True
	else:
		os.makedirs(path)
		return False


def get_translation_query(line):
	"""
	处理需要翻译的行
	return: source_str, query, format_str_list
	"""
	i = 0
	replace_list = []
	format_str_list = []
	source_s = source_pattern.search(line).group()
	if source_s[-1] == '"':
		source_s = source_s[:-1]
	source_str = source_s + '%s\n' % TRANS_CONTENT
	query = query_pattern.search(line).group()[1:-1]
	# print(u'==> 处理翻译内容...')
	for pattern in trans_replace_pattern:
		res = pattern.findall(query)
		for replace in res:
			if replace in replace_list:
				continue
			query = query.replace(replace, '{{{}}}'.format(i))
			format_str_list.append(replace)
			replace_list.append('{{{}}}'.format(i))
			i += 1
	# print(u'==> 返回需要翻译的行的模板：{}'.format(query))
	# print(u'==> 返回待翻译字符串：{}'.format(query))
	# print(u'==> 返回待翻译字符串的替换字典：{}'.format(tuple(format_str_list)))
	return source_str, query, tuple(format_str_list)




def translate(q, from_lan='en', to_lan='zh'):
	# 发送翻译请求
	appid = APP_ID
	url = API_URL
	salt = str(int(time.time()))
	sign = encrypt(q, salt)
	data = {
		'q': q,
		'from': from_lan,
		'to': to_lan,
		'appid': appid,
		'salt': salt,
		'sign': sign
	}
	s = urlencode(data)
	res = urlopen(url, s.encode())
	res_dict = json.loads(res.read())
	return res_dict


def translate_file(file_path, file_name, output_dir, exclude=[]):
	if os.path.join(output_dir, file_name) in exclude:
		return False

	ENTER = '\n'
	DOUBLE_DOT = '"'
	string_flag = False
	format_str_list = []
	query_list = []
	output_list = []
	translated = []

	trans_num = 0
	with codecs.open(file_path, 'r', encoding='utf-8') as file:
		line = file.readline()
		while line:
			# 处理行
			if is_translate_string_sentence(line):
				string_flag = True
			elif is_translate_sentence(line):
				string_flag = False
			if translation_is_needed(line, string_flag) and all(ord(c) < 128 for c in line):
				# 需要翻译，则先把不需要翻译的部分提取出来
				print(u'==> 找到需要翻译的行：')
				print(u'==> {}'.format(line[:-1]))

				source_str, query, format_str = get_translation_query(line)
				query_list.append(query)
				format_str_list.append(format_str)
				output_line = {
					'is_translated': True,
					'line': source_str
				}
				trans_num += 1
			else:
				output_line = {
					'is_translated': False,
					'line': line.replace('\n', '')
				}
			# 暂存输出文件内容
			output_list.append(output_line)
			# 读取下一行
			line = file.readline()
    
	# 翻译长度太长，则分批翻译
	for i in range(0, len(query_list), TRANS_STEP):
		query_block = query_list[i: i+TRANS_STEP]

		query = ENTER.join(query_block)
		if query == '\n' or not query:
			return True
		trans_res = translate(query)
		if trans_res.get('error_code'):
			print(u'==> 翻译接口返回错误:\n')
			print(query)
			print(u'==> 翻译语句：{}'.format(query))
			print(u'==> 错误代码：{}， 错误信息： {}'.format(trans_res['error_code'], trans_res['error_msg']))
			input(' ========= puse any key continue ========= ')
			return False

		translated_block = [data['dst'] for data in trans_res['trans_result']]
		translated.extend(translated_block)
		time.sleep(SLEEP)

	print(u'==> 需要翻译的行数：{}'.format(trans_num))
	print(u'==> 翻译结果行数：{}'.format(len(translated)))
	print(u'==> 查询list长度：{}'.format(len(query_list)))
	exist_or_create(output_dir)
	with codecs.open(os.path.join(output_dir, file_name), 'wb', encoding='utf-8') as output_file:
		i = 0
		for line_item in output_list:
			if line_item['is_translated']:
				translated_content = DOUBLE_DOT + translated[i].format(*format_str_list[i]) + DOUBLE_DOT + ENTER
				line = line_item['line'].replace(TRANS_CONTENT, translated_content)
				i += 1
			else:
				line = line_item['line']
			output_file.write(line.decode('utf-8'))
	return True


def go_through_dir(root_dir, output_dir, extend='.rpy', through_subdir=True):
    record_file = open(RECORD_FILE, 'a+')
    exclude = [file.replace('\n', '') for file in record_file.readlines()]
    name_list = os.listdir(root_dir)
    for name in name_list:
        file_path = os.path.join(root_dir, name)
        if os.path.isdir(file_path) and through_subdir:
        	# 是文件夹且遍历文件
            print(u'==> 进入文件夹：{}'.format(name))
            go_through_dir(file_path, os.path.join(output_dir, name))
            continue

        if not name.endswith(extend):
    		continue

        global count
        count += 1
        print('==========================================================================================\n')
        print(u'翻译第 {} 个文件: {}'.format(count, name))

        # 处理文件
        trans_res = translate_file(file_path, name, output_dir, exclude)
        if trans_res:
        	record_file.write(os.path.join(output_dir, name) + '\n')
    record_file.close()


def main():
	root = TRANSLATE_DIR
	output_dir = OUTPUT_DIR
	go_through_dir(root, output_dir, through_subdir=True)


if __name__ == "__main__":
	main()

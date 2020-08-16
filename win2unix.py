#coding:utf-8
import os
import codecs
import chardet

#文件路径准备    
route = 'path/to/trans'

i = 0

#遍历路径下目录，文件夹，文件
for root,dirs,files in os.walk(route):
    #遍历文件

    for name in files:
        #归纳文件名特征
        if name.endswith('.rpy'):
            i += 1
            #拼接文件名(目录+文件名称)
            catalog=os.path.join(root,name)
            #把所有行分割符替换为换行符\n返回. 
            fp=open(catalog,"rU+")
            #读取文件并保存
            strings=fp.read()
            fp.close()

            cd = chardet.detect(strings[:1024])
            conding = cd['encoding']

            print(u'=> 第{}个文件：{}'.format(i, catalog))
            print(u'=> 编码：{}\n'.format(conding))

            #使用二进制写文件
            fp1=codecs.open(catalog,"wb", 'utf-8')
            fp1.seek(0)
            if conding == 'utf-8':
                s = strings.decode('utf-8')
            else:
                s = strings.decode('utf-8-sig')

            fp1.write(s)
            fp1.flush()
            fp1.close()
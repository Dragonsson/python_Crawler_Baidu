"""
coding = utf-8
author = 幻夜
mail = xjy333@mail.nwpu.edu.cn
以贴吧的电脑端为爬取对象
由输入的贴吧名字，爬取该贴吧下所有子贴的url，tiltle以及子贴下所有图片（不包含广告，头像类）
之前尝试用xpath爬取，由于bug太多，最后放弃，采用了正则表达式去爬取
本代码采取获取一页的所有信息再去存储，下载,所以是50个存储一次
该代码进行多次不同贴吧尝试，没有报错，希望广大网友能够发现bug并及时联系我
"""
import requests
import re
import json
import os
import time


class TiebaSipder(object):
    def __init__(self, tieba_name):

        self.part_url = "https://tieba.baidu.com"
        self.headers = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) "
                                      "Chrome/68.0.3440.106 Safari/537.36"}
        self.tieba_name = tieba_name
        # 贴吧第一次url
        self.start_url = "https://tieba.baidu.com/f?kw={}&pn=0".format(self.tieba_name)
        # 由于每次调用时都需要进行对正则进行处理，这里进行预处理减少操作步骤
        # 下一页的url
        self.next_url_pattern = re.compile('<a href="(.*?)" class="next pagination-item " >下一页&gt;</a>')
        # 每一个子贴的url
        self.detailtie_url_pattern = re.compile(r'href="/p(.*)" title')
        # 每一个子贴的标题
        self.tie_title_pattern = re.compile('title=\"(.*)\" target=')
        # 进行预处理，分组，保证子贴title和url相互对应，不会出现某一项为空时错位
        self.detail_list_pattern = re.compile("<a (.*?)</a>")
        # 图片的链接
        self.detail_img_pattern = re.compile('<img class="BDE_Image" src="(https://imgsa.baidu.com.*?)"')   # http://fc-feed.cdn.bcebos.com.* 为广告
        # 子贴的下一页
        self.detail_next_url_pattern = re.compile('<a href="(.*?)">下一页')

    def parse_url(self, url):    # 获得url的HTML文件string类型
        response = requests.get(url, headers=self.headers)
        assert response.status_code == 200
        # 超过百分之99的贴吧response.encoding为utf-8编码,但是电脑版贴吧会出现部分报错UnicodeDecodeError
        # 添加gbk后还未出现报错，如果出现报错，请邮联
        try:
            html_str = response.content.decode(response.encoding)
        except UnicodeDecodeError:
            html_str = response.content.decode("gbk")
        return html_str

    def get_content_list(self, html_str): #获取url、title和图片链接并保存在content_list中
        content_list = list()
        # 进行预处理，分组
        detail_url_list = re.findall(self.detail_list_pattern, html_str)
        
        for dul in detail_url_list:
            item = dict()
            try:
                # 从detail_url_list依次寻找
                item["detail_url"] = self.part_url + '/p' + re.search(self.detailtie_url_pattern, dul).group(1)
                item["tie_title"] = re.search(self.tie_title_pattern, dul).group(1)
            except AttributeError:
                # 由于经过预处理，有一些detail_url_list的元素并不会匹配到，会报错AttributeError，但不影响正常获取，pass
                pass
            else:
                # 上面两个键未匹配到，就不进行下面一步，尽量优化，减少执行步骤
                try:
                    # 获取子贴的所有图片（不包含广告，头像类）
                    item["img_list"] = self.get_list_img(item["detail_url"], [])
                    # print("IMG", item["img_list"])
                    # print("-"*100)
                except KeyError:
                    pass
            if item != {}:
                content_list.append(item)
            else:
                # 如果没匹配到，删除item
                del item
        try:
            next_url = 'https:' + re.search(self.next_url_pattern, html_str).group(1)
        except AttributeError:
            if content_list != list():
                # 此时为贴吧的最后一页，代码执行完毕
                print(content_list)
                print("所要爬取的贴吧已经全部爬取结束")
                next_url = None
            else:
                # 输入的贴吧名字不存在，代码结束
                print("你所要爬取的贴吧不存在，请重新输入贴吧名字")
                next_url = None
        finally:
            return next_url, content_list

    def get_list_img(self, detail_url, all_img_list):  # 获取单个贴中的所有图片
        detail_html_str = self.parse_url(detail_url)
        img_list = re.findall(self.detail_img_pattern, detail_html_str)
        # 获取当前页面所有图片的链接
        # img_list = detail_html.xpath("""//img[@class="BDE_Image"]/@src""")
        if img_list is not None:
            all_img_list.extend(img_list)
        # 获取下一页链接
        try:
            detail_next_url = re.search(self.detail_next_url_pattern, detail_html_str).group(1)
            print("DETAIL_NEXT_URL", detail_next_url)
        except AttributeError:
            # 子贴爬取完毕
            pass
        else:
            if detail_next_url:
                # 存在，则递归获取，循环直到整个贴的图片获取结束
                detail_next_url = self.part_url + detail_next_url
                return self.get_list_img(detail_next_url, all_img_list)
        return all_img_list

    def save_content_list(self, content_list):
        file_path = self.tieba_name + ".txt"
        with open(file_path, 'a', encoding='utf-8') as f:
            # 保证中文的正常写入
            for content in content_list:
                # 将列表中获取的数据按照格式写入，保证中文输入，保证缩进
                f.write(json.dumps(content, ensure_ascii=False, indent=4))
                # 优化写入格式，保证中文的写入
                f.write("\n")

    def download_img(self, content_list): 
    # 下载所有的图片并新创建文件夹存入图片
        for content_dic in content_list:
            try:
                # 创建
                os.mkdir('./{}_image/'.format(self.tieba_name) + content_dic["tie_title"])
            except FileExistsError:
                # 如果存在两个title文件夹一样的情况，（由于部分贴吧刷新快，会出现这种情况）
                print("{}文件夹已经存在，是否覆盖或者重新建立一个文件夹".format(os.getcwd() + '/image/' + content_dic["tie_title"]))
                while True:
                    answer = input("Y:确认覆盖，N：重新建立一个文件夹")
                    if answer == "Y"or"y":
                        # 重新覆盖，会将最新的图片下载进入
                        os.makedirs('./{}_image/'.format(self.tieba_name) + content_dic["tie_title"], exist_ok = True)
                        break
                    elif answer == "N"or"n":
                        # 否则则创建尾不同的文件夹
                        os.mkdir('./{}_image/'.format(self.tieba_name) + content_dic["tie_title"] + '2')
                        break
                    else:
                        print("请重新输入")
            img_num = 1
            for img_url in content_dic["img_list"]:  
            # 对content_dic["img_list"]进行遍历，对于每一个img_url下载，编号为1~N
                with open('./{}_image/'.format(self.tieba_name) + content_dic["tie_title"] + '/' + str(img_num) + '.jpg', 'wb') as f:
                    # 二进制文件，不能用utf-8
                    img_content = requests.get(img_url)
                    f.write(img_content.content)
                    img_num += 1

    def run(self):

        next_url = self.start_url
        try:
            # 创建名为所要爬取贴吧名字的文件夹，存储图片
            os.mkdir('./{}_image/'.format(self.tieba_name))
        except FileExistsError:
            # 如果已经存在报错，并且忽略文件夹时，会对原文件夹进行写入
            print("当文件已存在时，无法创建该文件。: './lol_image/'", "\n是否继续进行?")
            input("按下任意键继续")
        # 主循环
        while next_url is not None:
            # 1、获取第一个url地址，以及生成的html
            html_str = self.parse_url(next_url)
            # 2、根据第一个url返回的信息，提取下一页url和数据
            next_url, content_list = self.get_content_list(html_str)
            # 3 、实现图片的下载并保存
            self.download_img(content_list)
            # 4、保存数据
            self.save_content_list(content_list)


def main():
    tieba_name = input("输入要爬取的网站")
    tieba_sipder = TiebaSipder(tieba_name)
    tieba_sipder.run()


if __name__ == '__main__':
    main()

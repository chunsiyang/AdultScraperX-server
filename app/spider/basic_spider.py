import logging
from io import BytesIO
from lxml import etree  # Xpath包

from PIL import Image

from app.internel.config import ConfigManager
import app.internel.cache_tools as cacheTools

from app.internel.tools import Tools
import config.config as config
import requests


class BasicSpider:

    def __init__(self):
        self.tools = Tools()
        self.configmanager = ConfigManager()
        self.client_session = requests.Session()
        self.checkUrl = ''  # 服务状态检查Url 子类必须为此变量赋值
        self.media = {
            'm_id': '',
            'm_number': '',
            'm_title': '',
            'm_poster': '',
            'm_art_url': '',
            'm_summary': '',
            'm_studio': '',
            'm_directors': '',
            'm_collections': '',
            'm_year': '',
            'm_originallyAvailableAt': '',
            'm_category': '',
            'm_actor': ''
        }

    def searchWithCache(self, q, type):
        metaDate = cacheTools.checkCache(q, type)
        if metaDate is not None:
            logging.info('缓存命中： %s ， %s' % (q, type))
            return metaDate
        else:
            metaDate = self.search(q)
            if len(metaDate) is not 0:
                cacheTools.setCache(q, metaDate, type)
                logging.info('首次匹配设置缓存： %s ， %s' % (q, type))

        return metaDate

    def search(self, q):
        """
        根据番号爬取数据（子类必须实现）
        :param q: 番号
        :return:  json格式的数据plex直接使用
        """
        raise RuntimeError('未实现接口')

    def analysisMediaHtmlByxpath(self, html, q):
        """
       根据爬取的数据格式化为plex能使用的数据（子类必须实现，供search（q）方法使用的工具方法）
       :param html: 番号
       :param q: 番号
       :return:  格式化后的网站数据，可被plex使用
       """
        raise RuntimeError('未实现接口')

    def posterPicture(self, url, r, w, h):
        """
       处理海报图片，默认实现根据webui配置进行剪裁，如果子类无特殊需求不需要重写
       :param url: 图片地址
       :param r: 横向裁切位置
       :param w: 缩放比例:宽
       :param h: 缩放比例:高
       :return: 处理后的图片
       """
        cropped = None
        try:
            response = requests.get(url)
            if response.status_code == 403:
                response = self.client_session.get(url)
            
        except Exception as ex:
            print('error : %s' % repr(ex))
            return cropped

        img = Image.open(BytesIO(response.content))
        rimg = img.resize((int(w), int(h)), Image.ANTIALIAS)
        # (left, upper, right, lower)
        cropped = rimg.crop((int(w) - int(r), 0, int(w), int(h)))
        return cropped

    def artPicture(self, url, r, w, h):
        cropped = None
        """
        处理背景图片，默认实现不进行剪裁，如果子类无特殊需求不需要重写
        :param url: 图片地址
        :param r: 横向裁切位置
        :param w: 缩放比例:宽
        :param h: 缩放比例:高
        :return: 处理后的图片
        """
        cropped = None
        try:
            response = requests.get(url)
            if response.status_code == 403:
                response = self.client_session.get(url)
        except Exception as ex:
            print('error : %s' % repr(ex))
            return cropped
        img = Image.open(BytesIO(response.content))
        cropped = img.crop((0, 0, img.size[0], img.size[1]))

        return cropped

    def actorPicture(self, url, r, w, h):
        """
       处理艺人图片，默认实现根据webui配置进行剪裁，如果子类无特殊需求不需要重写
       :param url: 图片地址
       :param r: 横向裁切位置
       :param w: 缩放比例:宽
       :param h: 缩放比例:高
       :return: 处理后的图片
       """
        cropped = None
        try:
            response = requests.get(url)
            if response.status_code == 403:
                response = self.client_session.get(url)
        except Exception as ex:
            print('error : %s' % repr(ex))
            return cropped

        img = Image.open(BytesIO(response.content))
        rimg = img.resize((int(w), int(h)), Image.ANTIALIAS)
        # (left, upper, right, lower)
        cropped = rimg.crop((int(w) - int(r), 0, int(w), int(h)))
        # TODO 目前除Arzon实现了演员图片外其他站未实现，且默认实现未提供
        return cropped

    def getName(self):
        return self.__class__.__name__

    def pictureProcessing(self, data):
        mode = data['mode']
        url = data['url']
        r = config.IMG_R
        w = config.IMG_W
        h = config.IMG_H
        webkey = data['webkey']
        cropped = None
        # 开始剪切
        if mode == 'poster':
            cropped = self.posterPicture(url, r, w, h)
        if mode == 'art':
            cropped = self.artPicture(url, r, w, h)
        if mode == 'actor':
            cropped = self.actorPicture(url, r, w, h)
        return cropped

    def pictureProcessingCFT(self, data,r,w,h):        
        mode = data['mode']
        url = data['url']
        webkey = data['webkey']
        cropped = None
        # 开始剪切        
        if r == '0':
            r = config.IMG_R
        if w == '0':
            w = config.IMG_W
        if h == '0':
            h = config.IMG_H
        if mode == 'poster':
            cropped = self.posterPicture(url, r, w, h)
        if mode == 'art':
            cropped = self.artPicture(url, r, w, h)
        if mode == 'actor':
            cropped = self.actorPicture(url, r, w, h)
        return cropped

    def webSiteConfirmByurl(self, url, headers):
        '''
        针对有需要确认访问声明的站点
        return: <dict{issuccess,ex}>
        '''
        item = {
            'issuccess': False,
            'ex': None
        }
        self.client_session.headers = headers
        try:
            self.client_session.get(
                url, allow_redirects=False)
        except requests.RequestException as e:
            item.update({'issuccess': False, 'ex': e})

        item.update({'issuccess': True, 'ex': None})
        return item

    def getimage(self, url):
        try:
            r = self.client_session.get(url)
        except requests.RequestException as e:

            return r.content

    def getHtmlByurl(self, url):
        '''
        获取html对象函数
        url：需要访问的地址<str>
        return:<dict{issuccess,ex,html}>
        '''
        html = None
        item = {'issuccess': False, 'html': None, 'ex': None}
        try:
            r = self.client_session.get(url, allow_redirects=False)
        except requests.RequestException as e:
            item.update({'issuccess': False, 'html': None, 'ex': e})
            return item

        r.encoding = r.apparent_encoding
        if r.status_code == 200:
            t = r.text.replace('\r', '').replace(
                '\n', '').replace('\r\n', '')
            t = t.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            t = t.replace(
                '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"', '')
            t = t.replace(
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">', '')

            html = etree.HTML(t)
            item.update({'issuccess': True, 'html': html, 'ex': None})
        else:
            scc = self.tools.statusCodeConvert(r.status_code)
            logging.info('匹配数据结果：%s' % scc)
            item.update({'issuccess': False, 'html': None,
                         'execpt': scc})
        return item

    def getHtmlByurlheaders(self, url, headers):
        """
        获取html对象函数
        url：需要访问的地址<str>
        return:<dict{issuccess,ex,html}>
        """
        html = None
        item = {'issuccess': False, 'html': None, 'ex': None}
        try:
            self.client_session.headers = headers
            r = self.client_session.get(url, allow_redirects=False)
        except requests.RequestException as e:
            item.update({'issuccess': False, 'html': None, 'ex': e})
            return item

        r.encoding = r.apparent_encoding
        if r.status_code == 200:
            t = r.text.replace('\r', '').replace(
                '\n', '').replace('\r\n', '')
            t = t.replace('<?xml version="1.0" encoding="UTF-8"?>', '')
            t = t.replace(
                '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"', '')
            t = t.replace(
                '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">', '')

            html = etree.HTML(t)
            item.update({'issuccess': True, 'html': html, 'ex': None})
        else:
            scc = self.tools.statusCodeConvert(r.status_code)
            item.update({'issuccess': False, 'html': None,
                         'execpt': scc})
        return item

    def getitemspage(self, html, xpaths):
        url = html.xpath(xpaths)
        return url

    def checkServer(self):
        """
        检测站点是否在线
        :return: 站点是否在线
        """
        html_item = self.getHtmlByurl(self.checkUrl)
        if html_item['issuccess']:
            return True
        else:
            return False
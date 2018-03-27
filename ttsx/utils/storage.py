from django.core.files.storage import Storage
from django.conf import settings
#python链接FastDFS服务器的驱动
from fdfs_client.client import Fdfs_client



class FdfsStorage(Storage):
    def save(self, name, content, max_length=None):
        #从网络流中读取文件数据
        buffer = content.read()

        #根据配置文件创建链接的客户端
        client = Fdfs_client(settings.FDFS_CLIENT)
        #调用方法上传文件
        # client.upload_appender_by_file(buffer)在本地服务器获取
        try:
            result = client.upload_appender_by_buffer(buffer)#在request请求报文中获取
        except:
            raise
        if result.get('Status')=='Upload successed.':
            return result.get('Remote file_id')
        else:
            raise Exception('上传文件失败')

    def url(self, name):
        return settings.FDFS_SERVER+name
from haystack import indexes
from .models import GoodsSKU

class GoodsSKUIndex(indexes.SearchIndex, indexes.Indexable):
    """定义字符类型的属性，名称固定为text
        document=True 表示简历的索引数据存储在文件中
        use_template=True表示查询表的哪一列，通过模板指定表中的字段
    """
    text = indexes.CharField(document=True, use_template=True)

    #针对哪张表进行查询
    def get_model(self):
        """从哪个表中查询"""
        return GoodsSKU

    #针对哪张表的哪一行进行查询
    def index_queryset(self, using=None):
        """返回要建立索引的数据"""
        return self.get_model().objects.filter(isDelete=False)
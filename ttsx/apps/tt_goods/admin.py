from django.contrib import admin
from .models import GoodsCategory,GoodsSKU,Goods,GoodsImage,IndexCategoryGoodsBanner,IndexGoodsBanner,IndexPromotionBanner
from django.shortcuts import render
from .models import GoodsCategory,IndexGoodsBanner,IndexPromotionBanner,IndexCategoryGoodsBanner
from django.conf import settings
import os
import time
from celery_tasks.tasks import generate_html
from django.core.cache import cache

class BaseAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.save()
        #生成静态页面
        generate_html.delay()
        #删除缓存
        cache.delete('index')
    #当删除对象时，这个方法会被调用
    def delete_model(self, request, obj):
        obj.delete()
        generate_html.delay()
        #删除缓存
        cache.delete('index')


class GoodsCategoryAdmin(BaseAdmin):
    list_display = ['id','name','logg']

    #当添加对象，修改对象时，这个方法会被调用
class IndexCategoryGoodsBannerAdmin(BaseAdmin):
    pass

class IndexGoodsBannerAdmin(BaseAdmin):
    pass

class IndexPromotionBannerAdmin(BaseAdmin):
    pass

admin.site.register(GoodsCategory,GoodsCategoryAdmin)
admin.site.register(GoodsSKU)
admin.site.register(Goods)
admin.site.register(GoodsImage)
admin.site.register(IndexCategoryGoodsBanner,IndexCategoryGoodsBannerAdmin)
admin.site.register(IndexGoodsBanner,IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner,IndexPromotionBannerAdmin)
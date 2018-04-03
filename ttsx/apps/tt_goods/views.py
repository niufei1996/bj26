from django.shortcuts import render
from .models import GoodsCategory,IndexGoodsBanner,IndexPromotionBanner,IndexCategoryGoodsBanner,GoodsSKU
from django.conf import settings
import os
from django.core.cache import cache
from django.http import Http404
from django_redis import get_redis_connection
from django.core.paginator import Paginator,Page
from haystack.generic_views import SearchView
from utils.page_list import get_page_list
import json


def fdfs_test(request):
    category = GoodsCategory.objects.get(pk=1)
    context= {'category':category}
    return render(request,'fdfs_test.html',context)

def index(request):
    #从缓存中读取数据
    context=cache.get('index')

    if context is None:
        print('---------------------')
        #查询分类信息
        category_list = GoodsCategory.objects.all()

        #查询轮播图片
        banner_list = IndexGoodsBanner.objects.all().order_by('index')

        #查询广告
        adv_list = IndexPromotionBanner.objects.all().order_by('index')

        #查询每个分类的推荐产品
        for category in category_list:
            #查询推荐的标题商品
            category.title_list = IndexCategoryGoodsBanner.objects.filter(display_type=0,
            category=category).order_by('index')[0:3]
            #查询推荐的图片商品
            category.img_list = IndexCategoryGoodsBanner.objects.filter(display_type=1,
            category=category).order_by('index')[0:4]


        context = {
            'title':'首页',
            'category_list':category_list,
            'banner_list':banner_list,
            'adv_list':adv_list,
        }

        #缓存数据
        cache.set('index',context,3600)
    #设置购物车数量
    context['total_count'] = get_cart_total(request)

    response = render(request,'index.html', context)


    return response


def detail(request,sku_id):
    #查询商品信息
    try:
        sku = GoodsSKU.objects.get(pk=sku_id)
    except:
        raise Http404()

    #查询分类信息
    category_list = GoodsCategory.objects.all()

    #查询新品推荐
    # new_list = GoodsSKU.objects.filter(category=sku.category).order_by('-id')[0:2]
    new_list = sku.category.goodssku_set.all().order_by('-id')[0:2]

    #查询当前商品对应的所有陈列
    goods=sku.goods
    other_list = goods.goodssku_set.all()

    #最近浏览
    if request.user.is_authenticated():
        redis_client = get_redis_connection()
        #构造键
        key='history%d'%request.user.id
        #如果编号已经存在，则删除
        redis_client.lrem(key,0,sku_id)
        #讲当前编号加入
        redis_client.lpush(key, sku_id)
        #超过5个，则删除
        if redis_client.llen(key)>5:
            redis_client.rpop(key)


    context={
        'title':'商品详情',
        'sku':sku,
        'category_list':category_list,
        'new_list':new_list,
        'other_list':other_list,
    }
    context['total_count'] = get_cart_total(request)


    return render(request,'detail.html',context)

def list_sku(request,category_id):
    try:
        # 查询当前分类对象
        category_now = GoodsCategory.objects.get(pk=category_id)
    except:
        raise Http404

    #接受排序规则
    order=int(request.GET.get('order',1))
    if order==2:
        order_by='-price'#按照价格降序
    elif order==3:
        order_by='price'#按照价格升序
    elif order==4:
        order_by='sales'#按照销量降序
    else:
        order_by='-id'  #按照编号降序排列
    #查询当前分类的所有商品
    sku_list = GoodsSKU.objects.filter(category=category_id).order_by(order_by)

    #分页
    paginator = Paginator(sku_list,1)
    #总页数
    total_page = paginator.num_pages
    #接受页码值，进行判断
    pindex=int(request.GET.get('pindex',1))
    if pindex<1:
        pindex=1

    if pindex>total_page:
        pindex=total_page

    #查询制定页码数据
    page = paginator.page(pindex)

    #构造页码的列表，用于提示页码链接
    # page_list = []# 3 4 5 6 7
    # #如果不足5页，则显示所有数字
    # if total_page<=5:
    #     page_list=range(1,total_page+1)
    # #如果是前两也，则显示1-5
    # elif pindex<=2:
    #     page_list=range(1,6)
    # #如果是最后两页，则显示最后五页
    # elif pindex>=total_page-1:
    #     page_list=range(total_page-4,total_page+1)
    # else:
    #     page_list=range(pindex-2,pindex+3)
    page_list = get_page_list(total_page, pindex)


    #查询所有分类信息
    category_list = GoodsCategory.objects.all()

    #当前分类的最新的两个商品
    new_list = category_now.goodssku_set.all().order_by('-id')[0:2]

    context = {
        'title':'商品列表',
        'sku_list':sku_list,
        'page':page,
        'category_list':category_list,
        'category_now':category_now,
        'new_list':new_list,
        'order':order,
        'page_list':page_list
    }

    context['total_count'] = get_cart_total(request)


    return render(request,'list.html',context)

class MySearchView(SearchView):

    def get(self, request, *args, **kwargs):

        self.request = request
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['title']='搜索结果'
        context['category_list']=GoodsCategory.objects.all()

        #页码控制
        total_page=context['paginator'].num_pages
        pindex=context['page_obj'].number
        context['page_list']=get_page_list(total_page,pindex)

        context['total_count'] = get_cart_total(self.request)

        return context


def get_cart_total(request):
    total_count = 0
    #判断用户是否登陆
    if request.user.is_authenticated():
        #如果登陆则从redis中读取
        redis_client = get_redis_connection()
        key = 'cart%d'%request.user.id
        for v in redis_client.hvals(key):
            total_count+=int(v)

    else:
        #如果未登陆则从cookie中读取
        cart_str = request.COOKIES.get('cart')
        if cart_str:
            cart_dict = json.loads(cart_str)
            for k,v in cart_dict.items():
                total_count+=v



    return total_count
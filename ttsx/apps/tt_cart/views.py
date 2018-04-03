from django.shortcuts import render
from django.http import JsonResponse,Http404
from tt_goods.models import GoodsSKU
import json
from django_redis import get_redis_connection



def add(request):
    if request.method!='POST':
        return  Http404


    #接受商品编号，数量
    dict=request.POST
    sku_id = dict.get('sku_id')
    count = int(dict.get('count',0))

    #验证数据有效性

    #判断商品编号是否合法
    if GoodsSKU.objects.filter(id=sku_id).count() <= 0:
        return JsonResponse({'status':2})
    #判断数量是否合法
    if count <= 0:
        return JsonResponse({'status':3})
    if count >= 5:
        count = 5


    #区分用户是否登陆
    if request.user.is_authenticated():
        #如果已经登陆，则购物车信息存储到redis中
        redis_client = get_redis_connection()
        key = 'cart%d'%request.user.id
        if redis_client.hexists(key,sku_id):
            #如果存在则数量相加
            count1 = int(redis_client.hget(key,sku_id))
            count2 = count
            count0 = count1 + count2
            if count0 > 5:
                count0 = 5
            redis_client.hset(key,sku_id,count0)
        else:
            redis_client.hset(key,sku_id,count)

        #计算购物车总数
        total_count=0
        for v in redis_client.hvals(key):
            total_count+=int(v)

        response = JsonResponse({'status': 1, 'total_count': total_count})

    else:
        #如果未登录，则购物车信息存储到cookie中
        #构建字典数据
        #读取cookie中的购物车ixnxi，然后讲数据加入这个字典中
        cart_dict={}
        cart_str = request.COOKIES.get('cart')
        if cart_str:#已经存在购物车信息
            #将购物车信息转换成字典
            cart_dict = json.loads(cart_str)
       #将指定的商品加入购物车
        #判断购物车中是否有sku_id商品
        if sku_id in cart_dict:
            #如果商品存在，则数量相加
            count1 = cart_dict[sku_id]
            count0 = count1+count
            if count0 > 5:
                count0 = 5
            cart_dict[sku_id]=count0


        else:
            #如果不存在，则添加
            cart_dict[sku_id] = count

        #讲字典转换成字符串，用于存入cookie中
        cart_str = json.dumps(cart_dict)

        #计算商品总数量
        total_count = 0
        for k,v in cart_dict.items():
            total_count+=v



        response = JsonResponse({'status': 1,'total_count':total_count})



        #写入cookie
        response.set_cookie('cart',cart_str,expires=60*60*24)


    print(response)
    return response


def index(request):
    sku_list = []
    #查询购物车中的商品信息
    if request.user.is_authenticated():
        #如果登陆则从redis中读取信息
        redis_client = get_redis_connection()
        key = 'cart%d'%request.user.id
        id_list = redis_client.hkeys(key)
        for id1 in id_list:
            sku = GoodsSKU.objects.get(pk=id1)
            sku.cart_count = int(redis_client.hget(key,id1))
            sku_list.append(sku)
    else:
        #如果未登陆则从cookie中读取信息
        cart_str = request.COOKIES.get('cart')
        if cart_str:
            #将购物车字符串转换成字典
            cart_dict = json.loads(cart_str)
            #遍历字典，根据商品编号查询商品对象
            #k表示商品编号，v表示商品数量   键：值
            # print(cart_dir)
            for k,v in cart_dict.items():
                sku = GoodsSKU.objects.get(pk=k)
                sku.cart_count = v
                sku_list.append(sku)
            # print(sku)

    context = {
        'title':'购物车',
        'sku_list':sku_list,
    }
    return render(request,'cart.html',context)

def edit(request):
    if request.method!='POST':
        return Http404()

    #接受参数
    dict = request.POST
    sku_id = dict.get('sku_id',0)
    count = dict.get('count',0)

    response = JsonResponse({'status': 1})
    #验证数据有效性
    #判断商品是否存在
    if GoodsSKU.objects.filter(pk=sku_id).count()<=0:
        return JsonResponse({'status':2})
    #判断数量是一个有效数字
    try:
        count=int(count)
    except:
        return JsonResponse({'status':3})
    #判断数量大于0并小于5
    if count<=0:
        count=1
    elif count>=5:
        count=5

    #改写购物车中的数量
    if request.user.is_authenticated():
        #如果已登陆，操作redis
        redis_client = get_redis_connection()
        redis_client.hset('cart%d'%request.user.id,sku_id,count)

    else:
        #如果未登陆，则操作cookie
        cart_str = request.COOKIES.get('cart')
        if cart_str:
            cart_dict = json.loads(cart_str)
            #改写数量
            cart_dict[sku_id]=count
            #将字典转成字符串，用于cookie保存
            cart_str = json.dumps(cart_dict)
            #写cookie
            response.set_cookie('cart',cart_str,expires=60*60*24)



    return response

def delete(request):
    if request.method != 'POST':
        return Http404()

    sku_id = request.POST.get('sku_id')

    response = JsonResponse({'status':1})
    if request.user.is_authenticated():
        redis_client = get_redis_connection()
        redis_client.hdel('cart%d'%request.user.id,sku_id)
    else:
        cart_str = request.COOKIES.get('cart')
        if cart_str:
            cart_dict = json.loads(cart_str)
            cart_dict.pop(sku_id)
            cart_str = json.dumps(cart_dict)
            response.set_cookie('cart',cart_str,expires=60*60*24)
    return response

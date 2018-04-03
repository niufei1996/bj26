from django.shortcuts import render,redirect
from django.views.generic import View
from .models import User,Address,AreaInfo
import re
from django.http import HttpResponse,JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired
from celery_tasks.tasks import send_user_active
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.decorators import login_required
from utils.views import LoginRequiredView,LoginRequiredViewMixin
from django_redis import get_redis_connection
from tt_goods.models import GoodsSKU
import json

#判断register访问是post请求还是get请求
class RegisterView(View):
    #如果是get请求做的处理
    def get(self,request):
        return render(request, 'register.html')
    #如果是post请求做的处理
    def post(self,request):
        #post请求获得post，同时获得request请求中的加密的表单
        dict = request.POST
        uname = dict.get('user_name')
        pwd = dict.get('pwd')
        cpwd = dict.get('cpwd')
        email = dict.get('email')
        uallow = dict.get('allow')


        context = {
            'err_msg':'',
            'uname':uname,
            'pwd':pwd,
            'cpwd':cpwd,
            'email':email,
            'title':'注册'

        }


        if uallow is None:
            context['err_msg']='请接受协议'
            return render(request,'register.html',context)

        if not all([uname,pwd,cpwd,email]):
            context['err_msg']='请填写完整信息'
            return render(request,'register.html',context)

        if pwd != cpwd:
            context['err_msg']='密码不一致'
            return render(request,'register.html',context)

        if User.objects.filter(username=uname).count()>0:
            context['err_msg']='用户已存在'
            return render(request,'register.html',context)

        if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$',email):
            context['err_msg']='邮箱格式不正确'
            return render(request,'register.html',context)
        # #
        if User.objects.filter(email=email).count()>0:
            context['err_msg']='邮箱已经存在'
            return render(request,'register.html',context)



        user = User.objects.create_user(uname,email,pwd)
        user.is_active = False
        user.save()

        # #加密编号
        # serializer = Serializer(settings.SECRET_KEY,60*60)
        # value = serializer.dumps({'id':user.id}).decode()
        #
        # #激活邮箱
        # # msg = '<a href="http:/127.0.0.1:8000/user/active/%s>点击激活</a>'%value
        # msg = '<a href="http://127.0.0.1:8000/user/active/%s">点击激活</a>' % value
        # send_mail('天天生鲜<账户激活>','',settings.EMAIL_FORM,[email],html_message=msg)

        #celery执行
        send_user_active.delay(user.id,user.email)

        return HttpResponse('注册成功，请稍候到邮箱中激活账户')
def active(request,value):
    #链接失效会报错
    try:
        serializer = Serializer(settings.SECRET_KEY)
        #解密，解密出来的是个str字符串属性
        dict = serializer.loads(value)
    except SignatureExpired as e:
        return HttpResponse('链接已过期，请重新发送邮件')

    uid = dict.get('id')
    user = User.objects.get(pk=uid)
    user.is_active=True
    user.save()

    return redirect('/user/login')

#判断用户名在不在数据库
def exists(request):
    uname = request.GET.get('uname')

    if uname is not None:
        result = User.objects.filter(username=uname).count()

    return JsonResponse({'result':result})

#用户登陆
class LoginView(View):
    def get(self,request):
        uname = request.COOKIES.get('uname','')
        context = {'uname':uname}
        return render(request,'login.html',context)

    def post(self,request):
        dict = request.POST
        uname = dict.get('username')
        upwd = dict.get('pwd')
        remember = dict.get('remember')

        context = {
            'err_msg':'',
            'uname': uname,
            'upwd': upwd,
            'title':'登录'
        }

        if not all([uname,upwd]):
            context['err_msg'] = '请填写完整信息'
            return render(request,'login.html',context)

        user = authenticate(username=uname,password=upwd)

        if user is None:
            context['err_msg'] = '用户名或密码错误'
            return render(request,'login.html',context)

        if not user.is_active:
            context['err_msg'] = '请去邮箱激活'
            return render(request,'login.html',context)

        #保持登陆状态
        login(request,user)
        #获取next参数
        next_url = request.GET.get('next','/user/info')

        response = redirect(next_url)
        if remember is None:
            response.delete_cookie('uname')
        else:
            response.set_cookie('uname',uname,expires=60*60*24)

        #1.读取cookie中的购物车信息，转成字典
        cart_str = request.COOKIES.get('cart')
        if cart_str:
            # 讲cookie中的购物车信息转存入redis中
            key = 'cart%d' % request.user.id
            redis_client = get_redis_connection()
            cart_dict = json.loads(cart_str)
            #2.遍历字典
            for k,v in cart_dict.items():
                #3.判断redis中是否已经存在这个商品
                if redis_client.hexists(key,k):
                    #3.1如果有则数量相加
                    count1 = int(redis_client.hget(key,k))
                    count2 = v
                    count0 = count1 + count2
                    if count0 > 5:
                        count0 = 5
                    redis_client.hset(key,k,count0)
                else:
                    #如果没有则直接添加
                    redis_client.hset(key,k,v)
            response.delete_cookie('cart')

        return response
#用户退出
def logout_user(request):
    logout(request)
    return redirect('/user/login')

@login_required
def info(request):
    address = request.user.address_set.filter(isDefault=True)

    if address:
        address=address[0]
    else:
        address=None

    # #获取redis服务器的链接.根据settings.py中的caches的default获取
    redis_client = get_redis_connection()
    # #因为redis中会存储所有用户的浏览记录，所以在建上需要区分用户
    gid_list = redis_client.lrange('history%d'%request.user.id,0,-1)
    print('history%d'%request.user.id)
    # #根据商品编号查询商品对象
    goods_list = []

    for gid in gid_list:
        goods_list.append(GoodsSKU.objects.get(pk=gid))
    print(goods_list)
    context = {
        'title':'个人信息',
        'address': address,
        'goods_list':goods_list,
    }
    return render(request,'user_center_info.html',context)

@login_required
def order(request):
    context = {}
    return render(request,'user_center_order.html',context)

class SiteView(LoginRequiredViewMixin,View):
    def get(self,request):

        addr_list = Address.objects.filter(user=request.user)

        context = {
            'title':'收货地址',
            'addr_list':addr_list
        }
        return render(request,'user_center_site.html',context)

    def post(self,request):
        dict = request.POST
        receiver = dict.get('receiver')
        provice = dict.get('provice')  # 选中的option的value值
        city = dict.get('city')
        district = dict.get('district')
        addr = dict.get('addr')
        code = dict.get('code')
        phone = dict.get('phone')
        default = dict.get('default')

        if not all([receiver,provice,city,district,addr,code,phone]):
            return render(request,'user_center_site.html',{'err_msg':'信息填写不完整'})

        address = Address()
        address.receiver = receiver
        address.province_id = provice
        address.city_id = city
        address.district_id = district
        address.addr = addr
        address.code = code
        address.phone_number = phone
        if default:
            address.isDefault = True
        address.user = request.user
        address.save()

        # # context = {}
        # request.user.is_authenticated()
        return redirect('/user/site')

def area(request):
    #获取上级地区编号
    pid = request.GET.get('pid')
    if pid is None:
        slist=AreaInfo.objects.filter(aParent__isnull=True)
    else:
        # slist=AreaInfo.objects.filter(aParent__id=pid)
        slist = AreaInfo.objects.filter(aParent_id=pid)
    #查询省的信息
    # slist = AreaInfo.objects.filter(aParent__isnull=True)

    slist2 = []
    for s in slist:
        slist2.append({'id':s.id,'title':s.title})

    return  JsonResponse({'list':slist2})
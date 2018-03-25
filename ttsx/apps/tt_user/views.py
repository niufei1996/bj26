from django.shortcuts import render,redirect
from django.views.generic import View
from .models import User
import re
from django.http import HttpResponse,JsonResponse
from django.core.mail import send_mail
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from django.core.mail import send_mail
from django.conf import settings
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired
from celery_tasks.tasks import send_user_active
from django.contrib.auth import authenticate,login
# Create your views here.


class RegisterView(View):
    def get(self,request):
        return render(request, 'register.html')

    def post(self,request):
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
        # if User.objects.filter(email=email).count()>0:
        #     context['err_msg']='邮箱已经存在'
        #     return render(request,'register.html',context)



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
    try:
        serializer = Serializer(settings.SECRET_KEY)
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

        login(request,user)

        response = redirect('/user/info')
        if remember is None:
            response.delete_cookie('uname')
        else:
            response.set_cookie('uname',uname,expires=60*60*24)


        return response
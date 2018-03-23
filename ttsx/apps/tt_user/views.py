from django.shortcuts import render
from django.views.generic import View
from .models import User
import re
from django.http import HttpResponse,JsonResponse
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, SignatureExpired
from django.core.mail import send_mail
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

        if User.objects.filter(email=email).count()>0:
            context['err_msg']='邮箱已经存在'
            return render(request,'register.html',context)



        user = User.objects.create_user(uname,email,pwd)
        user.is_active = False
        user.save()




        return HttpResponse('注册成功，请稍候到邮箱中激活账户')


#判断用户名在不在数据库
def exists(request):
    uname = request.GET.get('uname')

    result = User.objects.filter(username=uname).count()

    return JsonResponse({'result':result})


#用户登陆
class LoginView(View):
    def get(request):
        dict = request.GET
        return render(request,'login.html')


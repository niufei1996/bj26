from itsdangerous import TimedJSONWebSignatureSerializer as Serializer,SignatureExpired
from django.conf import settings
from django.core.mail import send_mail
from celery import Celery

app = Celery('celery_tasks.tasks',broker='redis://127.0.0.1:6379/6')


@app.task
def send_user_active(user_id,user_email):
    # 加密编号
    serializer = Serializer(settings.SECRET_KEY, 60 * 60)
    value = serializer.dumps({'id': user_id}).decode()

    # 激活邮箱
    # msg = '<a href="http:/127.0.0.1:8000/user/active/%s>点击激活</a>'%value
    msg = '<a href="http://127.0.0.1:8000/user/active/%s">点击激活</a>' % value
    send_mail('天天生鲜<账户激活>', '', settings.EMAIL_FORM, [user_email], html_message=msg)

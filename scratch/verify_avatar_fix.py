import sys, os, django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from accounts.models import User

u = User.objects.get(email='shahau933@gmail.com')
c = Client()
c.force_login(u)

resp = c.get('/accounts/profile/')
content = resp.content.decode('utf-8')

print('HAS ONERROR:', 'SprintlyProfile.handleImageError' in content)
print('HAS ONLOAD:', 'SprintlyProfile.handleImageLoad' in content)
print('HAS ALT EMPTY:', 'alt=""' in content)
print('HAS INITIALS FALLBACK:', 'avatarInitialsFallback' in content)
print('HAS CSP BLOB:', 'blob:' in resp.headers.get('Content-Security-Policy', ''))
